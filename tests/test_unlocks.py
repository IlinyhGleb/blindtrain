import pytest_check as check

import app as app_module


def _set_level(user, level):
    user.level = level
    app_module.db.session.commit()


def _alice():
    return app_module.User.query.filter_by(username='alice').first()


def test_level_1_user_has_only_base_options(logged_in_client):
    user = _alice()
    _set_level(user, 1)

    check.is_true(app_module._is_option_unlocked(user, 'theme', 'light'))
    check.is_false(app_module._is_option_unlocked(user, 'theme', 'dark'))

    check.is_true(app_module._is_option_unlocked(user, 'typingFg', 'default'))
    check.is_false(app_module._is_option_unlocked(user, 'typingFg', 'blue'))

    check.is_true(app_module._is_option_unlocked(user, 'highlight', 'flash'))
    check.is_true(app_module._is_option_unlocked(user, 'highlight', 'fade'))
    check.is_false(app_module._is_option_unlocked(user, 'highlight', 'solid'))

    check.is_true(app_module._is_option_unlocked(user, 'title', ''))
    check.is_true(app_module._is_option_unlocked(user, 'title', 'novice'))
    check.is_false(app_module._is_option_unlocked(user, 'title', 'master'))


def test_level_7_user_unlocks_dark_theme(logged_in_client):
    user = _alice()
    _set_level(user, 7)
    check.is_true(app_module._is_option_unlocked(user, 'theme', 'dark'))


def test_level_20_user_has_everything(logged_in_client):
    user = _alice()
    _set_level(user, 20)
    for category, options in app_module.UNLOCKS.items():
        for code in options:
            check.is_true(
                app_module._is_option_unlocked(user, category, code),
                msg=f'Уровень 20 должен иметь доступ к {category}/{code}'
            )


def test_unknown_category_is_locked(logged_in_client):
    user = _alice()
    _set_level(user, 99)                 
    check.is_false(app_module._is_option_unlocked(user, 'cursors', 'fancy'))
    check.is_false(app_module._is_option_unlocked(user, 'theme', 'unknown_theme'))


def test_unlocks_for_client_has_correct_flags(logged_in_client):
    user = _alice()
    _set_level(user, 5)
    snapshot = app_module._unlocks_for_client(user)

                                                       
    check.is_true(snapshot['typingBg']['warm']['unlocked'])
                                             
    check.is_false(snapshot['typingBg']['cool']['unlocked'])


def test_unlocks_for_client_preserves_required_level(logged_in_client):
    user = _alice()
    _set_level(user, 1)
    snapshot = app_module._unlocks_for_client(user)

    check.equal(snapshot['theme']['dark']['required_level'], 7)
    check.equal(snapshot['typingBg']['paper']['required_level'], 20)


def test_api_user_settings_rejects_locked_title(logged_in_client):
    user = _alice()
    _set_level(user, 1)

                                        
    response = logged_in_client.post('/api/user_settings',
                                     json={'selected_title': 'grandmaster'})
    check.equal(response.status_code, 200)
    data = response.get_json()
    check.is_true(data['success'])
                                                                      
    check.not_equal(data['selected_title'], 'grandmaster')

    user = _alice()                
    check.not_equal(user.selected_title, 'grandmaster')


def test_api_user_settings_accepts_unlocked_title(logged_in_client):
    user = _alice()
    _set_level(user, 5)

    response = logged_in_client.post('/api/user_settings',
                                     json={'selected_title': 'student'})
    data = response.get_json()
    check.equal(data['selected_title'], 'student')

    user = _alice()
    check.equal(user.selected_title, 'student')


def test_api_user_settings_accepts_empty_title(logged_in_client):
    user = _alice()
    _set_level(user, 5)
    user.selected_title = 'student'
    app_module.db.session.commit()

    response = logged_in_client.post('/api/user_settings',
                                     json={'selected_title': ''})
    data = response.get_json()
    check.equal(data['selected_title'], '')


def test_title_label_known_code(logged_in_client):
    check.equal(app_module._title_label('master'), 'Мастер')


def test_title_label_empty_code(logged_in_client):
    check.equal(app_module._title_label(''), '')


def test_title_label_unknown_code(logged_in_client):
    check.equal(app_module._title_label('nonexistent'), '')


def test_leaderboard_shows_titles(logged_in_client):
    user = _alice()
    _set_level(user, 15)
    user.selected_title = 'master'
    app_module.db.session.commit()

    response = logged_in_client.get('/leaderboard?tab=level')
    body = response.get_data(as_text=True)
    check.is_in('Мастер', body)


def test_leaderboard_hides_title_of_hidden_user(logged_in_client):
                                                               
    bob = app_module.User(username='bob', level=15,
                          selected_title='master',
                          hidden_in_leaderboard=True)
    bob.set_password('x')
    app_module.db.session.add(bob)
    app_module.db.session.commit()

                           
    response = logged_in_client.get('/leaderboard?tab=level')
    body = response.get_data(as_text=True)
    check.is_in('Аноним', body)
    check.is_not_in('bob', body)
                                                      
                                                                         
    check.is_not_in('Мастер', body)


def test_index_passes_unlocks_to_template(logged_in_client):
    response = logged_in_client.get('/')
    body = response.get_data(as_text=True)
                                            
    check.is_in('const UNLOCKS =', body)
                              
    check.is_in('"dark"', body)
    check.is_in('"grandmaster"', body)


def test_typing_font_category_exists():
    check.is_in('typingFont', app_module.UNLOCKS)
    fonts = app_module.UNLOCKS['typingFont']
    for code in ['default', 'jetbrains', 'roboto_mono', 'source_code_pro', 'pt_mono']:
        check.is_in(code, fonts, msg=f'Отсутствует шрифт: {code}')


def test_typing_font_entries_have_css_family():
    for code, meta in app_module.UNLOCKS['typingFont'].items():
        check.is_in('css_family', meta, msg=f'У {code} нет css_family')
        check.is_in('monospace', meta['css_family'],
                    msg=f'css_family для {code} не содержит fallback monospace')


def test_typing_font_levels_monotonic():
    order = ['default', 'jetbrains', 'roboto_mono', 'source_code_pro', 'pt_mono']
    levels = [app_module.UNLOCKS['typingFont'][c]['required_level'] for c in order]
    check.equal(levels, sorted(levels),
                msg=f'Уровни шрифтов не монотонны: {dict(zip(order, levels))}')


def test_typing_font_default_available_at_level_1(logged_in_client):
    user = _alice()
    _set_level(user, 1)
    check.is_true(app_module._is_option_unlocked(user, 'typingFont', 'default'))


def test_typing_font_pt_mono_locked_at_level_1(logged_in_client):
    user = _alice()
    _set_level(user, 1)
    check.is_false(app_module._is_option_unlocked(user, 'typingFont', 'pt_mono'))


def test_typing_font_pt_mono_unlocked_at_level_15(logged_in_client):
    user = _alice()
    _set_level(user, 15)
    check.is_true(app_module._is_option_unlocked(user, 'typingFont', 'pt_mono'))


def test_index_renders_font_group_in_modal(logged_in_client):
    response = logged_in_client.get('/')
    body = response.get_data(as_text=True)
                     
    check.is_in('id="settingsTypingFont"', body)
    check.is_in('Шрифт для набора', body)
                              
    check.is_in("containerId:'settingsTypingFont'", body)
    check.is_in("bindOptionGroup('settingsTypingFont'", body)
