from flask import Blueprint, request, json, abort
from alfred_db.models import Repository, Commit

from .database import db
from .helpers import parse_hook_data


webhooks = Blueprint('webhooks', __name__)


@webhooks.route('/', methods=['POST'])
def handler():
    event = request.headers.get('X-Github-Event')
    if event != 'push':
        abort(406)
    payload = request.form.get('payload')
    try:
        payload_data = json.loads(payload)
    except (ValueError, TypeError):
        abort(400)
    hook_data = parse_hook_data(payload_data)

    repository = db.session.query(Repository.id).filter_by(
        name=hook_data['repo_name'], user=hook_data['repo_user']
    ).first()
    if repository is None:
        repository = Repository(
            name=hook_data['repo_name'],
            user=hook_data['repo_user'],
            url=hook_data['repo_url']
        )
        db.session.add(repository)
        db.session.commit()

    commit = db.session.query(Commit.id).filter_by(
        hash=hook_data['hash'], repository_id=repository.id
    ).first()
    if commit is None:
        commit = Commit(
            repository_id=repository.id,
            hash=hook_data['hash'],
            ref=hook_data['ref'],
            compare_url=hook_data['compare_url'],
            committer_name=hook_data['committer_name'],
            committer_email=hook_data['committer_email'],
            message=hook_data['message']
        )
        db.session.add(commit)
        db.session.commit()
    return 'OK'
