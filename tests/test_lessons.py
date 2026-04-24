import pytest_check as check

import app as app_module


def _pass_exercise(client, accuracy=95):
    return client.post('/save_stats', json={'wpm': 150, 'accuracy': accuracy})


def _complete_lesson(client, accuracy=95):
    for _ in range(app_module.EXERCISES_PER_LESSON):
        _pass_exercise(client, accuracy=accuracy)


def test_lessons_page_accessible(logged_in_client):
    response = logged_in_client.get('/lessons')
    assert response.status_code == 200
    body = response.get_data(as_text=True)
                                                   
    for lesson in app_module.LESSONS:
        check.is_in(lesson.title, body)


def test_first_lesson_is_current_for_new_user(logged_in_client):
    lesson_id = app_module._current_lesson_id(
        app_module.User.query.first().id
    )
    check.equal(lesson_id, 1)


def test_strict_lessons_blocked_until_previous_completed(logged_in_client):
    user_id = app_module.User.query.first().id

    accessible, reason = app_module._is_lesson_accessible(user_id, 2)
    check.is_false(accessible)
    check.is_in('урок 1', reason.lower())

    accessible, _ = app_module._is_lesson_accessible(user_id, 3)
    check.is_false(accessible)


def test_mid_lessons_blocked_before_home_row(logged_in_client):
    user_id = app_module.User.query.first().id
    for lesson_id in (4, 5, 6, 7):
        accessible, _ = app_module._is_lesson_accessible(user_id, lesson_id)
        check.is_false(accessible, msg=f'Урок {lesson_id} должен быть заблокирован')


def test_exercise_passed_at_threshold(logged_in_client):
    response = _pass_exercise(logged_in_client, accuracy=90)
    data = response.get_json()
    check.is_true(data['exercise_passed'])
    check.equal(data['pass_threshold'], 90)

    user_id = app_module.User.query.first().id
    progress = app_module._get_progress(user_id, 1)
    check.equal(progress.completed_exercises, 1)


def test_exercise_not_passed_below_threshold(logged_in_client):
    response = _pass_exercise(logged_in_client, accuracy=85)
    data = response.get_json()
    check.is_false(data['exercise_passed'])

    user_id = app_module.User.query.first().id
    progress = app_module._get_progress(user_id, 1)
    check.equal(progress.completed_exercises, 0)


def test_completing_lesson_unlocks_next(logged_in_client):
    _complete_lesson(logged_in_client, accuracy=95)

    user_id = app_module.User.query.first().id
    progress = app_module._get_progress(user_id, 1)
    check.is_true(progress.is_completed)

    accessible, _ = app_module._is_lesson_accessible(user_id, 2)
    check.is_true(accessible)


def test_best_accuracy_tracked(logged_in_client):
    _pass_exercise(logged_in_client, accuracy=85)                                     
    _pass_exercise(logged_in_client, accuracy=95)
    _pass_exercise(logged_in_client, accuracy=80)                             

    user_id = app_module.User.query.first().id
    progress = app_module._get_progress(user_id, 1)
    check.equal(progress.best_accuracy, 95)


def test_free_practice_blocked_for_new_user(logged_in_client):
    user_id = app_module.User.query.first().id
    accessible, reason = app_module._is_lesson_accessible(
        user_id, app_module.FREE_LESSON_ID
    )
    check.is_false(accessible)
    check.is_in('1', reason)                       


def test_free_practice_requires_good_avg_accuracy(logged_in_client):
    user_id = app_module.User.query.first().id

                                                                   
    for _ in range(3):
        _complete_lesson(logged_in_client, accuracy=90)
                                  
    for _ in range(3):
        _complete_lesson(logged_in_client, accuracy=90)


    accessible, reason = app_module._is_lesson_accessible(
        user_id, app_module.FREE_LESSON_ID
    )
    check.is_true(accessible, msg=f'Ожидался доступ к свободе, причина: {reason}')


