#!/usr/bin/env python
#
# Copyright 2010 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Model classes which are used to communicate between parts of implementation.

These model classes are describing mapreduce, its current state and
communication messages. They are either stored in the datastore or
serialized to/from json and passed around with other means.
"""

# Disable "Invalid method name"
# pylint: disable-msg=C6409



__all__ = ["JsonMixin", "JsonProperty", "MapreduceState", "MapperSpec",
           "MapreduceControl", "MapreduceSpec", "ShardState", "CountersMap"]

import copy
import datetime
import logging
import math
import random
from mapreduce.lib import simplejson
import time
import types

from google.appengine.api import datastore_errors
from google.appengine.api import datastore_types
from google.appengine.ext import db
from mapreduce import context
from mapreduce import util
from mapreduce.lib.graphy.backends import google_chart_api


# Default rate of processed entities per second.
_DEFAULT_PROCESSING_RATE_PER_SEC = 100

# Default number of shards to have.
_DEFAULT_SHARD_COUNT = 8


class JsonMixin(object):
  """Simple, stateless json utilities mixin.

  Requires class to implement two methods:
    to_json(self): convert data to json-compatible datastructure (dict,
      list, strings, numbers)
    @classmethod from_json(cls, json): load data from json-compatible structure.
  """

  def to_json_str(self):
    """Convert data to json string representation.

    Returns:
      json representation as string.
    """
    return simplejson.dumps(self.to_json(), sort_keys=True)

  @classmethod
  def from_json_str(cls, json_str):
    """Convert json string representation into class instance.

    Args:
      json_str: json representation as string.

    Returns:
      New instance of the class with data loaded from json string.
    """
    return cls.from_json(simplejson.loads(json_str))


class JsonProperty(db.UnindexedProperty):
  """Property type for storing json representation of data.

  Requires data types to implement two methods:
    to_json(self): convert data to json-compatible datastructure (dict,
      list, strings, numbers)
    @classmethod from_json(cls, json): load data from json-compatible structure.
  """

  def __init__(self, data_type, default=None, **kwargs):
    """Constructor.

    Args:
      data_type: underlying data type as class.
      default: default value for the property. The value is deep copied
        fore each model instance.
      kwargs: remaining arguments.
    """
    kwargs["default"] = default
    super(JsonProperty, self).__init__(**kwargs)
    self.data_type = data_type

  def get_value_for_datastore(self, model_instance):
    """Gets value for datastore.

    Args:
      model_instance: instance of the model class.

    Returns:
      datastore-compatible value.
    """
    value = super(JsonProperty, self).get_value_for_datastore(model_instance)
    if not value:
      return None
    return datastore_types.Text(simplejson.dumps(
        value.to_json(), sort_keys=True))

  def make_value_from_datastore(self, value):
    """Convert value from datastore representation.

    Args:
      value: datastore value.

    Returns:
      value to store in the model.
    """

    if value is None:
      return None
    return self.data_type.from_json(simplejson.loads(value))

  def validate(self, value):
    """Validate value.

    Args:
      value: model value.

    Returns:
      Whether the specified value is valid data type value.

    Raises:
      BadValueError: when value is not of self.data_type type.
    """
    if value is not None and not isinstance(value, self.data_type):
      raise datastore_errors.BadValueError(
          "Property %s must be convertible to a %s instance (%s)" %
          (self.name, self.data_type, value))
    return super(JsonProperty, self).validate(value)

  def empty(self, value):
    """Checks if value is empty.

    Args:
      value: model value.

    Returns:
      True passed value is empty.
    """
    return not value

  def default_value(self):
    """Create default model value.

    If default option was specified, then it will be deeply copied.
    None otherwise.

    Returns:
      default model value.
    """
    if self.default:
      return copy.deepcopy(self.default)
    else:
      return None



# Ridiculous future UNIX epoch time, 500 years from now.
_FUTURE_TIME = 2**34


def _get_descending_key(gettime=time.time, getrandint=random.randint):
  """Returns a key name lexically ordered by time descending.

  This lets us have a key name for use with Datastore entities which returns
  rows in time descending order when it is scanned in lexically ascending order,
  allowing us to bypass index building for descending indexes.

  Args:
    gettime: Used for testing.
    getrandint: Used for testing.

  Returns:
    A string with a time descending key.
  """
  now_descending = int((_FUTURE_TIME - gettime()) * 100)
  tie_breaker = getrandint(0, 100)
  return "%d%d" % (now_descending, tie_breaker)


class CountersMap(JsonMixin):
  """Maintains map from counter name to counter value.

  The class is used to provide basic arithmetics of counter values (buil
  add/remove), increment individual values and store/load data from json.
  """

  def __init__(self, initial_map=None):
    """Constructor.

    Args:
      initial_map: initial counter values map from counter name (string) to
        counter value (int).
    """
    if initial_map:
      self.counters = initial_map
    else:
      self.counters = {}

  def __repr__(self):
    """Compute string representation."""
    return "mapreduce.model.CountersMap(%r)" % self.counters

  def get(self, counter_name):
    """Get current counter value.

    Args:
      counter_name: counter name as string.

    Returns:
      current counter value as int. 0 if counter was not set.
    """
    return self.counters.get(counter_name, 0)

  def increment(self, counter_name, delta):
    """Increment counter value.

    Args:
      counter_name: counter name as String.
      delta: increment delta as Integer.

    Returns:
      new counter value.
    """
    current_value = self.counters.get(counter_name, 0)
    new_value = current_value + delta
    self.counters[counter_name] = new_value
    return new_value

  def add_map(self, counters_map):
    """Add all counters from the map.

    For each counter in the passed map, adds its value to the counter in this
    map.

    Args:
      counters_map: CounterMap instance to add.
    """
    for counter_name in counters_map.counters:
      self.increment(counter_name, counters_map.counters[counter_name])

  def sub_map(self, counters_map):
    """Subtracts all counters from the map.

    For each counter in the passed map, subtracts its value to the counter in
    this map.

    Args:
      counters_map: CounterMap instance to subtract.
    """
    for counter_name in counters_map.counters:
      self.increment(counter_name, -counters_map.counters[counter_name])

  def clear(self):
    """Clear all values."""
    self.counters = {}

  def to_json(self):
    """Serializes all the data in this map into json form.

    Returns:
      json-compatible data representation.
    """
    return {"counters": self.counters}

  @classmethod
  def from_json(cls, json):
    """Create new CountersMap from the json data structure, encoded by to_json.

    Args:
      json: json representation of CountersMap .

    Returns:
      an instance of CountersMap with all data deserialized from json.
    """
    counters_map = cls()
    counters_map.counters = json["counters"]
    return counters_map


class MapperSpec(JsonMixin):
  """Contains a specification for the mapper phase of the mapreduce.

  MapperSpec instance can be changed only during mapreduce starting process,
  and it remains immutable for the rest of mapreduce execution. MapperSpec is
  passed as a payload to all mapreduce tasks in JSON encoding as part of
  MapreduceSpec.

  Specifying mapper handlers:
    * '<module_name>.<class_name>' - __call__ method of class instance will be
      called
    * '<module_name>.<function_name>' - function will be called.
    * '<module_name>.<class_name>.<method_name>' - class will be instantiated
      and method called.
  """

  def __init__(self, handler_spec, input_reader_spec, params, shard_count):
    """Creates a new MapperSpec.

    Args:
      handler_spec: handler specification as string (see class doc for
        details).
      input_reader_spec: The class name of the input reader to use.
      params: Dictionary of additional parameters for the mapper.
      shard_count: number of shards to process in parallel.

    Properties:
      handler_spec: name of handler class/function to use.
      shard_count: number of shards to process in parallel.
      handler: cached instance of mapper handler as callable.
      input_reader_spec: The class name of the input reader to use.
      params: Dictionary of additional parameters for the mapper.
    """
    self.handler_spec = handler_spec
    self.__handler = None
    self.input_reader_spec = input_reader_spec
    self.shard_count = shard_count
    self.params = params

  def get_handler(self):
    """Get mapper handler instance.

    Returns:
      cached handler instance as callable.
    """
    if self.__handler is None:
      resolved_spec = util.for_name(self.handler_spec)
      if isinstance(resolved_spec, type):
        # create new instance if this is type
        self.__handler = resolved_spec()
      elif isinstance(resolved_spec, types.MethodType):
        # bind the method
        self.__handler = getattr(resolved_spec.im_class(),
                                 resolved_spec.__name__)
      else:
        self.__handler = resolved_spec
    return self.__handler

  handler = property(get_handler)

  def input_reader_class(self):
    """Get input reader class.

    Returns:
      input reader class object.
    """
    return util.for_name(self.input_reader_spec)

  def to_json(self):
    """Serializes this MapperSpec into a json-izable object."""
    return {
        "mapper_handler_spec": self.handler_spec,
        "mapper_input_reader": self.input_reader_spec,
        "mapper_params": self.params,
        "mapper_shard_count": self.shard_count,
    }

  @classmethod
  def from_json(cls, json):
    """Creates MapperSpec from a dict-like object."""
    return cls(json["mapper_handler_spec"],
               json["mapper_input_reader"],
               json["mapper_params"],
               json["mapper_shard_count"])


class MapreduceSpec(JsonMixin):
  """Contains a specification for the whole mapreduce.

  MapreduceSpec instance can be changed only during mapreduce starting process,
  and it remains immutable for the rest of mapreduce execution. MapreduceSpec is
  passed as a payload to all mapreduce tasks in json encoding.
  """

  # Url to call when mapreduce finishes its execution.
  PARAM_DONE_CALLBACK = "done_callback"
  # Queue to use to call done callback
  PARAM_DONE_CALLBACK_QUEUE = "done_callback_queue"

  def __init__(self,
               name,
               mapreduce_id,
               mapper_spec,
               params = {}):
    """Create new MapreduceSpec.

    Args:
      name: The name of this mapreduce job type.
      mapreduce_id: ID of the mapreduce.
      mapper_spec: JSON-encoded string containing a MapperSpec.
      params: dictionary of additional mapreduce parameters.

    Properties:
      name: The name of this mapreduce job type.
      mapreduce_id: unique id of this mapreduce as string.
      mapper: This MapreduceSpec's instance of MapperSpec.
      params: dictionary of additional mapreduce parameters.
    """
    self.name = name
    self.mapreduce_id = mapreduce_id
    self.mapper = MapperSpec.from_json(mapper_spec)
    self.params = params

  def to_json(self):
    """Serializes all data in this mapreduce spec into json form.

    Returns:
      data in json format.
    """
    mapper_spec = self.mapper.to_json()
    return {
        "name": self.name,
        "mapreduce_id": self.mapreduce_id,
        "mapper_spec": mapper_spec,
        "params": self.params,
    }

  @classmethod
  def from_json(cls, json):
    """Create new MapreduceSpec from the json, encoded by to_json.

    Args:
      json: json representation of MapreduceSpec.

    Returns:
      an instance of MapreduceSpec with all data deserialized from json.
    """
    mapreduce_spec = cls(json["name"],
                         json["mapreduce_id"],
                         json["mapper_spec"],
                         json.get("params"))
    return mapreduce_spec


class MapreduceState(db.Model):
  """Holds accumulated state of mapreduce execution.

  MapreduceState is stored in datastore with a key name equal to the
  mapreduce ID. Only controller tasks can write to MapreduceState.

  Properties:
    mapreduce_spec: cached deserialized MapreduceSpec instance. read-only
    active: if we have this mapreduce running right now
    last_poll_time: last time controller job has polled this mapreduce.
    counters_map: shard's counters map as CountersMap. Mirrors
      counters_map_json.
    chart_url: last computed mapreduce status chart url. This chart displays the
      progress of all the shards the best way it can.
    sparkline_url: last computed mapreduce status chart url in small format.
    result_status: If not None, the final status of the job.
    active_shards: How many shards are still processing.
    start_time: When the job started.
  """

  RESULT_SUCCESS = "success"
  RESULT_FAILED = "failed"
  RESULT_ABORTED = "aborted"

  _RESULTS = frozenset([RESULT_SUCCESS, RESULT_FAILED, RESULT_ABORTED])

  # Functional properties.
  mapreduce_spec = JsonProperty(MapreduceSpec, indexed=False)
  active = db.BooleanProperty(default=True, indexed=False)
  last_poll_time = db.DateTimeProperty(required=True)
  counters_map = JsonProperty(CountersMap, default=CountersMap(), indexed=False)
  app_id = db.StringProperty(required=False, indexed=True)

  # For UI purposes only.
  chart_url = db.TextProperty(default="")
  sparkline_url = db.TextProperty(default="")
  result_status = db.StringProperty(required=False, choices=_RESULTS)
  active_shards = db.IntegerProperty(default=0, indexed=False)
  failed_shards = db.IntegerProperty(default=0, indexed=False)
  aborted_shards = db.IntegerProperty(default=0, indexed=False)
  start_time = db.DateTimeProperty(auto_now_add=True)

  @classmethod
  def get_key_by_job_id(cls, mapreduce_id):
    """Retrieves the Key for a Job.

    Args:
      mapreduce_id: The job to retrieve.

    Returns:
      Datastore Key that can be used to fetch the MapreduceState.
    """
    return db.Key.from_path(cls.kind(), mapreduce_id)

  def set_processed_counts(self, shards_processed):
    """Updates a chart url to display processed count for each shard.

    Args:
      shards_processed: list of integers with number of processed entities in
        each shard
    """
    chart = google_chart_api.BarChart(shards_processed)
    if self.mapreduce_spec and shards_processed:
      chart.bottom.labels = [
          str(x) for x in xrange(self.mapreduce_spec.mapper.shard_count)]
      chart.left.labels = ['0', str(max(shards_processed))]
      chart.left.min = 0
    self.chart_url = chart.display.Url(300, 200)

  def get_processed(self):
    """Number of processed entities.

    Returns:
      The total number of processed entities as int.
    """
    return self.counters_map.get(context.COUNTER_MAPPER_CALLS)

  processed = property(get_processed)

  @staticmethod
  def create_new(getkeyname=_get_descending_key,
                 gettime=datetime.datetime.now):
    """Create a new MapreduceState.

    Args:
      getkeyname: Used for testing.
      gettime: Used for testing.
    """
    state = MapreduceState(key_name=getkeyname(),
                           last_poll_time=gettime())
    state.set_processed_counts([])
    return state


class ShardState(db.Model):
  """Single shard execution state.

  The shard state is stored in the datastore and is later aggregated by
  controller task. Shard key_name is equal to shard_id.

  Properties:
    active: if we have this shard still running as boolean.
    counters_map: shard's counters map as CountersMap. Mirrors
      counters_map_json.
    mapreduce_id: unique id of the mapreduce.
    shard_id: unique id of this shard as string.
    shard_number: ordered number for this shard.
    result_status: If not None, the final status of this shard.
    update_time: The last time this shard state was updated.
    shard_description: A string description of the work this shard will do.
    last_work_item: A string description of the last work item processed.
  """

  RESULT_SUCCESS = "success"
  RESULT_FAILED = "failed"
  RESULT_ABORTED = "aborted"

  _RESULTS = frozenset([RESULT_SUCCESS, RESULT_FAILED, RESULT_ABORTED])

  # Functional properties.
  active = db.BooleanProperty(default=True, indexed=False)
  counters_map = JsonProperty(CountersMap, default=CountersMap(), indexed=False)
  result_status = db.StringProperty(choices=_RESULTS, indexed=False)

  # For UI purposes only.
  mapreduce_id = db.StringProperty(required=True)
  update_time = db.DateTimeProperty(auto_now=True, indexed=False)
  shard_description = db.TextProperty(default="")
  last_work_item = db.TextProperty(default="")

  def get_shard_number(self):
    """Gets the shard number from the key name."""
    return int(self.key().name().split("-")[-1])

  shard_number = property(get_shard_number)

  def get_shard_id(self):
    """Returns the shard ID."""
    return self.key().name()

  shard_id = property(get_shard_id)

  @classmethod
  def shard_id_from_number(cls, mapreduce_id, shard_number):
    """Get shard id by mapreduce id and shard number.

    Args:
      mapreduce_id: mapreduce id as string.
      shard_number: shard number to compute id for as int.

    Returns:
      shard id as string.
    """
    return "%s-%d" % (mapreduce_id, shard_number)

  @classmethod
  def get_key_by_shard_id(cls, shard_id):
    """Retrieves the Key for this ShardState.

    Args:
      shard_id: The shard ID to fetch.

    Returns:
      The Datatore key to use to retrieve this ShardState.
    """
    return db.Key.from_path(cls.kind(), shard_id)

  @classmethod
  def get_by_shard_id(cls, shard_id):
    """Get shard state from datastore by shard_id.

    Args:
      shard_id: shard id as string.

    Returns:
      ShardState for given shard id or None if it's not found.
    """
    return cls.get_by_key_name(shard_id)

  @classmethod
  def find_by_mapreduce_id(cls, mapreduce_id):
    """Find all shard states for given mapreduce.

    Args:
      mapreduce_id: mapreduce id.

    Returns:
      iterable of all ShardState for given mapreduce id.
    """
    return cls.all().filter("mapreduce_id =", mapreduce_id).fetch(99999)

  @classmethod
  def create_new(cls, mapreduce_id, shard_number):
    """Create new shard state.

    Args:
      mapreduce_id: unique mapreduce id as string.
      shard_number: shard number for which to create shard state.

    Returns:
      new instance of ShardState ready to put into datastore.
    """
    shard_id = cls.shard_id_from_number(mapreduce_id, shard_number)
    state = cls(key_name=shard_id,
                mapreduce_id=mapreduce_id)
    return state


class MapreduceControl(db.Model):
  """Datastore entity used to control mapreduce job execution.

  Only one command may be sent to jobs at a time.

  Properties:
    command: The command to send to the job.
  """

  ABORT = "abort"

  _COMMANDS = frozenset([ABORT])
  _KEY_NAME = "command"

  command = db.TextProperty(choices=_COMMANDS, required=True)

  @classmethod
  def get_key_by_job_id(cls, mapreduce_id):
    """Retrieves the Key for a mapreduce ID.

    Args:
      mapreduce_id: The job to fetch.

    Returns:
      Datastore Key for the command for the given job ID.
    """
    return db.Key.from_path(cls.kind(), "%s:%s" % (mapreduce_id, cls._KEY_NAME))

  @classmethod
  def abort(cls, mapreduce_id):
    """Causes a job to abort.

    Args:
      mapreduce_id: The job to abort. Not verified as a valid job.
    """
    cls(key_name="%s:%s" % (mapreduce_id, cls._KEY_NAME),
        command=cls.ABORT).put()
