import pytest_check as check

import app as app_module


def _pass(client, **kwargs):
    payload = {'wpm': 100, 'accuracy': 95, 'text_length': 80}
    payload.update(kwargs)
    return client.post('/save_stats', json=payload)


def _earned_codes(username='alice'):
    user = app_module.User.query.filter_by(username=username).first()
    return {a.code for a in app_module.Achievement.query.filter_by(user_id=user.id).all()}


def test_no_achievements_for_noop_user(logged_in_client):
    check.equal(_earned_codes(), set())


def test_first_perfect_session_earned(logged_in_client):
    response = _pass(logged_in_client, accuracy=100, text_length=60, wpm=120)
    data = response.get_json()

    codes = [ach['code'] for ach in data['new_achievements']]
    check.is_in('perfect_session', codes)
                                   
    for ach in data['new_achievements']:
        check.is_in('title', ach)
        check.is_in('description', ach)
        check.is_in('icon', ach)


def test_perfect_session_requires_min_text_length(logged_in_client):
    response = _pass(logged_in_client, accuracy=100, text_length=30)
    codes = [ach['code'] for ach in response.get_json()['new_achievements']]
    check.is_not_in('perfect_session', codes)


def test_zero_errors_long_requires_long_text(logged_in_client):
                        
    response = _pass(logged_in_client, accuracy=100, text_length=100)
    codes = {ach['code'] for ach in response.get_json()['new_achievements']}
    check.is_not_in('zero_errors_long', codes)

                    
    response = _pass(logged_in_client, accuracy=100, text_length=200)
    codes = {ach['code'] for ach in response.get_json()['new_achievements']}
    check.is_in('zero_errors_long', codes)


def test_achievement_given_only_once(logged_in_client):
                                              
    r1 = _pass(logged_in_client, accuracy=100, text_length=80)
    codes_1 = {ach['code'] for ach in r1.get_json()['new_achievements']}
    check.is_in('perfect_session', codes_1)

                                                                     
    r2 = _pass(logged_in_client, accuracy=100, text_length=80)
    codes_2 = {ach['code'] for ach in r2.get_json()['new_achievements']}
    check.is_not_in('perfect_session', codes_2)


def test_speed_achievements_require_accuracy(logged_in_client):
    response = _pass(logged_in_client, wpm=150, accuracy=85, text_length=80)
    codes = {ach['code'] for ach in response.get_json()['new_achievements']}
    check.is_not_in('speed_100', codes)
    check.is_not_in('speed_150', codes)


def test_speed_achievements_cascade(logged_in_client):
    response = _pass(logged_in_client, wpm=200, accuracy=95, text_length=80)
    codes = {ach['code'] for ach in response.get_json()['new_achievements']}
    check.is_in('speed_100', codes)
    check.is_in('speed_150', codes)
    check.is_in('speed_200', codes)
    check.is_not_in('speed_300', codes)                          


def test_ten_sessions_after_ten_submits(logged_in_client):
    for i in range(9):
        r = _pass(logged_in_client, wpm=50, accuracy=80, text_length=60)
        codes = {ach['code'] for ach in r.get_json()['new_achievements']}
        check.is_not_in('ten_sessions', codes,
                        msg=f'ten_sessions выдано раньше времени (сабмит {i+1})')

    r = _pass(logged_in_client, wpm=50, accuracy=80, text_length=60)
    codes = {ach['code'] for ach in r.get_json()['new_achievements']}
    check.is_in('ten_sessions', codes, msg='ten_sessions должно выдаться на 10-м сабмите')


def test_three_perfect_in_a_row(logged_in_client):
                          
    _pass(logged_in_client, accuracy=100, text_length=60)
    r2 = _pass(logged_in_client, accuracy=100, text_length=60)
    codes_2 = {ach['code'] for ach in r2.get_json()['new_achievements']}
    check.is_not_in('three_perfect', codes_2)

                               
    r3 = _pass(logged_in_client, accuracy=100, text_length=60)
    codes_3 = {ach['code'] for ach in r3.get_json()['new_achievements']}
    check.is_in('three_perfect', codes_3)


def test_three_perfect_broken_by_bad_session(logged_in_client):
    _pass(logged_in_client, accuracy=100, text_length=60)
    _pass(logged_in_client, accuracy=100, text_length=60)
                                 
    _pass(logged_in_client, accuracy=90, text_length=60)
                                                       
    r = _pass(logged_in_client, accuracy=100, text_length=60)
    codes = {ach['code'] for ach in r.get_json()['new_achievements']}
    check.is_not_in('three_perfect', codes)


def test_streak_3_earned_on_third_day(logged_in_client):
    from datetime import date
    from unittest.mock import patch

    with patch.object(app_module, '_today', return_value=date(2026, 4, 20)):
        _pass(logged_in_client)
    with patch.object(app_module, '_today', return_value=date(2026, 4, 21)):
        _pass(logged_in_client)
    with patch.object(app_module, '_today', return_value=date(2026, 4, 22)):
        r = _pass(logged_in_client)

    codes = {ach['code'] for ach in r.get_json()['new_achievements']}
    check.is_in('streak_3', codes)


def test_achievements_page_renders(logged_in_client):
    response = logged_in_client.get('/achievements')
    assert response.status_code == 200
    body = response.get_data(as_text=True)
    check.is_in('Достижения', body)
    check.is_in('Прогресс по урокам', body)
    check.is_in('Серии', body)
    check.is_in('Скорость', body)


def test_achievements_page_shows_earned_count(logged_in_client):
                             
    _pass(logged_in_client, accuracy=100, text_length=80)

    response = logged_in_client.get('/achievements')
    body = response.get_data(as_text=True)
    total = len(app_module.ACHIEVEMENTS)
                                 
    check.is_in('из ' + str(total), body)


def test_achievements_page_shows_all_titles(logged_in_client):
    response = logged_in_client.get('/achievements')
    body = response.get_data(as_text=True)
    for meta in app_module.ACHIEVEMENTS.values():
        check.is_in(meta['title'], body,
                    msg=f'Отсутствует заголовок "{meta["title"]}"')


def test_save_stats_always_returns_new_achievements_field(logged_in_client):
    response = _pass(logged_in_client, wpm=10, accuracy=50, text_length=10)
    data = response.get_json()
    check.is_in('new_achievements', data)
    check.is_true(isinstance(data['new_achievements'], list))
