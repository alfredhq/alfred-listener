import msgpack
import zmq

from flask import current_app
from alfred_db.models import Report, Commit
from .database import db


def get_shell():
    try:
        from IPython.frontend.terminal.embed import InteractiveShellEmbed
    except ImportError:
        import code
        return lambda **context: code.interact('', local=context)
    else:
        ipython = InteractiveShellEmbed(banner1='')
        return lambda **context: ipython(global_ns={}, local_ns=context)


def parse_hook_data(data):
    hash = data.get('after')
    compare_url = data.get('compare')
    ref = data.get('ref')
    commit = data.get('head_commit')
    committer = commit.get('committer')
    committer_name = committer.get('name')
    committer_email = committer.get('email')

    return {
        'hash': hash,
        'compare_url': compare_url,
        'ref': ref,
        'committer_name': committer_name,
        'committer_email': committer_email,
        'message': commit['message'],
    }


def report_for_payload(payload_data, repository):
    hook_data = parse_hook_data(payload_data)
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
        db.session.flush()
    report = Report(commit_id=commit.id)
    db.session.add(report)
    db.session.commit()
    return report


def push_report_data(report):
    repository = report.commit.repository
    context = zmq.Context.instance()
    socket = context.socket(zmq.PUSH)
    socket.connect(current_app.config['COORDINATOR'])
    msg = msgpack.packb({
        'report_id': report.id,
        'owner_name': repository.owner_name,
        'repo_name': repository.name,
        'hash': report.commit.hash
    })
    socket.send(msg)
    socket.close()
