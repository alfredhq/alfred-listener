def get_shell():
    try:
        from IPython.frontend.terminal.embed import InteractiveShellEmbed
    except ImportError:
        import code
        return lambda **context: code.interact('', local=context)
    else:
        ipython = InteractiveShellEmbed(banner1='')
        return lambda **context: ipython(global_ns={}, local_ns=context)
