from sqlalchemy import create_engine, Engine, text
from sqlalchemy.orm import sessionmaker, scoped_session
from sqlalchemy.exc import OperationalError, DisconnectionError, SQLAlchemyError

from spider.common import config
from spider.common.logger import logger

class SQLAlchemyConnection:

    _instance = None
    
    __engine: Engine = None

    __logger = logger

    @staticmethod
    def get_instance():
        if SQLAlchemyConnection._instance is None:
            SQLAlchemyConnection._instance = SQLAlchemyConnection()
        return SQLAlchemyConnection._instance

    def __init__(self):
        if SQLAlchemyConnection._instance is not None:
            raise Exception("This is a singleton class. Use get_instance() method.")
        self._conn()
        SQLAlchemyConnection._instance = self

    def _conn(self):
        self.__engine = self.__connect(config.mysql_uri)
        self.__session_maker = scoped_session(sessionmaker(bind=self.__engine))

    def _get_session(self):
        session = self.__session_maker()
        session.connection()
        return session

    @property
    def session(self):
        session = self._get_session()
        try:
            session.execute(text("SELECT 1"))
            return session
        except (OperationalError, DisconnectionError, SQLAlchemyError) as e:
            self.__logger.error(f"数据库连接失败: {e}")
            session.rollback()
            session.close()
            # 重新连接数据库
            self._conn()
            return self._get_session()
    
    def __connect(self, database_url):
        """
        使用 SQLAlchemy 创建数据库引擎和会话
        """
        try:
            engine = create_engine(
                database_url,
                pool_size=20,          # 连接池大小降低为20
                max_overflow=10,       # 超过连接池大小时额外创建的连接数
                pool_timeout=30,       # 连接池中没有可用连接时的等待时间增加到30秒
                pool_recycle=1800,
                echo=False,
                # isolation_level="AUTOCOMMIT",
                pool_pre_ping=True,
                connect_args={
                    'connect_timeout': 30,  # 连接超时增加到30秒
                    'read_timeout': 30,     # 读取超时增加到30秒
                    'write_timeout': 30     # 写入超时增加到30秒
                }
            )
            self.__logger.info('数据库连接成功')
            return engine
        except SQLAlchemyError as e:
            self.__logger.error(f"数据库连接失败: {e}")
            raise  # 重新抛出异常，让调用者知道连接失败

    def close(self):
        self.__session_maker.remove()
