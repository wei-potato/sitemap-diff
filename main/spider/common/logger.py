import logging, os, sys

from loguru import logger as _logger

default_logger = logging.getLogger()
default_logger.setLevel(logging.WARNING)
httpx_logger = logging.getLogger("httpx")
httpx_logger.setLevel(logging.WARNING)
oss2_logger = logging.getLogger("oss2.api")
oss2_logger.setLevel(logging.WARNING)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - \n%(message)s')

loguru_level = os.environ.get('LOG_LEVEL', 'INFO')
logger = _logger
logger.remove()
# logger.level('PERF', no=35, color='<blue>')
logger.level('DEBUG', color='<green>')
logger.level('INFO', color='<cyan>')
logger.level('SUCCESS', color='<green>')
logger.level('WARNING', color='<yellow>')
logger.level('ERROR', color='<red>')
logger.level('CRITICAL', color='<red>')
logger.level('WEBINFO', no=45, color='<blue>')  # 定义 webInfo 级别
logger.level('WPLOG', no=45, color='<blue>')  # 定义 webInfo 级别

logger.perf = lambda message: logger.log('PERF', message)
log_format = "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | {name}:{function}:{line} | \n<level>{message}</level>"
logger.configure(handlers=[{"sink": sys.stdout, "format": log_format, "colorize": True, 'level': loguru_level}])
logger.add("logs/my_app.log", format=log_format, rotation="1 week", compression="zip")
logger.add("logs/errors.log", format=log_format, level="ERROR", rotation="1 day", compression="zip")

def web_info(uuid):
  log_file = f"logs/{uuid}_info.log"
  all_log_file = f"logs/{uuid}_info_all.log"
  logger.add(log_file, format="{message}", level="WEBINFO", rotation="1 day", compression="zip")
  logger.add(all_log_file, format=log_format, retention="1 week", compression="zip")

def wp_log():
  log_file = "logs/wp_{time:YYYY-MM-DD HH:mm:ss}_info.log"
  logger.add(log_file, format=log_format, rotation="1 week", compression="zip")
