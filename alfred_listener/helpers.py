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
    repo = data.get('repository', {})
    repo_url = repo.get('url')
    repo_name = repo.get('name')
    repo_user = repo.get('owner', {}).get('name')

    commit = data.get('head_commit')
    committer = commit.get('committer')
    committer_name = committer.get('name')
    committer_email = committer.get('email')

    return {
        'hash': hash,
        'compare_url': compare_url,
        'ref': ref,
        'repo_url': repo_url,
        'repo_name': repo_name,
        'repo_user': repo_user,
        'committer_name': committer_name,
        'committer_email': committer_email,
        'message': commit['message'],
    }
