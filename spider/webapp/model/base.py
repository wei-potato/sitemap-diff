from datetime import datetime, date

from typing import TypeVar
import pandas as pd
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, DateTime, update, desc

from common.logger import logger
from .db_conn import SQLAlchemyConnection

Base = declarative_base()
T = TypeVar('T', bound='BaseModel')

class BaseModel(Base):

  __allow_unmapped__ = True
  __abstract__ = True
  logger = logger
  conn = SQLAlchemyConnection.get_instance()

  @classmethod
  def new(cls, **kwargs):
    instance = cls(**kwargs)
    instance.save()
    primary_key = [prop for prop in cls._sa_class_manager.mapper._primary_key_propkeys][0]
    primary_value = getattr(instance, primary_key)
    instance = cls.find_one_by(**{primary_key: primary_value})
    return instance

  @classmethod
  def find_one_by(cls, order_by: dict = None, **kwargs):
    kwargs = [getattr(cls, k) == v for k, v in kwargs.items()]
    return cls.conn.session.query(cls).filter(*kwargs).order_by(order_by).first()
    
  @classmethod
  def find(
    cls,
    order_by: dict = None,
    limit: int = 10,
    offset: int = 0,
    **kwargs
  ):
    kwargs = [getattr(cls, k) == v for k, v in kwargs.items()]
    return cls.conn.session.query(cls).filter(*kwargs).order_by(order_by).limit(limit=limit).offset(offset=offset).all()
  
  @classmethod
  def find_in(
    cls,
    order_by: dict = None,
    limit: int = 10,
    offset: int = 0,
    in_ = None,
    **kwargs
  ) -> list:
    kwargs = [getattr(cls, k) == v for k, v in kwargs.items()]
    return cls.conn.session.query(cls).filter(in_).filter(*kwargs).order_by(order_by).limit(limit=limit).offset(offset=offset).all()
  
  @classmethod
  def find_by_page(
    cls,
    page: int = 1,
    limit: int = 10,
    order_by: dict = None,
    **kwargs
  ):
    offset = (page - 1) * limit
    return cls.find(
      order_by=order_by,
      limit=limit,
      offset=offset,
      **kwargs
    )
  
  @classmethod
  def find_all(
    cls,
    order_by: dict = None,
    **kwargs
  ):
    result = []
    page = 1
    while True:
      batch_result = cls.find_by_page(page=page, limit=50, order_by=order_by, **kwargs)
      if not batch_result:
        break
      result.extend(batch_result)
      page += 1
    return result
  
  @classmethod
  def get_all_count_by(cls, **kwargs):
    kwargs = [getattr(cls, k) == v for k, v in kwargs.items()]
    return  cls.conn.session.query(cls).filter(*kwargs).count()
  
  @classmethod
  def count(cls, **kwargs):
    kwargs = [getattr(cls, k) == v for k, v in kwargs.items()]
    return  cls.conn.session.query(cls).filter(*kwargs).count()

  @classmethod
  def delete_many(cls, **kwargs):
    kwargs = [getattr(cls, k) == v for k, v in kwargs.items()]
    cls.conn.session.query(cls).filter(*kwargs).delete()
    cls.conn.session.commit()
  
  @classmethod
  def save_many(cls, instances: list[T]):
    now = datetime.now()
    for instance in instances:
      instance.created_at = now
      instance.updated_at = now
    cls.conn.session.bulk_save_objects(instances)
    cls.conn.session.commit()

  @classmethod
  def update_many(cls, filter_kwargs: dict, update_kwargs: dict):
    now = datetime.now()
    update_kwargs['updated_at'] = now
    stmt = update(cls)
    for key, value in filter_kwargs.items():
      if isinstance(value, list):
        stmt = stmt.where(getattr(cls, key).in_(value))
      else:
        stmt = stmt.where(getattr(cls, key) == value)
    stmt = stmt.values(**update_kwargs)
    cls.conn.session.execute(stmt)
    cls.conn.session.commit()

  @classmethod
  def copy(cls, instance: T):
    return cls(**{k: v for k, v in instance.cols.items() if k != 'id'})
  
  @classmethod
  def copy_many(cls, instances: list[T]):
    return [cls.copy(instance) for instance in instances]
  
  @classmethod
  def find_or_create(cls, **kwargs):
    instance = cls.find_one_by(**kwargs)
    if instance is None:
      instance = cls(**kwargs)
      instance.save()
    return instance
  
  @property
  def cols(self):
    cols = self.__table__.columns
    return {k: v for k, v in self.__dict__.items() if k in cols}
  
  def instantiate(self):
    '''
      Initialize the instance with necessary attributes.
      Auto called by occasion when instance is generated from db query
    '''
    pass

  def set(self, **kwargs):
    kwargs = {k: v for k, v in kwargs.items() if hasattr(self, k)}
    for key, value in kwargs.items():
      setattr(self, key, value)
  
  def refresh(self):
    self.conn.session.refresh(self)
  
  def to_dict(self, str_datetime: bool = False, pickout: list = None):
    relations = {}
    for key, _ in self.__mapper__.relationships.items():
      if pickout is not None and key in pickout:
        continue
      try:
        relations[key] = getattr(self, key).to_dict(str_datetime=True)
      except Exception as e:
        logger.error(f'Error getting relation {key}: {str(e)}')
        raise e
    if str_datetime:
      return {
        **self.cols,
        'created_at': self.created_at_str,
        'updated_at': self.updated_at_str,
        **relations
      }
    else:
      return {
        **self.cols,
        **relations
      }
    
  def delete(self):
    self.conn.session.delete(self)
    self.conn.session.commit()
  
  def __str__(self):
    serie = pd.Series(self.cols)
    return f'''{self.__class__.__name__}\n{serie}'''
  
  @classmethod
  def find_by_date(cls, query_date:date, order_by: dict = None, limit: int = 1000, offset: int = 0, **kwargs):
    start_of_day = datetime.combine(query_date, datetime.min.time())
    end_of_day = datetime.combine(query_date, datetime.max.time())

    # 默认按照 created_at 降序排列
    if order_by is None:
        order_by = {'created_at': 'desc'}

    # 处理 order_by 参数
    order_by_clauses = []
    for column, direction in order_by.items():
        if direction.lower() == 'desc':
            order_by_clauses.append(desc(getattr(cls, column)))
        else:
            order_by_clauses.append(getattr(cls, column))

    kwargs = [getattr(cls, k) == v for k, v in kwargs.items()]
    return cls.conn.session.query(cls).filter(
        cls.created_at >= start_of_day,
        cls.created_at <= end_of_day,
        *kwargs
    ).order_by(*order_by_clauses).limit(limit=limit).offset(offset=offset).all()
  
# def init_instance(target: BaseModel, identifier):
#   target.instantiate()

# listens_for(BaseModel, 'load', propagate=True)(init_instance)