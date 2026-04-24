import pytest_check as check

import app as app_module


def test_index_renders_random_text(logged_in_client):
    response = logged_in_client.get('/')
    assert response.status_code == 200
    body = response.get_data(as_text=True)

                                                          
    import re
    match = re.search(r'const targetText = "([^"]+)"', body)
    check.is_not_none(match, msg='На странице должен быть targetText с текстом для набора')
    if match:
        check.is_true(len(match.group(1)) > 0, msg='targetText не должен быть пустым')


def test_save_stats_creates_record(logged_in_client):
    response = logged_in_client.post(
        '/save_stats',
        json={'wpm': 200, 'accuracy': 90},
    )
    assert response.status_code == 200
    data = response.get_json()

    check.is_true(data['success'])
    check.equal(data['gained_xp'], int(200 * 0.90))       

    user = app_module.User.query.filter_by(username='alice').first()
    check.equal(len(user.stats), 1)
    check.equal(user.stats[0].wpm, 200)
    check.equal(user.stats[0].accuracy, 90)


def test_zero_accuracy_gives_zero_xp(logged_in_client):
    response = logged_in_client.post(
        '/save_stats',
        json={'wpm': 150, 'accuracy': 0},
    )
    assert response.get_json()['gained_xp'] == 0


def test_level_up_on_enough_xp(logged_in_client):
                                                              
    response = logged_in_client.post(
        '/save_stats',
        json={'wpm': 100, 'accuracy': 100},
    )
    data = response.get_json()
    check.is_true(data['leveled_up'])
    check.equal(data['new_level'], 2)

    user = app_module.User.query.filter_by(username='alice').first()
    check.equal(user.level, 2)
    check.equal(user.xp, 0)                    


def test_multiple_level_ups_in_one_submission(logged_in_client):
                                                                                   
                                               
    response = logged_in_client.post(
        '/save_stats',
        json={'wpm': 300, 'accuracy': 100},
    )
    data = response.get_json()
    check.equal(data['new_level'], 3)


def test_stats_page_shows_history(logged_in_client):
    for wpm in (120, 140, 160):
        logged_in_client.post('/save_stats', json={'wpm': wpm, 'accuracy': 95})

    response = logged_in_client.get('/stats')
    assert response.status_code == 200
    body = response.get_data(as_text=True)
    for wpm in (120, 140, 160):
        check.is_in(str(wpm), body)


def test_errors_by_char_increment_counters(logged_in_client):
    logged_in_client.post('/save_stats', json={
        'wpm': 100, 'accuracy': 80,
        'errors_by_char': {'ж': 3, 'ъ': 1}
    })
    logged_in_client.post('/save_stats', json={
        'wpm': 100, 'accuracy': 80,
        'errors_by_char': {'ж': 2, 'э': 5}
    })

    response = logged_in_client.get('/api/weak_keys')
    data = response.get_json()

    check.equal(data['errors']['ж'], 5)                        
    check.equal(data['errors']['ъ'], 1)
    check.equal(data['errors']['э'], 5)
    check.equal(data['max'], 5)


def test_errors_by_char_ignores_bad_input(logged_in_client):
    response = logged_in_client.post('/save_stats', json={
        'wpm': 100, 'accuracy': 100,
        'errors_by_char': {
            'ab': 1,                                      
            'ж': 'not-int',                                 
            'ш': -3,                                  
            'ц': 2,                  
            '': 5,                                    
        }
    })
    assert response.status_code == 200

    response = logged_in_client.get('/api/weak_keys')
    errors = response.get_json()['errors']
    check.equal(errors, {'ц': 2})


def test_weak_keys_empty_for_new_user(logged_in_client):
    response = logged_in_client.get('/api/weak_keys')
    data = response.get_json()
    check.equal(data['errors'], {})
    check.equal(data['max'], 0)
