import sys
import os

# 添加父目录到sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

import traceback, time

from tqdm import tqdm

from datasource.spy import Spy
from webapp.model.session import Session
from webapp.model.rs import RS
from webapp.model.multiline import Multiline
from common.const import RootKeywords
from common.logger import logger

def collect_rs(rk: str, sess: Session):
  for i in range(5):
    try:
      spy = Spy(0)
      related_queries = spy.query_related_search(rk, sess=sess).get('rising').to_records(index=False)
      for rs in related_queries:
        if RS.validate(rs[0]) and not RS.exists(rs[0], sess.uuid):
          rs = RS.create(
            rs=rs[0],
            rk=rk,
            session_uuid=sess.uuid
          )
          RS.conn.session.add(rs)
      RS.conn.session.commit()
      break
    except IndexError as e:
      break
    except Exception as e:
      logger.warning(f'Failed to collect rs for {rk}: {e}, retrying for {i} times')
      traceback.print_exc()
      j = i 
      if i > 1:
        j=2
      time.sleep(60 * (j) + 10)

def collect_multiline(rs: RS, sess: Session):
  for i in range(5):
    try:
      spy = Spy(0)
      multiline, ref = spy.query_multiline(rs.rs, sess=sess)
      multiline.drop(['isPartial'], axis=1, inplace=True)
      Multiline.create_from_df(multiline, rskw=rs.rs, rs_uuid=rs.uuid, ref=ref)
      break
    except AttributeError as e:
      logger.warning(f'raw data is invalid for {rs.rs}: {e}, exit')
      break
    except Exception as e:
      logger.warning(f'Failed to collect multiline for {rs.rs}: {e}, retrying for {i} times')
      traceback.print_exc()
      j = i 
      if i > 1:
        j=2
      time.sleep(60 * (j) + 10)

def main(geo: str, timeframe: str):
  sess = Session.create(
    geo=geo,
    timeframe=timeframe
  )
  for rk in tqdm(RootKeywords, total=len(RootKeywords), desc='Collecting RS'):
    collect_rs(rk, sess=sess) 

  rss = RS.conn.session.query(RS).filter(RS.session_uuid==sess.uuid).all()

  for rs in tqdm(rss, total=len(rss), desc='Collecting Multiline'):
    collect_multiline(rs, sess=sess)

if __name__ == '__main__':
  main('', 'now 7-d')
