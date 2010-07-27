/*
 * Copyright 2010 Google Inc.
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *      http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

/********* Common functions *********/

// Sets the status butter, optionally indicating if it's an error message.
function setButter(message, error) {
  var butter = $("#butter");
  // Prevent flicker on butter update by hiding it first.
  butter.css('display', 'none');
  if (error) {
    butter.removeClass('info').addClass('error').text(message);
  } else {
    butter.removeClass('error').addClass('info').text(message);
  }
  butter.css('display', null)
  $(document).scrollTop(0);
}

// Given an AJAX error message (which is empty or null on success) and a
// data payload containing JSON, parses the data payload and returns the object.
// Server-side errors and AJAX errors will be brought to the user's attention
// if present in the response object
function getResponseDataJson(error, data) {
  var response = null;
  try {
    response = $.parseJSON(data);
  } catch (e) {
    error = '' + e;
  }
  if (response && response.error_class) {
    error = response.error_class + ': ' + response.error_message;
  } else if (!response) {
    error = 'Could not parse response JSON data.';
  }
  if (error) {
    setButter('Error -- ' + error, true);
    return null;
  }
  return response;
}

// Retrieve the list of configs.
function listConfigs(resultFunc) {
  $.ajax({
    type: 'GET',
    url: 'command/list_configs',
    dataType: 'text',
    error: function(request, textStatus) {
      getResponseDataJson(textStatus);
    },
    success: function(data, textStatus, request) {
      var response = getResponseDataJson(null, data);
      if (response) {
        resultFunc(response.configs);
      }
    }
  });
}

// Return the list of job records.
function listJobs(cursor, resultFunc) {
  $.ajax({
    type: 'GET',
    url: 'command/list_jobs',
    dataType: 'text',
    error: function(request, textStatus) {
      getResponseDataJson(textStatus);
    },
    success: function(data, textStatus, request) {
      var response = getResponseDataJson(null, data);
      if (response) {
        resultFunc(response.jobs, response.cursor);
      }
    }
  });
}

// Cleans up a job with the given name and ID, updates butter with status.
function cleanUpJob(name, mapreduce_id) {
  if (!confirm('Clean up job "' + name +
               '" with ID "' + mapreduce_id + '"?')) {
    return;
  }

  $.ajax({
    async: false,
    type: 'POST',
    url: 'command/cleanup_job',
    data: {'mapreduce_id': mapreduce_id},
    dataType: 'text',
    error: function(request, textStatus) {
      getResponseDataJson(textStatus);
    },
    success: function(data, textStatus, request) {
      var response = getResponseDataJson(null, data);
      if (response) {
        setButter(response.status);
      }
    }
  });
}

// Aborts the job with the given ID, updates butter with status.
function abortJob(name, mapreduce_id) {
  if (!confirm('Abort job "' + name + '" with ID "' + mapreduce_id + '"?')) {
    return;
  }

  $.ajax({
    async: false,
    type: 'POST',
    url: 'command/abort_job',
    data: {'mapreduce_id': mapreduce_id},
    dataType: 'text',
    error: function(request, textStatus) {
      getResponseDataJson(textStatus);
    },
    success: function(data, textStatus, request) {
      var response = getResponseDataJson(null, data);
      if (response) {
        setButter(response.status);
      }
    }
  });
}

// Retrieve the detail for a job.
function getJobDetail(jobId, resultFunc) {
  $.ajax({
    type: 'GET',
    url: 'command/get_job_detail',
    dataType: 'text',
    data: {'mapreduce_id': jobId},
    error: function(request, textStatus) {
      getResponseDataJson(textStatus);
    },
    success: function(data, textStatus, request) {
      var response = getResponseDataJson(null, data);
      if (response) {
        resultFunc(jobId, response);
      }
    }
  });
}

// Turns a key into a nicely scrubbed parameter name.
function getNiceParamKey(key) {
  // TODO: Figure out if we want to do this at all.
  return key;
}

// Returns an array of the keys of an object in sorted order.
function getSortedKeys(obj) {
  var keys = [];
  $.each(obj, function(key, value) {
    keys.push(key);
  });
  keys.sort();
  return keys;
}

// Gets a local datestring from a UNIX timestamp in milliseconds.
function getLocalTimestring(timestamp_ms) {
  var when = new Date();
  when.setTime(timestamp_ms);
  return when.toLocaleString();
}

