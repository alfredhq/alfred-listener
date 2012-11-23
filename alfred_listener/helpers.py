import msgpack
import zmq

from flask import current_app
from alfred_db.models import Report, Push
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
    commit_hash = data.get('after')
    compare_url = data.get('compare')
    ref = data.get('ref')
    commit = data.get('head_commit')
    committer = commit.get('committer')
    committer_name = committer.get('name')
    committer_email = committer.get('email')

    return {
        'commit_hash': commit_hash,
        'compare_url': compare_url,
        'ref': ref,
        'committer_name': committer_name,
        'committer_email': committer_email,
        'commit_message': commit['message'],
    }


def report_for_payload(payload_data, repository):
    hook_data = parse_hook_data(payload_data)
    push = db.session.query(Push.id).filter_by(
        commit_hash=hook_data['commit_hash'], repository_id=repository.id
    ).first()
    if push is None:
        push = Push(
            repository_id=repository.id,
            ref=hook_data['ref'],
            compare_url=hook_data['compare_url'],
            commit_hash=hook_data['commit_hash'],
            commit_message=hook_data['commit_message'],
            committer_name=hook_data['committer_name'],
            committer_email=hook_data['committer_email'],
        )
        db.session.add(push)
        db.session.flush()
    report = Report(push_id=push.id)
    db.session.add(report)
    db.session.commit()
    return report


def push_report_data(report):
    repository = report.push.repository
    context = zmq.Context.instance()
    socket = context.socket(zmq.PUSH)
    socket.connect(current_app.config['COORDINATOR'])
    msg = msgpack.packb({
        'report_id': report.id,
        'owner_name': repository.owner_name,
        'repo_name': repository.name,
        'hash': report.push.commit_hash
    })
    socket.send(msg)
    socket.close()
