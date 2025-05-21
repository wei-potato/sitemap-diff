import enum, os, asyncio
from functools import wraps

from pandas import DataFrame

from .redis import RedisCache
from common.logger import logger
from common.utils import md5
from common.decoutils import extract_real_args

class ReservedKeys(enum.Enum):
  CACHEKEY = '__cachekey__'
  NOCACHE = '__nocache__'

class CacheBase(enum.Enum):
  REDIS = RedisCache

VALID_ARG_TYPES = (int, str, float, bool)

def _validate_arg(arg):
  if isinstance(arg, VALID_ARG_TYPES):
    return
  if isinstance(arg, list):
    for item in arg:
      _validate_arg(item)
    return
  if isinstance(arg, dict):
    for k, v in arg.items():
      _validate_arg(k)
      _validate_arg(v)
    return
  if isinstance(arg, enum.Enum):
    _validate_arg(arg.value)
    return
  raise TypeError(f"Invalid argument type: {type(arg)}")

def _delete_reserved_keys(kwargs: dict):
  kwargs = {k: v for k ,v in kwargs.items() if k not in [k.value for k in ReservedKeys]}
  return kwargs

def _validate_args(func, *args, **kwargs):
  args, kwargs = extract_real_args(func, *args, **kwargs)
  if kwargs.get(ReservedKeys.CACHEKEY.value, None) is not None:
    return
  for arg in args:
    _validate_arg(arg)
  for k, v in kwargs.items():
    _validate_arg(k)
    _validate_arg(v)

def _strfy_arg(obj):
  if isinstance(obj, VALID_ARG_TYPES):
    return str(obj)
  if isinstance(obj, list):
    return '-'.join([_strfy_arg(item) for item in obj])
  if isinstance(obj, dict):
    return '-'.join([f"{_strfy_arg(k)}-{_strfy_arg(v)}" for k, v in obj.items()])
  if isinstance(obj, enum.Enum):
    return _strfy_arg(obj.value)
  raise TypeError(f"Invalid argument type: {type(obj)}")

def _format_cachekey(func, key: str):
  return f"samwise-cache:{func.__module__}:{func.__name__}:{key}"

def _key(func, *args, **kwargs) -> str:
  if (cachekey := kwargs.pop(ReservedKeys.CACHEKEY.value, None)):
    return _format_cachekey(func, md5(cachekey))
  args, kwargs = extract_real_args(func, *args, **kwargs)
  keystrs = []
  for arg in args:
    keystrs.append(_strfy_arg(arg))
  for k, v in kwargs.items():
    keystrs.append(f"{_strfy_arg(k)}-{_strfy_arg(v)}")
  key = md5('.'.join(keystrs))
  return _format_cachekey(func, key)

def _use_cache(**kwargs):
  nocache = kwargs.pop(ReservedKeys.NOCACHE.value, False)
  SYS_USE_CACHE = int(os.environ.get('USE_REDIS_CACHE', 1)) > 0
  return not nocache and SYS_USE_CACHE

def _sync_apply(base: CacheBase, key, expiration, func, *args, **kwargs):
  result = func(*args, **_delete_reserved_keys(kwargs))
  base.value.put(key, result, expiration)
  return base.value.get(key)

async def _async_apply(base: CacheBase, key, expiration, func, *args, **kwargs):
  result = await func(*args, **_delete_reserved_keys(kwargs))
  base.value.put(key, result, expiration)
  return result

def _fetch_in_cache(base: CacheBase, key):
  cached_result = base.value.get(key)
  if cached_result is not None:
    logger.info(f"缓存命中: {key}")
    return cached_result
  else:
    logger.info(f"缓存未命中: {key}")
    return None
  
def _validate_and_get_key(func, *args, **kwargs) -> str:
  _validate_args(func, *args, **kwargs)
  return _key(func, *args, **kwargs)

def _decorate(base: CacheBase, expiration: int):
  def decorator(func):
    @wraps(func)
    def sync_wrapper(*args, **kwargs):
      key = _validate_and_get_key(func, *args, **kwargs)
      if _use_cache(**kwargs):
        try:
          if (result := _fetch_in_cache(base, key)) is not None:
            return result
        except ModuleNotFoundError as e:
          logger.error(f'{e}, using remote resource')
      return _sync_apply(base, key, expiration, func, *args, **kwargs)
      
    @wraps(func)
    async def async_wrapper(*args, **kwargs):
      key = _validate_and_get_key(func, *args, **kwargs)
      if _use_cache(**kwargs):
        try: 
          if (result := _fetch_in_cache(base, key)) is not None:
            return result
        except ModuleNotFoundError as e:
          logger.error(f'{e}, using remote resource')
      return await _async_apply(base, key, expiration, func, *args, **kwargs)
    
    if asyncio.iscoroutinefunction(func):
      return async_wrapper
    else:
      return sync_wrapper
  return decorator

class Cache:
  @staticmethod
  def redis(expiration=86400):
    return _decorate(CacheBase.REDIS, expiration)