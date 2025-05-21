import os, sys

mysql_uri = os.environ.get('MYSQL_URI', 'mysql+pymysql://root:duwei123@localhost/googletrend')
proxy = 'brd-customer-hl_0842853d-zone-datacenter_proxy1:q3d2vxm3uq66@brd.superproxy.io:33335'
redis_host = os.environ.get('REDIS_HOST', '139.224.31.38')
redis_pass = os.environ.get('REDIS_PASS', 'lanxiaocong123')

config_vars = [x for x in dir() if not x.startswith('__') and x not in [
  'os', 'sys',
  'remote_mysql_host', 'remote_mysql_user', 'remote_mysql_pass', 'remote_mysql_db'
]]

current_module = sys.modules[__name__]

for varname in config_vars:
  value = getattr(current_module, varname)
  if value is None:
    print(f"Error: Fail to start project. \nMissing environment variable for '{varname}'")
    sys.exit(1)  # 终止程序执行

# 创建必须的隐藏目录

os.makedirs('logs', exist_ok=True)
os.makedirs('.images', exist_ok=True)