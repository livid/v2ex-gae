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

"""Simple quota system backed by memcache storage."""




# Memcache namespace to use.
_QUOTA_NAMESPACE = "quota"

# Offset all quota values by this amount since memcache incr/decr
# operate only with unsigned values.
_OFFSET = 2**32


class QuotaManager(object):
  """Simple quota system manager, backed by memcache storage.

  Since memcache storage is not reliable, this quota system is not reliable and
  best effort only.

  Quota is managed by buckets. Each bucket contains a 32-bit int value of
  available quota. Buckets should be refilled manually with 'put' method.

  It is safe to use a single bucket from multiple clients simultaneously.
  """

  def __init__(self, memcache_client):
    """Initialize new instance.

    Args:
      memcache_client: an instance of memcache client to use.
    """
    self.memcache_client = memcache_client

  def put(self, bucket, amount):
    """Put amount into quota bucket.

    Args:
      bucket: quota bucket as string.
      amount: amount to bit put into quota as int.
    """
    self.memcache_client.incr(bucket, delta=amount,
                              initial_value=_OFFSET, namespace=_QUOTA_NAMESPACE)

  def consume(self, bucket, amount, consume_some=False):
    """Consume amount from quota bucket.

    Args:
      bucket: quota bucket as string.
      amount: amount to consume.
      consume_some: specifies behavior in case of not enough quota. If False,
        the method will leave quota intact and return 0. If True, will try to
        consume as much as possible.

    Returns:
      Amount of quota consumed.
    """
    new_quota = self.memcache_client.decr(
        bucket, delta=amount, initial_value=_OFFSET, namespace=_QUOTA_NAMESPACE)

    if new_quota >= _OFFSET:
      return amount

    if consume_some and _OFFSET - new_quota < amount:
      # we still can consume some
      self.put(bucket, _OFFSET - new_quota)
      return amount - (_OFFSET - new_quota)
    else:
      self.put(bucket, amount)
      return 0

  def get(self, bucket):
    """Get current bucket amount.

    Args:
      bucket: quota bucket as string.

    Returns:
      current bucket amount as int.
    """
    amount = self.memcache_client.get(bucket, namespace=_QUOTA_NAMESPACE)
    if amount:
      return int(amount) - _OFFSET
    else:
      return 0

  def set(self, bucket, amount):
    """Set bucket amount.

    Args:
      bucket: quota bucket as string.
      amount: new bucket amount as int.
    """
    self.memcache_client.set(bucket, amount + _OFFSET,
                             namespace=_QUOTA_NAMESPACE)


class QuotaConsumer(object):
  """Quota consumer wrapper for efficient quota consuming/reclaiming.

  Quota is consumed in batches and put back in dispose() method.

  WARNING: Always call the dispose() method if you need to keep quota
  consistent.
  """

  def __init__(self, quota_manager, bucket, batch_size):
    """Initialize new instance.

    Args:
      quota_manager: quota manager to use for quota operations as QuotaManager.
      bucket: quota bucket name as string.
      batch_size: batch size for quota consuming as int.
    """
    self.quota_manager = quota_manager
    self.batch_size = batch_size
    self.bucket = bucket
    self.quota = 0

  def consume(self, amount=1):
    """Consume quota.

    Args:
      amount: amount of quota to be consumed as int.

    Returns:
      True if quota was successfully consumed, False if there's not enough
      quota.
    """
    while self.quota < amount:
      delta = self.quota_manager.consume(self.bucket, self.batch_size,
                                         consume_some=True)
      if not delta:
        return False
      self.quota += delta

    self.quota -= amount
    return True

  def put(self, amount=1):
    """Put quota back.

    Args:
      amount: amount of quota as int.
    """
    self.quota += amount

  def check(self, amount=1):
    """Check that we have enough quota right now.

    This doesn't lock or consume the quota. Following consume might in fact
    fail/succeeded.

    Args:
      amount: amount of quota to check.

    Returns:
      True if we have enough quota to consume specified amount right now. False
      otherwise.
  """
    if self.quota >= amount:
      return True
    return self.quota + self.quota_manager.get(self.bucket) >= amount

  def dispose(self):
    """Dispose QuotaConsumer and put all actually unconsumed quota back.

    This method has to be called for quota consistency!
    """
    self.quota_manager.put(self.bucket, self.quota)
