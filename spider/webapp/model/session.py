from uuid import uuid4
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, String

from .base import BaseModel

class Session(BaseModel):
  __tablename__ = 'session'

  uuid = Column(String, nullable=False, primary_key=True)
  geo = Column(String, nullable=True)
  timeframe = Column(String, nullable=True)
  created_at = Column(DateTime, nullable=False)

  @classmethod
  def create(cls, geo:str, timeframe:str):
    instance = cls(
      uuid=uuid4().hex,
      geo=geo,
      timeframe=timeframe,
      created_at=datetime.now(timezone.utc)
    )
    cls.conn.session.add(instance)
    cls.conn.session.commit()
    return instance