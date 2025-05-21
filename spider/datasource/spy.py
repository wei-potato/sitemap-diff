from random import randint

from fake_useragent import UserAgent
from trendspy import Trends

from webapp.model.session import Session
from common.config import proxy
from common.const import TopWebsites

ua = UserAgent()

def get_random_referer():
  return f'https://{TopWebsites[randint(0, len(TopWebsites) - 1)]}'

class Spy:
  
  def __init__(self, delay: int = 0):
    self.spy = Trends(request_delay=2 + 60 * delay, proxy=proxy)

  def query_related_search(self, keyword: str, sess: Session):
    referer = get_random_referer()
    res = self.spy.related_queries(
      keyword,
      timeframe=sess.timeframe,
      geo=sess.geo,
      headers={'referer': referer}
    )
    return res
  
  def query_multiline(self, keyword: str, sess: Session, reference: str = 'gpts'):
    referer = get_random_referer()
    res = self.spy.interest_over_time(
      [keyword, reference],
      timeframe=sess.timeframe,
      geo=sess.geo,
      headers={'referer': referer}
    )
    return res, reference
 