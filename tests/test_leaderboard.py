import pytest_check as check

import app as app_module


def _create_user(username, level=1, xp=0, hidden=False):
    user = app_module.User(username=username, level=level, xp=xp,
                           hidden_in_leaderboard=hidden)
    user.set_password('x')
    app_module.db.session.add(user)
    app_module.db.session.commit()
    return user


def _add_stat(user_id, wpm, accuracy):
    app_module.db.session.add(
        app_module.Stat(user_id=user_id, wpm=wpm, accuracy=accuracy)
    )
    app_module.db.session.commit()


def test_leaderboard_level_sorts_by_level_then_xp(logged_in_client):
    with app_module.app.app_context():
        _create_user('bob',     level=5, xp=50)
        _create_user('charlie', level=5, xp=10)                              
        _create_user('dave',    level=7, xp=0)                

    rows = app_module._leaderboard_rows_by_level()
                                                                               
    usernames = [r['username'] for r in rows]
    check.equal(usernames[0], 'dave')
    check.equal(usernames[1], 'bob')
    check.equal(usernames[2], 'charlie')
    check.is_in('alice', usernames)


def test_leaderboard_speed_ignores_low_accuracy(logged_in_client):
    with app_module.app.app_context():
        bob = _create_user('bob', level=1, xp=0)
                                                        
        _add_stat(bob.id, wpm=500, accuracy=50)
                             
        _add_stat(bob.id, wpm=100, accuracy=95)

    rows = app_module._leaderboard_rows_by_speed()
    bob_row = next(r for r in rows if r['username'] == 'bob')
                                                                      
    check.equal(bob_row['metric_value'], 100)


def test_leaderboard_speed_users_without_qualifying_sessions_go_last(logged_in_client):
    with app_module.app.app_context():
        bob = _create_user('bob', level=1, xp=0)
        _add_stat(bob.id, wpm=150, accuracy=95)

        charlie = _create_user('charlie', level=1, xp=0)
                                          
        _add_stat(charlie.id, wpm=400, accuracy=60)

    rows = app_module._leaderboard_rows_by_speed()
    usernames = [r['username'] for r in rows]
                                                               
    check.is_true(usernames.index('bob') < usernames.index('charlie'))


def test_paginate_shows_me_if_outside_top(logged_in_client):
    with app_module.app.app_context():
                                             
        for i in range(25):
            _create_user(f'user{i}', level=10, xp=100 - i)
                                                                          

    rows = app_module._leaderboard_rows_by_level()
    alice = app_module.User.query.filter_by(username='alice').first()
    result = app_module._paginate_leaderboard(rows, alice.id, top_n=20)

    check.equal(len(result['top']), 20)
    check.is_not_none(result['me'], msg='Должна быть отдельная строка "моё место"')
    check.equal(result['my_position'], 26)                                     


def test_paginate_does_not_duplicate_me_when_in_top(logged_in_client):
    with app_module.app.app_context():
                                                                  
        _create_user('bob', level=5, xp=0)

    rows = app_module._leaderboard_rows_by_level()
    alice = app_module.User.query.filter_by(username='alice').first()
    result = app_module._paginate_leaderboard(rows, alice.id, top_n=20)

    check.is_none(result['me'])
    check.is_none(result['my_position'])
                  
    alice_in_top = any(r['user_id'] == alice.id for r in result['top'])
    check.is_true(alice_in_top)


def test_leaderboard_page_shows_anon_for_hidden_users(logged_in_client):
    with app_module.app.app_context():
        _create_user('secretuser', level=10, xp=50, hidden=True)

    response = logged_in_client.get('/leaderboard?tab=level')
    body = response.get_data(as_text=True)

    check.is_not_in('secretuser', body, msg='Скрытый ник не должен светиться')
    check.is_in('Аноним', body)


def test_leaderboard_page_shows_own_username_even_when_hidden(logged_in_client):
    with app_module.app.app_context():
        alice = app_module.User.query.filter_by(username='alice').first()
        alice.hidden_in_leaderboard = True
        app_module.db.session.commit()

    response = logged_in_client.get('/leaderboard?tab=level')
    body = response.get_data(as_text=True)

                                                     
    check.is_in('alice', body, msg='Свой ник должен быть виден самому себе')


def test_api_user_settings_updates_hidden_flag(logged_in_client):
    response = logged_in_client.post('/api/user_settings',
                                     json={'hidden_in_leaderboard': True})
    data = response.get_json()
    check.is_true(data['success'])
    check.is_true(data['hidden_in_leaderboard'])

    alice = app_module.User.query.filter_by(username='alice').first()
    check.is_true(alice.hidden_in_leaderboard)

             
    logged_in_client.post('/api/user_settings',
                          json={'hidden_in_leaderboard': False})
    alice = app_module.User.query.filter_by(username='alice').first()
    check.is_false(alice.hidden_in_leaderboard)


def test_api_user_settings_requires_login(client):
    response = client.post('/api/user_settings',
                           json={'hidden_in_leaderboard': True})
                                      
    check.equal(response.status_code, 302)


def test_leaderboard_page_renders(logged_in_client):
    response = logged_in_client.get('/leaderboard')
    assert response.status_code == 200
    body = response.get_data(as_text=True)
    check.is_in('Рейтинг', body)
    check.is_in('По уровню', body)
    check.is_in('По лучшей скорости', body)


def test_leaderboard_page_unknown_tab_defaults_to_level(logged_in_client):
    response = logged_in_client.get('/leaderboard?tab=foobar')
    assert response.status_code == 200


def test_leaderboard_speed_tab_renders(logged_in_client):
    response = logged_in_client.get('/leaderboard?tab=speed')
    assert response.status_code == 200
    body = response.get_data(as_text=True)
                      
    check.is_in('is-active', body)
