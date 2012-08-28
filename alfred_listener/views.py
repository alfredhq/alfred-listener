from flask import Blueprint, request, json
from alfred_db.models import Repository, Commit

from .database import db
from .helpers import parse_hook_data


webhooks = Blueprint('webhooks', __name__)


@webhooks.route('/', methods=['POST'])
def handler():
    payload = request.form.get('payload', '')
    try:
        payload_data = json.loads(payload)
    except ValueError:
        return 'Bad request', 400
    hook_data = parse_hook_data(payload_data)

    repository = db.session.query(Repository).filter_by(
        name=hook_data['repo_name'], user=hook_data['repo_user']
    ).first()
    if repository is None:
        repository = Repository()
        repository.name = hook_data['repo_name']
        repository.user = hook_data['repo_user']
        repository.url = hook_data['repo_url']
        db.session.add(repository)
        db.session.commit()

    commit = db.session.query(Commit).filter_by(
        hash=hook_data['hash'], repository_id=repository.id
    ).first()
    if commit is None:
        commit = Commit()
        commit.repository_id = repository.id
        commit.hash = hook_data['hash']
        commit.ref = hook_data['ref']
        commit.compare_url = hook_data['compare_url']
        commit.committer_name = hook_data['committer_name']
        commit.committer_email = hook_data['committer_email']
        commit.message = hook_data['message']
        db.session.add(commit)
        db.session.commit()
    return 'OK'
