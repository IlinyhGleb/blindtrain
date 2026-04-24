import io
import os
import pytest_check as check
from PIL import Image

import app as app_module


def _make_png_bytes(size=(10, 10), color=(255, 0, 0)) -> bytes:
    img = Image.new('RGB', size, color)
    buf = io.BytesIO()
    img.save(buf, format='PNG')
    return buf.getvalue()


def _make_jpg_bytes(size=(10, 10), color=(0, 255, 0)) -> bytes:
    img = Image.new('RGB', size, color)
    buf = io.BytesIO()
    img.save(buf, format='JPEG')
    return buf.getvalue()


def _alice():
    return app_module.User.query.filter_by(username='alice').first()


def _set_level(user, level):
    user.level = level
    app_module.db.session.commit()


def test_validate_accepts_valid_png():
    data = _make_png_bytes()
    ext = app_module._validate_image(data)
    check.equal(ext, 'png')


def test_validate_accepts_valid_jpg():
    data = _make_jpg_bytes()
    ext = app_module._validate_image(data)
    check.equal(ext, 'jpg')


def test_validate_rejects_too_small():
    with check.raises(ValueError):
        app_module._validate_image(b'hi')


def test_validate_rejects_too_big():
    huge = b'\xff\xd8\xff' + b'x' * (app_module.MAX_BACKGROUND_SIZE + 100)
    with check.raises(ValueError):
        app_module._validate_image(huge)


def test_validate_rejects_text_file():
    with check.raises(ValueError):
        app_module._validate_image(b'Hello world, this is not an image file at all')


def test_validate_rejects_fake_jpg_signature():
                                                                              
    fake = b'\xff\xd8\xff' + b'\x00' * 1000
    with check.raises(ValueError):
        app_module._validate_image(fake)


def test_validate_rejects_gif():
                      
    gif_data = b'GIF89a' + b'\x00' * 100
    with check.raises(ValueError):
        app_module._validate_image(gif_data)


def test_detect_format_png():
    check.equal(app_module._detect_image_format(_make_png_bytes()), 'png')


def test_detect_format_jpg():
    check.equal(app_module._detect_image_format(_make_jpg_bytes()), 'jpg')


def test_detect_format_unknown():
    check.is_none(app_module._detect_image_format(b'not an image'))


def test_custom_bg_locked_at_level_1(logged_in_client):
    user = _alice()
    _set_level(user, 1)
    check.is_false(app_module._is_option_unlocked(user, 'customBg', 'enabled'))


def test_custom_bg_unlocked_at_level_12(logged_in_client):
    user = _alice()
    _set_level(user, 12)
    check.is_true(app_module._is_option_unlocked(user, 'customBg', 'enabled'))


def test_upload_rejected_for_low_level(logged_in_client):
    user = _alice()
    _set_level(user, 1)
    data = _make_png_bytes()
    response = logged_in_client.post(
        '/api/background/upload',
        data={'file': (io.BytesIO(data), 'bg.png')},
        content_type='multipart/form-data',
    )
    check.equal(response.status_code, 403)


def test_upload_accepts_valid_image_at_level_12(logged_in_client):
    user = _alice()
    _set_level(user, 12)
    data = _make_png_bytes()
    response = logged_in_client.post(
        '/api/background/upload',
        data={'file': (io.BytesIO(data), 'bg.png')},
        content_type='multipart/form-data',
    )
    body = response.get_json()
    check.equal(response.status_code, 200)
    check.is_true(body['success'])
    check.is_in('url', body)
    check.is_in('/static/uploads/backgrounds/', body['url'])

                             
    alice = _alice()
    check.is_not_none(alice.custom_background_path)

                                       
    full_path = os.path.join(
        app_module.BACKGROUND_UPLOAD_DIR, alice.custom_background_path
    )
    check.is_true(os.path.isfile(full_path),
                  msg=f'Файл не создан: {full_path}')

                        
    app_module._delete_user_background_file(alice.custom_background_path)
    alice.custom_background_path = None
    app_module.db.session.commit()


def test_upload_rejects_text_file(logged_in_client):
    user = _alice()
    _set_level(user, 12)
    response = logged_in_client.post(
        '/api/background/upload',
        data={'file': (io.BytesIO(b'not really an image'), 'fake.png')},
        content_type='multipart/form-data',
    )
    check.equal(response.status_code, 400)
    check.is_false(response.get_json()['success'])


def test_upload_replaces_previous_file(logged_in_client):
    user = _alice()
    _set_level(user, 12)

                     
    logged_in_client.post(
        '/api/background/upload',
        data={'file': (io.BytesIO(_make_png_bytes()), 'a.png')},
        content_type='multipart/form-data',
    )
    alice = _alice()
    first_filename = alice.custom_background_path
    first_path = os.path.join(app_module.BACKGROUND_UPLOAD_DIR, first_filename)
    check.is_true(os.path.isfile(first_path))

                                                      
    logged_in_client.post(
        '/api/background/upload',
        data={'file': (io.BytesIO(_make_jpg_bytes()), 'b.jpg')},
        content_type='multipart/form-data',
    )
    alice = _alice()
    second_filename = alice.custom_background_path
    check.not_equal(first_filename, second_filename)
    check.is_false(os.path.isfile(first_path),
                   msg='Старый файл не был удалён при загрузке нового')

            
    app_module._delete_user_background_file(alice.custom_background_path)
    alice.custom_background_path = None
    app_module.db.session.commit()


def test_delete_removes_file_and_clears_path(logged_in_client):
    user = _alice()
    _set_level(user, 12)
                       
    logged_in_client.post(
        '/api/background/upload',
        data={'file': (io.BytesIO(_make_png_bytes()), 'x.png')},
        content_type='multipart/form-data',
    )
    alice = _alice()
    filename = alice.custom_background_path
    full_path = os.path.join(app_module.BACKGROUND_UPLOAD_DIR, filename)
    check.is_true(os.path.isfile(full_path))

                    
    response = logged_in_client.post('/api/background/delete')
    check.equal(response.status_code, 200)
    check.is_true(response.get_json()['success'])

    alice = _alice()
    check.is_none(alice.custom_background_path)
    check.is_false(os.path.isfile(full_path))


def test_mode_accepts_page(logged_in_client):
    response = logged_in_client.post('/api/background/mode', json={'mode': 'page'})
    check.equal(response.status_code, 200)
    check.equal(response.get_json()['mode'], 'page')


def test_mode_accepts_field(logged_in_client):
    response = logged_in_client.post('/api/background/mode', json={'mode': 'field'})
    check.equal(response.status_code, 200)
    check.equal(response.get_json()['mode'], 'field')


def test_mode_rejects_junk(logged_in_client):
    response = logged_in_client.post('/api/background/mode', json={'mode': 'cucumber'})
    check.equal(response.status_code, 400)


def test_delete_helper_safe_against_traversal():
                                                                         
                                             
    outside_path = os.path.join(os.path.dirname(app_module.BACKGROUND_UPLOAD_DIR), 'marker.txt')
    os.makedirs(os.path.dirname(outside_path), exist_ok=True)
    with open(outside_path, 'w') as f:
        f.write('do not delete me')

    try:
        app_module._delete_user_background_file('../../marker.txt')
        check.is_true(os.path.isfile(outside_path),
                      msg='Файл вне папки был удалён — path traversal не защищён!')
    finally:
        if os.path.isfile(outside_path):
            os.remove(outside_path)


def test_delete_helper_handles_none():
                                                         
    app_module._delete_user_background_file(None)
    app_module._delete_user_background_file('')
    check.is_true(True)                             
