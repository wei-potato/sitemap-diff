import traceback, time

from flask import Blueprint, request, jsonify

from webapp.model.session import Session
from webapp.model.rs import RS
from datasource.spy import Spy
from common.logger import logger

session = Blueprint('session', __name__, url_prefix='/session')

@session.route('/<uuid>/rs', methods=['POST'])
def collect_rs_by_session_uuid(uuid):
  data = request.json
  rk = data.get('rk')
  sess = Session.conn.session.query(Session).filter(Session.uuid == uuid).first()
  for i in range(5):
    try:
      spy = Spy(i)
      related_queries = spy.query_related_search(rk, sess=sess).get('rising').to_records(index=False)
      for rs in related_queries:
        if RS.validate(rs[0]) and not RS.exists(rs[0], uuid):
          rs = RS.create(
            rs=rs[0],
            rk=rk,
            session_uuid=uuid
          )
          RS.conn.session.add(rs)
      RS.conn.session.commit()
      return jsonify({'uuid': uuid})
    except IndexError as e:
      logger.warning(f'No related search for {rk}: {e}, exit')
      break
    except Exception as e:
      logger.warning(f'Failed to collect rs for {rk}: {e}, retrying for {i} times')
      traceback.print_exc()
      time.sleep(60)
  return jsonify({'errmsg': f'Failed to collect rs for {rk}'}), 500