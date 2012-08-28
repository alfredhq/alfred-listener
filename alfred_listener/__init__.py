import os

from flask import Flask
from flask_alfred_db import AlfredDB

from .config import configure


db = AlfredDB()


def create_app(config):
    app = Flask(__name__)
    configure(app, config)
    db.init_app(app)
    return app
