import pickle

import redis

from common import config

redis_client = redis.Redis(host=config.redis_host, password=config.redis_pass, port=6379, db=0)

class RedisCache:

  @staticmethod
  def put(key, value, expiration=86400):
    redis_client.setex(key, expiration, pickle.dumps(value))

  @staticmethod
  def get(key):
    cached_result = redis_client.get(key)
    return pickle.loads(cached_result) if cached_result else None