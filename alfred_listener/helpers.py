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
