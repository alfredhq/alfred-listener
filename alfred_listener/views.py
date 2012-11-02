from flask import Blueprint, request, json, abort
from alfred_db.models import Repository

from .database import db
from .helpers import report_for_payload, push_report_data


webhooks = Blueprint('webhooks', __name__)


@webhooks.route('/', methods=['POST'])
def handler():
    event = request.headers.get('X-Github-Event')
    if event != 'push':
        abort(400)
    payload = request.form.get('payload')
    token = request.args.get('token')
    if token is None:
        abort(400)

    repository = db.session.query(Repository.id).filter_by(
        token=token
    ).first()
    if repository is None:
        abort(404)

    try:
        payload_data = json.loads(payload)
    except (ValueError, TypeError):
        abort(400)

    report = report_for_payload(payload_data, repository)
    push_report_data(report)

    return 'OK'
