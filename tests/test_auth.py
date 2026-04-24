import pytest_check as check

import app as app_module


def test_login_page_available(client):
    response = client.get('/login')
    assert response.status_code == 200


def test_register_page_available(client):
    response = client.get('/register')
    assert response.status_code == 200


def test_index_requires_login(client):
    response = client.get('/', follow_redirects=False)
    check.equal(response.status_code, 302)
    check.is_in('/login', response.location)


def test_stats_requires_login(client):
    response = client.get('/stats', follow_redirects=False)
    check.equal(response.status_code, 302)
    check.is_in('/login', response.location)


def test_register_creates_user(client):
    response = client.post(
        '/register',
        data={'username': 'bob', 'password': 'qwerty'},
        follow_redirects=False,
    )
    check.equal(response.status_code, 302)

    user = app_module.User.query.filter_by(username='bob').first()
    check.is_not_none(user)
    check.not_equal(user.password_hash, 'qwerty', msg='Пароль должен храниться в виде хеша')
    check.is_true(user.check_password('qwerty'))


def test_register_rejects_duplicate(client, registered_user):
    client.post('/register', data=registered_user, follow_redirects=True)
    users = app_module.User.query.filter_by(username=registered_user['username']).all()
    check.equal(len(users), 1)


def test_login_with_correct_credentials(client, registered_user):
    response = client.post('/login', data=registered_user, follow_redirects=True)
    check.equal(response.status_code, 200)
                                                                               
    check.is_in('Тренажер', response.get_data(as_text=True))


def test_login_with_wrong_password(client, registered_user):
    bad_creds = {'username': registered_user['username'], 'password': 'wrong-password'}
    client.post('/login', data=bad_creds, follow_redirects=True)

                                           
    response = client.get('/', follow_redirects=False)
    check.equal(response.status_code, 302)


def test_logout_clears_session(logged_in_client):
    logged_in_client.get('/logout', follow_redirects=True)
    response = logged_in_client.get('/stats', follow_redirects=False)
    assert response.status_code == 302
