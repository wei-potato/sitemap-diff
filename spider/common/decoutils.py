import inspect

def is_method(func):
  args = list(inspect.signature(func).parameters.values())
  return args and args[0].name in ['self', 'cls']

def extract_real_args(func, *args, **kwargs):
  if is_method(func):
    return args[1:], kwargs
  return args, kwargs