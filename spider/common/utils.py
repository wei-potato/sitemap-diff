import hashlib

def md5(s: str | bytes):
  if isinstance(s, str):
    s = s.encode()
  return hashlib.md5(s).hexdigest()
