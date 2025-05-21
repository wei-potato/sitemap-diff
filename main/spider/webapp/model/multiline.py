from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, String, BIGINT, JSON, Float
from pandas import DataFrame
import numpy as np

from .base import BaseModel

def calculate_geometric_trend_score(data, stability_weight=0.4):
    """
    改进的趋势评分算法:
    1. 评估趋势的持续性
    2. 惩罚剧烈波动
    3. 奖励稳定上升
    4. 考虑整体趋势形状
    
    Parameters:
    data (list): 标准化的7天时间序列数据 (0-100范围)
    stability_weight: 稳定性权重
    
    Returns:
    float: 0-1之间的分数
    """
    series = np.array(data)
    if len(series) < 4:
        return 0.0
        
    # 1. 计算连续性指标（惩罚突变）
    diffs = np.diff(series)
    continuity_score = 1.0 - np.std(diffs) / (np.max(series) - np.min(series) + 1e-6)
    
    # 2. 计算持续增长分数
    # 统计正向变化的比例
    positive_changes = np.sum(diffs > 0) / len(diffs)
    growth_score = positive_changes
    
    # 3. 计算形状分数（惩罚单点尖峰）
    peak_idx = np.argmax(series)
    is_spike = (peak_idx > 0 and peak_idx < len(series) - 1 and 
               series[peak_idx-1] < 0.3 * series[peak_idx] and 
               series[peak_idx+1] < 0.3 * series[peak_idx])
    shape_penalty = 0.2 if is_spike else 1.0
    
    # 4. 计算最终趋势值（相对于起始值）
    trend_strength = (series[-1] - series[0]) / 100.0
    trend_score = max(0, trend_strength)  # 只关注正向趋势
    
    # 综合计算
    stability_score = (continuity_score + growth_score) / 2
    trend_score = trend_score * shape_penalty
    
    final_score = (
        stability_weight * stability_score +
        (1 - stability_weight) * trend_score
    )
    
    return max(0.0, min(1.0, final_score))

class Multiline(BaseModel):
  __tablename__ = 'multiline'

  id = Column(BIGINT, nullable=False, primary_key=True)
  rs_uuid = Column(String, nullable=False)
  metric = Column(JSON, nullable=False)
  benchmark = Column(JSON, nullable=False)
  score = Column(Float, nullable=False)
  created_at = Column(DateTime, nullable=False)

  @classmethod
  def exists(cls, rs_uuid: str):
    return cls.conn.session.query(cls).filter(cls.rs_uuid == rs_uuid).first() is not None
  
  @classmethod
  def create_from_df(cls, df: DataFrame, rskw: str, rs_uuid: str, ref: str):
    data = df.to_dict()
    metric = list(data.get(rskw).values())
    benchmark = list(data.get(ref).values())
    instance = cls(
      rs_uuid=rs_uuid,
      metric=metric,
      benchmark=benchmark,
      score=calculate_geometric_trend_score(metric),
      created_at=datetime.now(timezone.utc)
    )
    cls.conn.session.add(instance)
    cls.conn.session.commit()