function leftPadNumber(number, minSize, paddingChar) {
  var stringified = '' + number;
  if (stringified.length < minSize) {
    for (var i = 0; i < (minSize - stringified.length); ++i) {
      stringified = paddingChar + stringified;
    }
  }
  return stringified;
}

// Get locale time string for time portion of job runtime. Specially
// handle number of days running as a prefix.
function getElapsedTimeString(start_timestamp_ms, updated_timestamp_ms) {
  var updatedDiff = updated_timestamp_ms - start_timestamp_ms;
  var updatedDays = Math.floor(updatedDiff / 86400000.0);
  updatedDiff -= (updatedDays * 86400000.0);
  var updatedHours = Math.floor(updatedDiff / 3600000.0);
  updatedDiff -= (updatedHours * 3600000.0);
  var updatedMinutes = Math.floor(updatedDiff / 60000.0);
  updatedDiff -= (updatedMinutes * 60000.0);
  var updatedSeconds = Math.floor(updatedDiff / 1000.0);

  var updatedString = '';
  if (updatedDays == 1) {
    updatedString = '1 day, ';
  } else if (updatedDays > 1) {
    updatedString = '' + updatedDays + ' days, ';
  }
  updatedString +=
      leftPadNumber(updatedHours, 2, '0') + ':' +
      leftPadNumber(updatedMinutes, 2, '0') + ':' +
      leftPadNumber(updatedSeconds, 2, '0');

  return updatedString;
}

// Retrieves the mapreduce_id from the query string. Assumes that it is
// the only querystring parameter.
function getJobId() {
  var index = window.location.search.lastIndexOf("=");
  if (index == -1) {
    return '';
  }
  return decodeURIComponent(window.location.search.substr(index+1));
}

/********* Specific to overview status page *********/

//////// Running jobs overview.
function initJobOverview(jobs, cursor) {
  // Empty body.
  var body = $('#running-list > tbody');
  body.empty();

  if (!jobs || (jobs && jobs.length == 0)) {
    $('<td colspan="8">').text("No job records found.").appendTo(body);
    return;
  }

  // Show header.
  $('#running-list > thead').css('display', null);

  // Populate the table.
  $.each(jobs, function(index, job) {
    var row = $('<tr>');

    // TODO: Style running colgroup for capitalization.
    var status = (job.active ? 'running' : job.result_status) || 'unknown';
    row.append($('<td class="status-text">').text(status));

    $('<td>').append(
      $('<a>')
        .attr('href', 'detail?mapreduce_id=' + job.mapreduce_id)
        .text('Detail')).appendTo(row);

    row.append($('<td>').text(job.mapreduce_id))
      .append($('<td>').text(job.name));

    var activity = '' + job.active_shards + ' / ' + job.shards + ' shards';
    row.append($('<td>').text(activity))

    row.append($('<td>').text(getLocalTimestring(job.start_timestamp_ms)));

    row.append($('<td>').text(getElapsedTimeString(
        job.start_timestamp_ms, job.updated_timestamp_ms)));

    // Controller links for abort, cleanup, etc.
    if (job.active) {
      var control = $('<a href="">').text('Abort')
        .click(function(event) {
          abortJob(job.name, job.mapreduce_id);
          event.stopPropagation();
          return false;
        });
      row.append($('<td>').append(control));
    } else {
      var control = $('<a href="">').text('Cleanup')
        .click(function(event) {
          cleanUpJob(job.name, job.mapreduce_id);
          event.stopPropagation();
          return false;
        });
      row.append($('<td>').append(control));
    }
    row.appendTo(body);
  });

  // Set up the next/first page links.
  $('#running-first-page')
    .css('display', null)
    .unbind('click')
    .click(function() {
    listJobs(null, initJobOverview);
    return false;
  });
  $('#running-next-page').unbind('click');
  if (cursor) {
    $('#running-next-page')
      .css('display', null)
      .click(function() {
        listJobs(cursor, initJobOverview);
        return false;
      });
  } else {
    $('#running-next-page').css('display', 'none');
  }
  $('#running-list > tfoot').css('display', null);
}

//////// Launching jobs.

var FIXED_JOB_PARAMS = [
    'name', 'mapper_input_reader', 'mapper_handler', 'mapper_params_validator'
];

