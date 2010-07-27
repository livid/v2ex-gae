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

"""Base handler class for all mapreduce handlers.
"""




import logging
from mapreduce.lib import simplejson

from google.appengine.ext import webapp


class BaseHandler(webapp.RequestHandler):
  """Base class for all mapreduce handlers."""

  def base_path(self):
    """Base path for all mapreduce-related urls."""
    path = self.request.path
    return path[:path.rfind("/")]


class JsonHandler(BaseHandler):
  """Base class for JSON handlers for user interface.

  Sub-classes should implement the 'handle' method. They should put their
  response data in the 'self.json_response' dictionary. Any exceptions raised
  by the sub-class implementation will be sent in a JSON response with the
  name of the error_class and the error_message.
  """

  def __init__(self):
    """Initializer."""
    super(BaseHandler, self).__init__()
    self.json_response = {}

  def get(self):
    self.post()

  def post(self):
    self.json_response.clear()
    try:
      self.handle()
    except Exception, e:
      logging.exception("Error in JsonHandler, returning exception.")
      # TODO(user): Include full traceback here for the end-user.
      self.json_response.clear()
      self.json_response["error_class"] = e.__class__.__name__
      self.json_response["error_message"] = str(e)

    self.response.headers["Content-Type"] = "text/javascript"
    try:
      output = simplejson.dumps(self.json_response)
    except:
      logging.exception("Could not serialize to JSON")
      self.response.set_status(500, message="Could not serialize to JSON")
      return
    else:
      self.response.out.write(output)

  def handle(self):
    """To be implemented by sub-classes."""
    raise NotImplementedError()