def test_free_practice_blocked_by_poor_recent_accuracy(logged_in_client):
    user_id = app_module.User.query.first().id

                                                          
    for _ in range(3):
        _complete_lesson(logged_in_client, accuracy=95)
                                 
    for _ in range(3):
        _complete_lesson(logged_in_client, accuracy=95)

                        
    accessible, _ = app_module._is_lesson_accessible(
        user_id, app_module.FREE_LESSON_ID
    )
    check.is_true(accessible)


    for _ in range(5):
        logged_in_client.post('/save_stats', json={'wpm': 50, 'accuracy': 50})

    accessible, reason = app_module._is_lesson_accessible(
        user_id, app_module.FREE_LESSON_ID
    )
    check.is_false(accessible, msg='Низкая средняя точность должна блокировать свободу')
    check.is_in('точность', reason.lower())


def test_lesson_page_shows_locked_reasons(logged_in_client):
    response = logged_in_client.get('/lessons')
    body = response.get_data(as_text=True)
    check.is_in('Сначала пройдите урок 1', body)


def test_start_lesson_redirects_blocked(logged_in_client):
    response = logged_in_client.get('/lesson/8', follow_redirects=False)
    check.equal(response.status_code, 302)
    check.is_in('/lessons', response.location)


def test_drill_uses_new_chars_not_accumulated(client):
    import lessons

    lesson5 = lessons.get_lesson(5)
    ex = lessons.generate_exercises(lesson5)
    drill = ex[0]
                                                
    check.is_in('нгшщ', drill, msg=f'Урок 5 drill должен содержать новые буквы нгшщ, получили: {drill}')
    check.is_not_in('фыва', drill, msg=f'Урок 5 drill НЕ должен содержать фыва, получили: {drill}')


def test_drill_falls_back_to_chars_when_new_chars_empty(client):
    import lessons

    lesson1 = lessons.get_lesson(1)
    check.equal(lesson1.new_chars, '', msg='Урок 1 не должен иметь new_chars (используется chars)')

    ex = lessons.generate_exercises(lesson1)
    check.is_in('фыва', ex[0], msg=f'Урок 1 drill должен содержать фыва: {ex[0]}')


def test_all_lessons_have_reasonable_drill(client):
    import lessons

    for lesson in lessons.LESSONS:
        if lesson.is_free_practice:
            continue
        ex = lessons.generate_exercises(lesson)
        drill = ex[0]
        check.is_true(len(drill) > 0, msg=f'Урок {lesson.id}: drill пустой')
        expected = lesson.new_chars or lesson.chars
                                                                           
        expected_letters = {c for c in expected if c != ' '}
        drill_letters = {c for c in drill if c != ' '}
        overlap = expected_letters & drill_letters
        check.is_true(
            len(overlap) > 0,
            msg=f'Урок {lesson.id}: drill {drill!r} не содержит ни одной буквы из {expected!r}'
        )


def test_save_stats_in_free_practice_does_not_return_pass_threshold(logged_in_client):
    user_id = app_module.User.query.first().id


    mandatory_count = len(app_module.LESSONS) - 1
    for _ in range(mandatory_count):
        _complete_lesson(logged_in_client, accuracy=95)

                                                          
    current = app_module._current_lesson_id(user_id)
    check.equal(current, app_module.FREE_LESSON_ID,
                msg=f'Ожидался урок 8 (свобода), получили {current}')

                                                
    response = logged_in_client.post('/save_stats', json={'wpm': 300, 'accuracy': 100})
    data = response.get_json()

    check.is_true(data['success'])
                                                            
    check.is_not_in('pass_threshold', data,
                    msg='pass_threshold не должен возвращаться в свободной практике')
                                                        
    check.is_false(data['exercise_passed'])
    check.is_false(data['lesson_completed'])


def test_save_stats_in_regular_lesson_returns_pass_threshold(logged_in_client):
    response = logged_in_client.post('/save_stats', json={'wpm': 100, 'accuracy': 85})
    data = response.get_json()
    check.is_in('pass_threshold', data,
                msg='pass_threshold должен возвращаться для обычных уроков')
    check.equal(data['pass_threshold'], app_module.EXERCISE_PASS_ACCURACY)