var EDITABLE_JOB_PARAMS = ['shard_count', 'processing_rate', 'queue_name'];

function getJobForm(name) {
  return $('form.run-job > input[name="name"][value="' + name + '"]').parent();
}

function showRunJobConfig(name) {
  var matchedForm = null;
  $.each($('form.run-job'), function(index, jobForm) {
    if ($(jobForm).find('input[name="name"]').val() == name) {
      matchedForm = jobForm;
    } else {
      $(jobForm).css('display', 'none');
    }
  });
  $(matchedForm).css('display', null);
}

function runJobDone(name, error, data) {
  var jobForm = getJobForm(name);
  var response = getResponseDataJson(error, data);
  if (response) {
    setButter('Successfully started job "' + response['mapreduce_id'] + '"');
    listJobs(null, initJobOverview);
  }
  jobForm.find('input[type="submit"]').attr('disabled', null);
}

function runJob(name) {
  var jobForm = getJobForm(name);
  jobForm.find('input[type="submit"]').attr('disabled', 'disabled');
  $.ajax({
    type: 'POST',
    url: 'command/start_job',
    data: jobForm.serialize(),
    dataType: 'text',
    error: function(request, textStatus) {
      runJobDone(name, textStatus);
    },
    success: function(data, textStatus, request) {
      runJobDone(name, null, data);
    }
  });
}

function initJobLaunching(configs) {
  $('#launch-control').empty();
  if (!configs || (configs && configs.length == 0)) {
    $('#launch-control').append('No job configurations found.');
    return;
  }

  // Set up job config forms.
  $.each(configs, function(index, config) {
    var jobForm = $('<form class="run-job">')
      .submit(function() {
        runJob(config.name);
        return false;
      })
      .css('display', 'none')
      .appendTo("#launch-container");

    // Fixed job config values.
    $.each(FIXED_JOB_PARAMS, function(unused, key) {
      var value = config[key];
      if (!value) return;
      if (key != 'name') {
        // Name is up in the page title so doesn't need to be shown again.
        $('<p class="job-static-param">')
          .append($('<span class="param-key">').text(getNiceParamKey(key)))
          .append($('<span class="param-value">').text(value))
          .appendTo(jobForm);
      }
      $('<input type="hidden">')
        .attr('name', key)
        .attr('value', value)
        .appendTo(jobForm);
    });

    // Add parameter values to the job form.
    function addParameters(params, prefix) {
      if (!params) {
        return;
      }

      var sortedParams = getSortedKeys(params);
      $.each(sortedParams, function(index, key) {
        var value = params[key];
        var paramId = 'job-' + prefix + key + '-param';
        var paramP = $('<p class="editable-input">');

        // Deal with the case in which the value is an object rather than
        // just the default value string.
        var prettyKey = key;
        if (value && value["human_name"]) {
          prettyKey = value["human_name"];
        }

        if (value && value["default_value"]) {
          value = value["default_value"];
        }

        $('<label>')
          .attr('for', paramId)
          .text(prettyKey)
          .appendTo(paramP);
        $('<input type="text">')
          .attr('id', paramId)
          .attr('name', prefix + key)
          .attr('value', value)
          .appendTo(paramP);
        paramP.appendTo(jobForm);
      });
    }

    addParameters(config.params, "params.");
    addParameters(config.mapper_params, "mapper_params.");

    $('<input type="submit">')
      .attr('value', 'Run')
      .appendTo(jobForm);
  });

  // Setup job name drop-down.
  var jobSelector = $('<select>')
      .change(function(event) {
        showRunJobConfig($(event.target).val());
      })
      .appendTo('#launch-control');
  $.each(configs, function(index, config) {
    $('<option>')
      .attr('name', config.name)
      .text(config.name)
      .appendTo(jobSelector);
  });
  showRunJobConfig(jobSelector.val());
}

//////// Status page entry point.
function initStatus() {
  listConfigs(initJobLaunching);
  listJobs(null, initJobOverview);
}

/********* Specific to detail status page *********/

