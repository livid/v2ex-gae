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

"""Mapreduce execution context.

Mapreduce context provides handler code with information about
current mapreduce execution and organizes utility data flow
from handlers such as counters, log messages, mutation pools.
"""



__all__ = ["MAX_ENTITY_COUNT", "MAX_POOL_SIZE", "Context", "MutationPool",
           "Counters", "ItemList", "EntityList", "get", "COUNTER_MAPPER_CALLS"]

from google.appengine.api import datastore
from google.appengine.ext import db

# Maximum pool size in bytes. Pool will be flushed when reaches this amount.
# We use 950,000 bytes which is slightly less than maximum allowed RPC size of
# 1M to have some space cushion.
MAX_POOL_SIZE = 900 * 1000

# Maximum number of items. Pool will be flushed when reaches this amount.
MAX_ENTITY_COUNT = 500

# The name of the counter which counts all mapper calls.
COUNTER_MAPPER_CALLS = "mapper_calls"


def _normalize_entity(value):
  """Return an entity from an entity or model instance."""
  # TODO(user): Consider using datastore.NormalizeAndTypeCheck.
  if getattr(value, "_populate_internal_entity", None):
    return value._populate_internal_entity()
  return value

def _normalize_key(value):
  """Return a key from an entity, model instance, key, or key string."""
  if getattr(value, "key", None):
    return value.key()
  elif isinstance(value, basestring):
    return datastore.Key(value)
  else:
    return value

class ItemList(object):
  """Holds list of arbitrary items, and their total size.

  Properties:
    items: list of objects.
    length: length of item list.
    size: aggregate item size in bytes.
  """

  def __init__(self):
    """Constructor."""
    self.items = []
    self.length = 0
    self.size = 0

  def append(self, item, item_size):
    """Add new item to the list.

    Args:
      item: an item to add to the list.
      item_size: item size in bytes as int.
    """
    self.items.append(item)
    self.length += 1
    self.size += item_size

  def clear(self):
    """Clear item list."""
    self.items = []
    self.length = 0
    self.size = 0

  @property
  def entities(self):
    """Return items. For backwards compatability."""
    return self.items


# For backwards compatability.
EntityList = ItemList


# TODO(user): mutation pool has no error handling at all. Add some.
class MutationPool(object):
  """Mutation pool accumulates datastore changes to perform them in batch.

  Properties:
    puts: ItemList of entities to put to datastore.
    deletes: ItemList of keys to delete from datastore.
    max_pool_size: maximum single list pool size. List changes will be flushed
      when this size is reached.
  """

  def __init__(self, max_pool_size=MAX_POOL_SIZE):
    """Constructor.

    Args:
      max_pool_size: maximum pools size in bytes before flushing it to db.
    """
    self.max_pool_size = max_pool_size
    self.puts = ItemList()
    self.deletes = ItemList()

  def put(self, entity):
    """Registers entity to put to datastore.

    Args:
      entity: an entity or model instance to put.
    """
    actual_entity = _normalize_entity(entity)
    entity_size = len(actual_entity._ToPb().Encode())
    if (self.puts.length >= MAX_ENTITY_COUNT or
        (self.puts.size + entity_size) > self.max_pool_size):
      self.__flush_puts()
    self.puts.append(actual_entity, entity_size)

  def delete(self, entity):
    """Registers entity to delete from datastore.

    Args:
      entity: an entity, model instance, or key to delete.
    """
    # This is not very nice: we're calling two protected methods here...
    key = _normalize_key(entity)
    key_size = len(key._ToPb().Encode())
    if (self.deletes.length >= MAX_ENTITY_COUNT or
        (self.deletes.size + key_size) > self.max_pool_size):
      self.__flush_deletes()
    self.deletes.append(key, key_size)

  # TODO(user): some kind of error handling/retries is needed here.
  def flush(self):
    """Flush(apply) all changed to datastore."""
    self.__flush_puts()
    self.__flush_deletes()

  def __flush_puts(self):
    """Flush all puts to datastore."""
    datastore.Put(self.puts.items)
    self.puts.clear()

  def __flush_deletes(self):
    """Flush all deletes to datastore."""
    datastore.Delete(self.deletes.items)
    self.deletes.clear()


# This doesn't do much yet. In future it will play nicely with checkpoint/error
# handling system.
class Counters(object):
  """Regulates access to counters."""

  def __init__(self, shard_state):
    """Constructor.

    Args:
      shard_state: current mapreduce shard state as model.ShardState.
    """
    self._shard_state = shard_state

  def increment(self, counter_name, delta=1):
    """Increment counter value.

    Args:
      counter_name: name of the counter as string.
      delta: increment delta as int.
    """
    self._shard_state.counters_map.increment(counter_name, delta)

  def flush(self):
    """Flush unsaved counter values."""
    pass


class Context(object):
  """MapReduce execution context.

  Properties:
    mapreduce_spec: current mapreduce specification as model.MapreduceSpec.
    shard_state: current shard state as model.ShardState.
    mutation_pool: current mutation pool as MutationPool.
    counters: counters object as Counters.
  """

  # Current context instance
  _context_instance = None

  def __init__(self, mapreduce_spec, shard_state):
    """Constructor.

    Args:
      mapreduce_spec: mapreduce specification as model.MapreduceSpec.
      shard_state: shard state as model.ShardState.
    """
    # TODO(user): Make these properties protected
    self.mapreduce_spec = mapreduce_spec
    self.shard_state = shard_state

    # TODO(user): These properties can stay public.
    self.mutation_pool = MutationPool()
    self.counters = Counters(shard_state)

    self._pools = {}
    self.register_pool("mutation_pool", self.mutation_pool)
    self.register_pool("counters", self.counters)

  def flush(self):
    """Flush all information recorded in context."""
    for pool in self._pools.values():
      pool.flush()
    if self.shard_state:
      self.shard_state.put()

  # TODO(user): Add convenience method for mapper params.

  # TODO(user): Add fatal error logging method here. Will log the message
  # and set the shard state to failure result status, which the controller
  # callback should pick up and force all shards to terminate.

  def register_pool(self, key, pool):
    """Register an arbitrary pool to be flushed together with this context.

    Args:
      key: pool key as string.
      pool: a pool instance. Pool should implement flush(self) method.
    """
    self._pools[key] = pool

  def get_pool(self, key):
    """Obtains an instance of registered pool.

    Args:
      key: pool key as string.

    Returns:
      an instance of the pool registered earlier, or None.
    """
    return self._pools.get(key, None)

  @classmethod
  def _set(cls, context):
    """Set current context instance.

    Args:
      context: new context as Context or None.
    """
    cls._context_instance = context


def get():
  """Get current context instance.

  Returns:
    current context as Context.
  """
  return Context._context_instance
