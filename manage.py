#!/usr/bin/env python
import os
from app import create_app
from flask.ext.script import Manager
from app import db
from app.models import User

app = create_app(os.getenv('FLASK_CONFIG') or 'default')
manager = Manager(app)


@manager.command
def adduser(username, password, firstname="", lastname="", nickname="", admin=False):
    """Register a new user."""
    db.create_all()
    user = User(username=username, password=password, firstname=lastname, lastname=lastname, nickname=nickname,
                is_admin=admin)
    db.session.add(user)
    db.session.commit()
    print('User {0} was registered successfully.'.format(username))


if __name__ == '__main__':
    manager.run()