//////// Job detail.
function refreshJobDetail(jobId, detail) {
  // Overview parameters.
  var jobParams = $('#detail-params');
  jobParams.empty();

  // TODO: Style running colgroup for capitalization.
  var status = (detail.active ? 'running' : detail.result_status) || 'unknown';
  $('<li class="status-text">').text(status).appendTo(jobParams);

  $('<li>')
    .append($('<span class="param-key">').text('Elapsed time'))
    .append($('<span class="param-value">').text(getElapsedTimeString(
          detail.start_timestamp_ms, detail.updated_timestamp_ms)))
    .appendTo(jobParams);
  $('<li>')
    .append($('<span class="param-key">').text('Start time'))
    .append($('<span class="param-value">').text(getLocalTimestring(
          detail.start_timestamp_ms)))
    .appendTo(jobParams);

  $.each(FIXED_JOB_PARAMS, function(index, key) {
    // Skip some parameters or those with no values.
    if (key == 'name') return;
    var value = detail[key];
    if (!value) return;

    $('<li>')
      .append($('<span class="param-key">').text(getNiceParamKey(key)))
      .append($('<span class="param-value">').text(value))
      .appendTo(jobParams);
  });

  // User-supplied parameters.
  if (detail.mapper_spec.mapper_params) {
    var sortedKeys = getSortedKeys(detail.mapper_spec.mapper_params);
    $.each(sortedKeys, function(index, key) {
      var value = detail.mapper_spec.mapper_params[key];
      $('<li>')
        .append($('<span class="user-param-key"">').text(key))
        .append($('<span class="param-value">').html(value))
        .appendTo(jobParams);
    });
  }

  // Graph image.
  var detailGraph = $('#detail-graph');
  detailGraph.empty();
  $('<div>').text('Processed items per shard').appendTo(detailGraph);
  $('<img>')
    .attr('src', detail.chart_url)
    .attr('width', 300)
    .attr('height', 200)
    .appendTo(detailGraph);

  // Aggregated counters.
  var aggregatedCounters = $('#aggregated-counters');
  aggregatedCounters.empty();
  var runtimeMs = detail.updated_timestamp_ms - detail.start_timestamp_ms;
  var sortedCounters = getSortedKeys(detail.counters);
  $.each(sortedCounters, function(index, key) {
    var value = detail.counters[key];
    // Round to 2 decimal places.
    var avgRate = Math.round(100.0 * value / (runtimeMs / 1000.0)) / 100.0;
    $('<li>')
      .append($('<span class="param-key">').html(getNiceParamKey(key)))
      .append($('<span class="param-value">').html(value))
      .append($('<span class="param-aux">').text('(' + avgRate + '/sec avg.)'))
      .appendTo(aggregatedCounters);
  });

  // Set up the mapper detail.
  var mapperBody = $('#mapper-shard-status');
  mapperBody.empty();

  $.each(detail.shards, function(index, shard) {
    var row = $('<tr>');

    row.append($('<td>').text(shard.shard_number));

    // TODO: Style running colgroup for capitalization.
    var status = (shard.active ? 'running' : shard.result_status) || 'unknown';
    row.append($('<td>').text(status));

    // TODO: Set colgroup width for shard description.
    row.append($('<td>').text(shard.shard_description));

    row.append($('<td>').text(shard.last_work_item || 'Unknown'));

    row.append($('<td>').text(getElapsedTimeString(
        detail.start_timestamp_ms, shard.updated_timestamp_ms)));

    row.appendTo(mapperBody);
  });
}

function initJobDetail(jobId, detail) {
  // Set titles.
  var title = 'Status for "' + detail.name + '"-- Job #' + jobId;
  $('head > title').text(title);
  $('#detail-page-title').text(detail.name);
  $('#detail-page-undertext').text('Job #' + jobId);

  // Set control buttons.
  if (detail.active) {
    var control = $('<a href="">')
      .text('Abort Job')
      .click(function(event) {
        abortJob(detail.name, jobId);
        event.stopPropagation();
        return false;
      });
    $('#job-control').append(control);
  } else {
    var control = $('<a href="">')
      .text('Cleanup Job')
      .click(function(event) {
        cleanUpJob(detail.name, jobId);
        event.stopPropagation();
        return false;
      });
    $('#job-control').append(control);
  }

  refreshJobDetail(jobId, detail);
}

//////// Detail page entry point.
function initDetail() {
  var jobId = getJobId();
  if (!jobId) {
    setButter("Could not find job ID in query string.", true);
    return;
  }
  getJobDetail(jobId, initJobDetail);
}
