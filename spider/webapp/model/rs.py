from uuid import uuid4
from datetime import datetime, timezone, timedelta

from sqlalchemy import Column, DateTime, String
from sqlalchemy.sql.expression import func

from .base import BaseModel

class RS(BaseModel):
  __tablename__ = 'rs'

  uuid = Column(String, nullable=False, primary_key=True)
  rs = Column(String, nullable=False)
  rk = Column(String, nullable=False)
  session_uuid = Column(String, nullable=False)
  created_at = Column(DateTime, nullable=False)

  @classmethod
  def random_rs(cls):
    return RS.conn.session.query(RS).order_by(func.random()).first()

  @classmethod
  def validate(cls, rs: str):
    return len(rs.split(' ')) < 5
  
  @classmethod
  def exists(cls, rs: str, session_uuid: str):
    return cls.conn.session.query(cls).filter(
      cls.rs == rs,
      cls.session_uuid == session_uuid,
    ).first() is not None

  @classmethod
  def create(cls, rs: str, rk: str, session_uuid: str):
    instance = cls(
      uuid=uuid4(),
      rs=rs,
      rk=rk,
      session_uuid=session_uuid,
      created_at=datetime.now(timezone.utc)
    )
    return instance