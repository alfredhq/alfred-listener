from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker

from alfred_db import Session


def init_db(url):
    from alfred_db.models import Base, Commit, Repository
    engine = create_engine(url, convert_unicode=True)
    Base.metadata.create_all(bind=engine)


def get_db_session(url):
    engine = create_engine(url, convert_unicode=True)
    db_session = scoped_session(Session)
    db_session.bind = engine
    return db_session
