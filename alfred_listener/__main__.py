#!/usr/bin/env python

import os
from argh import arg, ArghParser
from functools import wraps


def with_app(func):
    @wraps(func)
    @arg('--config', help='Path to config file', required=True)
    def wrapper(*args, **kwargs):
        config = args[0].config
        from alfred_listener import create_app
        app = create_app(config)
        return func(app, *args, **kwargs)
    return wrapper


@arg('--host', default='127.0.0.1', help='the host')
@arg('--port', default=5000, help='the port')
@arg('--noreload', action='store_true', help='disable code reloader')
@with_app
def runserver(app, args):
    app.run(args.host, args.port, use_reloader=not args.noreload)


@with_app
def shell(app, args):
    from alfred_listener.helpers import get_shell
    with app.test_request_context():
        sh = get_shell()
        sh(app=app)


def main():
    parser = ArghParser()
    parser.add_commands([runserver, shell])
    parser.dispatch()


if __name__ == '__main__':
    main()
