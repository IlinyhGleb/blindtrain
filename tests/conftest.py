import os
import tempfile

import pytest

import app as app_module


@pytest.fixture
def client():
    db_fd, db_path = tempfile.mkstemp(suffix='.db')

    app_module.app.config.update(
        TESTING=True,
        SQLALCHEMY_DATABASE_URI=f'sqlite:///{db_path}',
        WTF_CSRF_ENABLED=False,
        SECRET_KEY='test-secret',
    )

    with app_module.app.app_context():
        app_module.db.create_all()
        with app_module.app.test_client() as test_client:
            yield test_client
        app_module.db.session.remove()
        app_module.db.drop_all()

    os.close(db_fd)
    os.unlink(db_path)


@pytest.fixture
def registered_user(client):
    creds = {'username': 'alice', 'password': 'secret123'}
    client.post('/register', data=creds, follow_redirects=True)
    return creds


@pytest.fixture
def logged_in_client(client, registered_user):
    client.post('/login', data=registered_user, follow_redirects=True)
    return client
