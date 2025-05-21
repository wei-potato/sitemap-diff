import traceback, time

from flask import Blueprint, jsonify

from datasource.spy import Spy
from webapp.model.rs import RS
from webapp.model.session import Session
from webapp.model.multiline import Multiline
from common.logger import logger

rs = Blueprint('rs', __name__, url_prefix='/rs')

@rs.route('/<uuid>', methods=['POST'])
def collect_rs(uuid: str):
  if Multiline.exists(uuid):
    return jsonify({'uuid': uuid})
  rs = RS.conn.session.query(RS).filter(RS.uuid == uuid).first()
  sess = Session.conn.session.query(Session).filter(Session.uuid == rs.session_uuid).first()
  for i in range(5):
    try:
      spy = Spy(i)
      multiline, ref = spy.query_multiline(rs.rs, sess=sess)
      multiline.drop(['isPartial'], axis=1, inplace=True)
      Multiline.create_from_df(multiline, rskw=rs.rs, rs_uuid=uuid, ref=ref)
      return jsonify({'uuid': uuid})
    except AttributeError as e:
      logger.warning(f'raw data is invalid for {rs.rs}: {e}, exit')
      break
    except Exception as e:
      logger.warning(f'Failed to collect multiline for {rs.rs}: {e}, retrying for {i} times')
      traceback.print_exc()
  return jsonify({'errmsg': f'Failed to collect multiline for {rs.rs}'}), 500