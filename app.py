import os
import io
import random
import secrets
from datetime import datetime, date, timedelta, timezone
from flask import Flask, render_template, redirect, url_for, request, flash, jsonify, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from PIL import Image

from lessons import LESSONS, get_lesson, generate_exercises, EXERCISES_PER_LESSON

app = Flask(__name__)
app.config.update(
    SECRET_KEY=os.environ.get('SECRET_KEY', 'dev-secret-key'),
    SQLALCHEMY_DATABASE_URI=os.environ.get('DATABASE_URL', 'sqlite:///typist.db'),
    SQLALCHEMY_TRACK_MODIFICATIONS=False
)

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

ALLOWED_BACKGROUND_MODES = ('none', 'page', 'field', 'both')


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(120), nullable=False)
    xp = db.Column(db.Integer, default=0)
    level = db.Column(db.Integer, default=1)

    current_streak = db.Column(db.Integer, default=0, nullable=False)
    longest_streak = db.Column(db.Integer, default=0, nullable=False)
    last_active_date = db.Column(db.Date, nullable=True)

    hidden_in_leaderboard = db.Column(db.Boolean, default=False, nullable=False)

    selected_title = db.Column(db.String(40), default='', nullable=False)

    custom_background_path = db.Column(db.String(255), nullable=True)

    custom_background_mode = db.Column(db.String(20), default='page', nullable=False)

    stats = db.relationship('Stat', backref='user', lazy=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class Stat(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    wpm = db.Column(db.Integer, nullable=False)
    accuracy = db.Column(db.Integer, nullable=False)
    date = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))


class KeyError_(db.Model):
    __tablename__ = 'key_error'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    char = db.Column(db.String(4), nullable=False)
    count = db.Column(db.Integer, default=0, nullable=False)
    __table_args__ = (db.UniqueConstraint('user_id', 'char', name='uix_user_char'),)


class LessonProgress(db.Model):
    __tablename__ = 'lesson_progress'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    lesson_id = db.Column(db.Integer, nullable=False)
    completed_exercises = db.Column(db.Integer, default=0, nullable=False)
    is_completed = db.Column(db.Boolean, default=False, nullable=False)
    best_accuracy = db.Column(db.Integer, default=0, nullable=False)
    __table_args__ = (db.UniqueConstraint('user_id', 'lesson_id', name='uix_user_lesson'),)


class Achievement(db.Model):
    __tablename__ = 'achievement'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    code = db.Column(db.String(40), nullable=False)
    earned_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    __table_args__ = (db.UniqueConstraint('user_id', 'code', name='uix_user_achievement'),)


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))


TEXTS = [
    "Печать вслепую - это навык, который позволяет набирать текст, не глядя на клавиатуру.",
    "Программирование на Python требует не только знаний алгоритмов, но и быстрой работы с кодом.",
    "Каждый день мы создаем мегабайты текста, общаясь в мессенджерах и работая за компьютером.",
    "Искусственный интеллект (ИИ) - это направление информатики, связанное с разработкой систем, способных выполнять интеллектуальные задачи, ранее доступные только человеку: распознавание образов, понимание естественного языка, обучение, принятие решений и прогнозирование.",
    "(A+B)*C = D - это простая формула.",
    "Держите осанку: сидите прямо, локти согнуты под углом 90 градусов.",
    "Расслабь мышцы плеч, рук и кистей. Кисти могут немного касаться стола в нижней части клавиатуры, но не переноси вес тела на руки, чтобы не перенапрягать кисти.",
    "Смотрите на экран, а не на клавиши - это базовое правило для развития мышечной памяти.",
    "Возвращайте пальцы в домик - после каждого нажатия пальцы должны возвращаться в исходную позицию (ФЫВА - ОЛДЖ)",
    "Тренируйтесь понемногу, но часто - лучше заниматься 15-20 минут каждый день, чем 2 часа раз в неделю.",
    "Не делайте длинных пауз - перерыв в несколько дней может заметно снизить прогресс в мышечной памяти.",
    "Правило 20-20-20: каждые 20 минут смотри на 20 метров вдаль в течение 20 секунд.",
    "Потягушки: вытяни руки вверх, а ноги вперед, чтобы снять мышечное напряжение.",
    "Таймер - твой друг: работай блоками по 25-50 минут с обязательным перерывом.",
    "Минута в темноте: Плотно прикрой глаза ладонями на 60 секунд, чтобы исключить любой свет - это мгновенно перезагружает зрительный анализатор и снимает напряжение.",
    "Разбуди свое тело: Встань из-за стола, сделай глубокий вдох и хорошенько потянись всем корпусом, чтобы разогнать застоявшуюся лимфу и кровь.",
    "Смена фокуса: Если работаешь головой, отдохни руками: помой чашку, полей цветок или просто наведи порядок на столе - физическое действие переключает режим работы мозга и помогает отдохнуть.",
    "Сила микроперерывов: Исследования показывают, что короткие паузы по 40 секунд, во время которых вы просто смотрите на изображение природы или в окно на дерево, повышают концентрацию на 15%. Мозгу критически важно видеть естественные фракталы для отдыха от строгих линий интерфейса.",
    "Синдром компьютерного зрения: Когда мы смотрим в монитор, частота моргания падает с 15-20 до 5-7 раз в минуту. Это главная причина сухости и рези в глазах. Поставьте рядом кактус или яркий стикер - каждый раз, бросая на него взгляд, заставляйте себя моргнуть несколько раз подряд.",
    "Связь осанки и настроения: Сгорбленная поза за столом не только вредит спине, но и повышает уровень кортизола (гормона стресса). Если расправить плечи и выпрямиться на 2 минуты, уровень тестостерона растет, а кортизола падает, что возвращает чувство уверенности и контроля над делами."
]


EXERCISE_PASS_ACCURACY = 90
STRICT_LESSONS = {1, 2, 3}

FREE_PRACTICE_MIN_AVG_ACCURACY = 85
FREE_PRACTICE_WINDOW = 5

FREE_PRACTICE_MIN_MID_LESSONS = 3
MID_LESSONS = {4, 5, 6, 7}
FREE_LESSON_ID = 8


def _get_progress(user_id: int, lesson_id: int) -> 'LessonProgress':
    progress = LessonProgress.query.filter_by(user_id=user_id, lesson_id=lesson_id).first()
    if progress is None:
        progress = LessonProgress(user_id=user_id, lesson_id=lesson_id)
        db.session.add(progress)
        db.session.flush()
    return progress


def _recent_avg_accuracy(user_id: int) -> float | None:
    recent = (Stat.query
              .filter_by(user_id=user_id)
              .order_by(Stat.date.desc())
              .limit(FREE_PRACTICE_WINDOW)
              .all())
    if not recent:
        return None
    return sum(s.accuracy for s in recent) / len(recent)


def _is_lesson_accessible(user_id: int, lesson_id: int) -> tuple[bool, str]:
    if lesson_id in STRICT_LESSONS:
        for prev_id in range(1, lesson_id):
            prev = _get_progress(user_id, prev_id)
            if not prev.is_completed:
                return False, f'Сначала пройдите урок {prev_id}.'
        return True, ''

    if lesson_id in MID_LESSONS:
        for strict_id in STRICT_LESSONS:
            prev = _get_progress(user_id, strict_id)
            if not prev.is_completed:
                return False, 'Сначала пройдите уроки 1–3 (домашний ряд).'
        return True, ''

    if lesson_id == FREE_LESSON_ID:
        for strict_id in STRICT_LESSONS:
            if not _get_progress(user_id, strict_id).is_completed:
                return False, 'Сначала пройдите уроки 1–3.'
        completed_mid = sum(
            1 for mid_id in MID_LESSONS
            if _get_progress(user_id, mid_id).is_completed
        )
        if completed_mid < FREE_PRACTICE_MIN_MID_LESSONS:
            return False, (
                f'Пройдите минимум {FREE_PRACTICE_MIN_MID_LESSONS} из уроков 4–7 '
                f'(сейчас: {completed_mid}).'
            )
        avg = _recent_avg_accuracy(user_id)
        if avg is not None and avg < FREE_PRACTICE_MIN_AVG_ACCURACY:
            return False, (
                f'Средняя точность за последние {FREE_PRACTICE_WINDOW} сессий — '
                f'{avg:.0f}%. Нужно довести до {FREE_PRACTICE_MIN_AVG_ACCURACY}%, '
                f'чтобы разблокировать свободную практику.'
            )
        return True, ''

    return False, 'Неизвестный урок.'


def _current_lesson_id(user_id: int) -> int:
    for lesson in LESSONS:
        progress = _get_progress(user_id, lesson.id)
        if not progress.is_completed:
            return lesson.id
    return FREE_LESSON_ID


def _get_weak_chars(user_id: int, limit: int = 5, min_count: int = 2) -> list[str]:
    rows = (KeyError_.query
            .filter(KeyError_.user_id == user_id, KeyError_.count >= min_count)
            .order_by(KeyError_.count.desc())
            .limit(limit)
            .all())
    return [row.char for row in rows]


def _pick_text_for_user(user_id: int) -> str:
    weak = _get_weak_chars(user_id)
    if not weak or random.random() > 0.6:
        return random.choice(TEXTS)

    weak_set = set(weak)

    def weak_ratio(text: str) -> float:
        letters = [c for c in text.lower() if c.isalpha()]
        if not letters:
            return 0.0
        return sum(1 for c in letters if c in weak_set) / len(letters)

    ranked = sorted(TEXTS, key=weak_ratio, reverse=True)
    top = [t for t in ranked[:3] if weak_ratio(t) > 0]
    return random.choice(top) if top else random.choice(TEXTS)


def _today() -> date:
    return datetime.now(timezone.utc).date()


def _update_streak(user: 'User', today: date | None = None) -> str:
    if today is None:
        today = _today()

    last = user.last_active_date

    if last is None:
        user.current_streak = 1
        event = 'started'
    elif last == today:
        return 'same_day'
    elif last == today - timedelta(days=1):
        user.current_streak += 1
        event = 'continued'
    else:
        user.current_streak = 1
        event = 'started'

    user.last_active_date = today

    if user.current_streak > user.longest_streak:
        user.longest_streak = user.current_streak
        if event == 'continued':
            event = 'new_record'

    return event


def _count_completed_sessions(user_id: int) -> int:
    return Stat.query.filter_by(user_id=user_id).count()


def _count_recent_perfect(user_id: int, limit: int = 3) -> int:
    recent = (Stat.query
              .filter_by(user_id=user_id)
              .order_by(Stat.date.desc())
              .limit(limit)
              .all())
    if len(recent) < limit:
        return 0
    return sum(1 for s in recent if s.accuracy == 100)


def _count_completed_lessons(user_id: int) -> int:
    return LessonProgress.query.filter_by(user_id=user_id, is_completed=True).count()


ACHIEVEMENTS = {
    'first_lesson': {
        'title': 'Первый урок',
        'description': 'Закрыли первый урок',
        'icon': '🎓',
        'category': 'progress',
        'condition': lambda ctx: _count_completed_lessons(ctx['user'].id) >= 1,
    },
    'home_row_done': {
        'title': 'Домашний ряд',
        'description': 'Закрыли уроки 1–3 (фыва + олдж)',
        'icon': '🏠',
        'category': 'progress',
        'condition': lambda ctx: all(
            LessonProgress.query.filter_by(user_id=ctx['user'].id, lesson_id=i).first()
            and LessonProgress.query.filter_by(user_id=ctx['user'].id, lesson_id=i).first().is_completed
            for i in (1, 2, 3)
        ),
    },
    'all_rows_done': {
        'title': 'Вся клавиатура',
        'description': 'Закрыли уроки 1–7',
        'icon': '⌨️',
        'category': 'progress',
        'condition': lambda ctx: _count_completed_lessons(ctx['user'].id) >= 7,
    },
    'first_free_session': {
        'title': 'На свободе',
        'description': 'Завершили первый текст в свободной практике',
        'icon': '🕊',
        'category': 'progress',
        'condition': lambda ctx: (
            get_lesson(ctx.get('lesson_id')) is not None
            and get_lesson(ctx['lesson_id']).is_free_practice
        ),
    },

    'streak_3': {
        'title': 'Три дня подряд',
        'description': 'Занимались 3 дня подряд',
        'icon': '🔥',
        'category': 'streak',
        'condition': lambda ctx: ctx['user'].current_streak >= 3,
    },
    'streak_7': {
        'title': 'Неделя',
        'description': 'Занимались 7 дней подряд',
        'icon': '🔥',
        'category': 'streak',
        'condition': lambda ctx: ctx['user'].current_streak >= 7,
    },
    'streak_14': {
        'title': 'Две недели',
        'description': 'Занимались 14 дней подряд',
        'icon': '🔥',
        'category': 'streak',
        'condition': lambda ctx: ctx['user'].current_streak >= 14,
    },
    'streak_30': {
        'title': 'Месяц ежедневной практики',
        'description': 'Занимались 30 дней подряд',
        'icon': '👑',
        'category': 'streak',
        'condition': lambda ctx: ctx['user'].current_streak >= 30,
    },

    'speed_100': {
        'title': '100 зн/мин',
        'description': 'Скорость 100+ зн/мин при точности ≥90%',
        'icon': '🚶',
        'category': 'speed',
        'condition': lambda ctx: ctx['wpm'] >= 100 and ctx['accuracy'] >= 90,
    },
    'speed_150': {
        'title': '150 зн/мин',
        'description': 'Скорость 150+ зн/мин при точности ≥90%',
        'icon': '🏃',
        'category': 'speed',
        'condition': lambda ctx: ctx['wpm'] >= 150 and ctx['accuracy'] >= 90,
    },
    'speed_200': {
        'title': '200 зн/мин',
        'description': 'Скорость 200+ зн/мин при точности ≥90%',
        'icon': '🚴',
        'category': 'speed',
        'condition': lambda ctx: ctx['wpm'] >= 200 and ctx['accuracy'] >= 90,
    },
    'speed_300': {
        'title': '300 зн/мин',
        'description': 'Скорость 300+ зн/мин при точности ≥90%',
        'icon': '🚀',
        'category': 'speed',
        'condition': lambda ctx: ctx['wpm'] >= 300 and ctx['accuracy'] >= 90,
    },

    'perfect_session': {
        'title': 'Без единой ошибки',
        'description': '100% точность (от 50 символов)',
        'icon': '💎',
        'category': 'precision',
        'condition': lambda ctx: ctx['accuracy'] == 100 and ctx['text_length'] >= 50,
    },
    'zero_errors_long': {
        'title': 'Выдержка',
        'description': '100% точность на длинном тексте (от 150 символов)',
        'icon': '🎯',
        'category': 'precision',
        'condition': lambda ctx: ctx['accuracy'] == 100 and ctx['text_length'] >= 150,
    },
    'three_perfect': {
        'title': 'Три идеальных подряд',
        'description': 'Подряд три сессии со 100% точностью',
        'icon': '✨',
        'category': 'precision',
        'condition': lambda ctx: _count_recent_perfect(ctx['user'].id, 3) == 3,
    },
    'ten_sessions': {
        'title': 'Первая десятка',
        'description': 'Завершили 10 сессий',
        'icon': '🔟',
        'category': 'precision',
        'condition': lambda ctx: _count_completed_sessions(ctx['user'].id) >= 10,
    },
    'fifty_sessions': {
        'title': 'Полсотни',
        'description': 'Завершили 50 сессий',
        'icon': '📈',
        'category': 'precision',
        'condition': lambda ctx: _count_completed_sessions(ctx['user'].id) >= 50,
    },
    'hundred_sessions': {
        'title': 'Упорный',
        'description': 'Завершили 100 сессий',
        'icon': '💪',
        'category': 'precision',
        'condition': lambda ctx: _count_completed_sessions(ctx['user'].id) >= 100,
    },
}


UNLOCKS = {
    'theme': {
        'light': {'required_level': 1, 'label': 'Светлая'},
        'dark':  {'required_level': 7, 'label': 'Тёмная'},
    },
    'typingFg': {
        'default': {'required_level': 1,  'label': 'По умолчанию', 'swatch': '#222222'},
        'blue':    {'required_level': 3,  'label': 'Синий',        'swatch': '#1a4d8f'},
        'green':   {'required_level': 7,  'label': 'Зелёный',      'swatch': '#1e6e3c'},
        'purple':  {'required_level': 10, 'label': 'Фиолетовый',   'swatch': '#5a2a82'},
        'warm':    {'required_level': 15, 'label': 'Тёплый',       'swatch': '#8a4a1a'},
    },
    'typingBg': {
        'default': {'required_level': 1,  'label': 'По умолчанию', 'swatch': '#f8f9fa'},
        'warm':    {'required_level': 5,  'label': 'Тёплый',       'swatch': '#fff8e7'},
        'cool':    {'required_level': 10, 'label': 'Прохладный',   'swatch': '#eaf3f7'},
        'mint':    {'required_level': 15, 'label': 'Мятный',       'swatch': '#e9f5ec'},
        'paper':   {'required_level': 20, 'label': 'Бумага',       'swatch': '#f5ecd7'},
    },
    'typingFont': {
        'default': {
            'required_level': 1,
            'label': 'Системный',
            'css_family': 'Consolas, Monaco, "Courier New", monospace',
        },
        'jetbrains': {
            'required_level': 3,
            'label': 'JetBrains Mono',
            'css_family': '"JetBrains Mono", Consolas, monospace',
        },
        'roboto_mono': {
            'required_level': 7,
            'label': 'Roboto Mono',
            'css_family': '"Roboto Mono", Consolas, monospace',
        },
        'source_code_pro': {
            'required_level': 10,
            'label': 'Source Code Pro',
            'css_family': '"Source Code Pro", Consolas, monospace',
        },
        'pt_mono': {
            'required_level': 15,
            'label': 'PT Mono',
            'css_family': '"PT Mono", Consolas, monospace',
        },
    },
    'customBg': {
        'enabled': {'required_level': 12, 'label': 'Загрузка фона'},
    },
    'highlight': {
        'flash': {'required_level': 1,  'label': 'Вспышка'},
        'fade':  {'required_level': 1,  'label': 'Без подсветки'},
        'solid': {'required_level': 10, 'label': 'Стабильный зелёный'},
    },
    'title': {
        '':              {'required_level': 1,  'label': '— нет —'},
        'novice':        {'required_level': 1,  'label': 'Новичок'},
        'student':       {'required_level': 5,  'label': 'Ученик'},
        'persistent':    {'required_level': 10, 'label': 'Настойчивый'},
        'master':        {'required_level': 15, 'label': 'Мастер'},
        'grandmaster':   {'required_level': 20, 'label': 'Магистр'},
    },
}


def _is_option_unlocked(user, category: str, value: str) -> bool:
    cat = UNLOCKS.get(category)
    if cat is None:
        return False
    meta = cat.get(value)
    if meta is None:
        return False
    return user.level >= meta['required_level']


def _unlocks_for_client(user) -> dict:
    result = {}
    for category, options in UNLOCKS.items():
        result[category] = {}
        for code, meta in options.items():
            result[category][code] = {
                **meta,
                'unlocked': user.level >= meta['required_level'],
            }
    return result


def _title_label(title_code: str) -> str:
    meta = UNLOCKS['title'].get(title_code)
    return meta['label'] if meta and title_code else ''


BACKGROUND_UPLOAD_DIR = os.path.join(app.root_path, 'static', 'uploads', 'backgrounds')
MAX_BACKGROUND_SIZE = 3 * 1024 * 1024

_IMAGE_SIGNATURES = {
    b'\xff\xd8\xff': 'jpg',
    b'\x89PNG\r\n\x1a\n': 'png',
}


def _detect_image_format(data: bytes) -> str | None:
    for signature, ext in _IMAGE_SIGNATURES.items():
        if data.startswith(signature):
            return ext
    return None


def _validate_image(data: bytes) -> str:
    if len(data) > MAX_BACKGROUND_SIZE:
        raise ValueError(f'Файл слишком большой (максимум {MAX_BACKGROUND_SIZE // (1024*1024)} МБ)')
    if len(data) < 16:
        raise ValueError('Файл слишком маленький, чтобы быть картинкой')

    ext = _detect_image_format(data)
    if ext is None:
        raise ValueError('Формат не поддерживается. Разрешены JPG и PNG')

    try:
        img = Image.open(io.BytesIO(data))
        img.verify()
    except Exception:
        raise ValueError('Не удалось прочитать изображение — возможно, файл повреждён')

    img = Image.open(io.BytesIO(data))
    pil_format = (img.format or '').lower()
    if pil_format == 'jpeg':
        pil_format = 'jpg'
    if pil_format != ext:
        raise ValueError('Формат файла не соответствует содержимому')

    return ext


def _delete_user_background_file(filename: str | None) -> None:
    if not filename:
        return
    safe = secure_filename(filename)
    if not safe:
        return
    full = os.path.join(BACKGROUND_UPLOAD_DIR, safe)
    if not os.path.realpath(full).startswith(os.path.realpath(BACKGROUND_UPLOAD_DIR)):
        return
    try:
        if os.path.isfile(full):
            os.remove(full)
    except OSError:
        pass


def _custom_background_url(user) -> str | None:
    if not user.custom_background_path:
        return None
    return url_for('static', filename='uploads/backgrounds/' + user.custom_background_path)


def _check_achievements(user, context: dict) -> list[str]:
    already = {a.code for a in Achievement.query.filter_by(user_id=user.id).all()}

    newly_earned = []
    for code, meta in ACHIEVEMENTS.items():
        if code in already:
            continue
        try:
            if meta['condition'](context):
                db.session.add(Achievement(user_id=user.id, code=code))
                newly_earned.append(code)
        except Exception:
            continue

    return newly_earned


LEADERBOARD_SPEED_MIN_ACCURACY = 90
LEADERBOARD_TOP_N = 20


def _leaderboard_rows_by_level() -> list[dict]:
    users = (User.query
             .order_by(User.level.desc(), User.xp.desc(), User.id.asc())
             .all())
    return [
        {
            'user_id': u.id,
            'username': u.username,
            'hidden': u.hidden_in_leaderboard,
            'title_label': _title_label(u.selected_title),
            'metric_value': u.level * 10000 + u.xp,
            'metric_label': f'Уровень {u.level} · {u.xp} XP',
        }
        for u in users
    ]


def _leaderboard_rows_by_speed() -> list[dict]:
    from sqlalchemy import func
    best = (db.session.query(
                Stat.user_id.label('uid'),
                func.max(Stat.wpm).label('best_wpm'),
            )
            .filter(Stat.accuracy >= LEADERBOARD_SPEED_MIN_ACCURACY)
            .group_by(Stat.user_id)
            .subquery())

    rows = (db.session.query(User, best.c.best_wpm)
            .outerjoin(best, User.id == best.c.uid)
            .all())

    def sort_key(pair):
        u, best_wpm = pair
        return (best_wpm is None, -(best_wpm or 0), u.id)

    rows.sort(key=sort_key)

    return [
        {
            'user_id': u.id,
            'username': u.username,
            'hidden': u.hidden_in_leaderboard,
            'title_label': _title_label(u.selected_title),
            'metric_value': best_wpm or 0,
            'metric_label': f'{best_wpm} зн/мин' if best_wpm else '— нет записей',
        }
        for u, best_wpm in rows
    ]


def _paginate_leaderboard(all_rows: list[dict], current_user_id: int, top_n: int = LEADERBOARD_TOP_N) -> dict:
    top = all_rows[:top_n]
    top_ids = {row['user_id'] for row in top}

    my_position = None
    me = None
    if current_user_id not in top_ids:
        for idx, row in enumerate(all_rows):
            if row['user_id'] == current_user_id:
                my_position = idx + 1
                me = row
                break

    for idx, row in enumerate(top):
        row['position'] = idx + 1

    return {'top': top, 'me': me, 'my_position': my_position}


def _current_exercise_payload(user_id: int) -> dict:
    lesson_id = _current_lesson_id(user_id)
    lesson = get_lesson(lesson_id)
    progress = _get_progress(user_id, lesson_id)
    db.session.commit()

    if lesson.is_free_practice:
        text = _pick_text_for_user(user_id)
        return {
            'text': text,
            'lesson': {
                'id': lesson.id,
                'title': lesson.title,
                'description': lesson.description,
                'is_free_practice': True,
            },
            'exercise_num': None,
            'exercises_total': None,
        }

    exercises = generate_exercises(lesson)
    idx = min(progress.completed_exercises, len(exercises) - 1)
    text = exercises[idx]
    return {
        'text': text,
        'lesson': {
            'id': lesson.id,
            'title': lesson.title,
            'description': lesson.description,
            'is_free_practice': False,
        },
        'exercise_num': idx + 1,
        'exercises_total': len(exercises),
    }


@app.route('/')
@login_required
def index():
    payload = _current_exercise_payload(current_user.id)
    lesson = get_lesson(payload['lesson']['id'])
    return render_template(
        'index.html',
        text=payload['text'],
        user=current_user,
        lesson=lesson,
        exercise_num=payload['exercise_num'],
        exercises_total=payload['exercises_total'],
        unlocks=_unlocks_for_client(current_user),
        user_title_label=_title_label(current_user.selected_title),
        custom_background_url=_custom_background_url(current_user),
        custom_background_mode=current_user.custom_background_mode,
    )


@app.route('/api/next_exercise')
@login_required
def api_next_exercise():
    return jsonify({'success': True, **_current_exercise_payload(current_user.id)})


@app.route('/lessons')
@login_required
def lessons_list():
    items = []
    for lesson in LESSONS:
        progress = _get_progress(current_user.id, lesson.id)
        accessible, reason = _is_lesson_accessible(current_user.id, lesson.id)
        items.append({
            'lesson': lesson,
            'completed_exercises': progress.completed_exercises,
            'exercises_total': EXERCISES_PER_LESSON if not lesson.is_free_practice else None,
            'is_completed': progress.is_completed,
            'best_accuracy': progress.best_accuracy,
            'accessible': accessible,
            'lock_reason': reason,
        })
    db.session.commit()
    return render_template('lessons.html', items=items)


@app.route('/lesson/<int:lesson_id>')
@login_required
def start_lesson(lesson_id: int):
    lesson = get_lesson(lesson_id)
    if lesson is None:
        return redirect(url_for('lessons_list'))

    accessible, reason = _is_lesson_accessible(current_user.id, lesson_id)
    if not accessible:
        flash(reason or 'Этот урок пока недоступен.')
        return redirect(url_for('lessons_list'))

    return redirect(url_for('index'))


@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))

    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        if User.query.filter_by(username=username).first():
            flash('Пользователь с таким именем уже существует')
            return redirect(url_for('register'))

        new_user = User(username=username)
        new_user.set_password(password)
        db.session.add(new_user)
        db.session.commit()

        return redirect(url_for('login'))

    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))

    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()

        if user and user.check_password(password):
            login_user(user)
            return redirect(url_for('index'))

        flash('Неверные учетные данные')

    return render_template('login.html')


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))


@app.route('/stats')
@login_required
def stats():
    user_stats = Stat.query.filter_by(user_id=current_user.id).order_by(Stat.date.desc()).limit(20).all()
    return render_template('stats.html', stats=user_stats, user=current_user)


@app.route('/achievements')
@login_required
def achievements_page():
    earned = {a.code: a for a in Achievement.query.filter_by(user_id=current_user.id).all()}
    items = []
    for code, meta in ACHIEVEMENTS.items():
        items.append({
            'code': code,
            'title': meta['title'],
            'description': meta['description'],
            'icon': meta['icon'],
            'category': meta['category'],
            'earned': code in earned,
            'earned_at': earned[code].earned_at if code in earned else None,
        })
    items.sort(key=lambda it: (not it['earned'], list(ACHIEVEMENTS).index(it['code'])))
    earned_count = sum(1 for it in items if it['earned'])
    return render_template(
        'achievements.html',
        items=items,
        earned_count=earned_count,
        total=len(items),
        user=current_user,
    )


@app.route('/leaderboard')
@login_required
def leaderboard():
    tab = request.args.get('tab', 'level')
    if tab not in ('level', 'speed'):
        tab = 'level'

    if tab == 'level':
        rows = _leaderboard_rows_by_level()
        metric_title = 'По уровню'
    else:
        rows = _leaderboard_rows_by_speed()
        metric_title = 'По лучшей скорости'

    board = _paginate_leaderboard(rows, current_user.id)

    return render_template(
        'leaderboard.html',
        user=current_user,
        tab=tab,
        metric_title=metric_title,
        top=board['top'],
        me=board['me'],
        my_position=board['my_position'],
        total_users=len(rows),
    )


@app.route('/api/user_settings', methods=['POST'])
@login_required
def api_user_settings():
    data = request.get_json() or {}
    changed = False

    if 'hidden_in_leaderboard' in data:
        current_user.hidden_in_leaderboard = bool(data['hidden_in_leaderboard'])
        changed = True

    if 'selected_title' in data:
        new_title = data['selected_title'] or ''
        if _is_option_unlocked(current_user, 'title', new_title):
            current_user.selected_title = new_title
            changed = True

    if changed:
        db.session.commit()
    return jsonify({
        'success': True,
        'hidden_in_leaderboard': current_user.hidden_in_leaderboard,
        'selected_title': current_user.selected_title,
    })


@app.route('/api/background/upload', methods=['POST'])
@login_required
def api_background_upload():
    if not _is_option_unlocked(current_user, 'customBg', 'enabled'):
        return jsonify({
            'success': False,
            'error': 'Загрузка фона откроется на уровне 12',
        }), 403

    upload = request.files.get('file')
    if upload is None or upload.filename == '':
        return jsonify({'success': False, 'error': 'Файл не передан'}), 400

    data = upload.read()

    try:
        ext = _validate_image(data)
    except ValueError as e:
        return jsonify({'success': False, 'error': str(e)}), 400

    os.makedirs(BACKGROUND_UPLOAD_DIR, exist_ok=True)
    filename = f'{current_user.id}_{secrets.token_hex(8)}.{ext}'
    full_path = os.path.join(BACKGROUND_UPLOAD_DIR, filename)

    with open(full_path, 'wb') as f:
        f.write(data)

    _delete_user_background_file(current_user.custom_background_path)
    current_user.custom_background_path = filename
    db.session.commit()

    return jsonify({
        'success': True,
        'url': _custom_background_url(current_user),
        'mode': current_user.custom_background_mode,
    })


@app.route('/api/background/delete', methods=['POST'])
@login_required
def api_background_delete():
    _delete_user_background_file(current_user.custom_background_path)
    current_user.custom_background_path = None
    db.session.commit()
    return jsonify({'success': True})


@app.route('/api/background/mode', methods=['POST'])
@login_required
def api_background_mode():
    data = request.get_json() or {}
    mode = data.get('mode')
    if mode not in ALLOWED_BACKGROUND_MODES:
        return jsonify({'success': False, 'error': 'Недопустимый режим'}), 400
    current_user.custom_background_mode = mode
    db.session.commit()
    return jsonify({'success': True, 'mode': mode})


@app.route('/save_stats', methods=['POST'])
@login_required
def save_stats():
    data = request.get_json() or {}
    wpm = data.get('wpm', 0)
    accuracy = data.get('accuracy', 0)
    errors_by_char = data.get('errors_by_char') or {}
    text_length = int(data.get('text_length') or 0)

    db.session.add(Stat(user_id=current_user.id, wpm=wpm, accuracy=accuracy))

    for raw_char, count in errors_by_char.items():
        if not isinstance(raw_char, str) or len(raw_char) != 1:
            continue
        try:
            count = int(count)
        except (TypeError, ValueError):
            continue
        if count <= 0:
            continue
        char = raw_char.lower()

        existing = KeyError_.query.filter_by(user_id=current_user.id, char=char).first()
        if existing:
            existing.count += count
        else:
            db.session.add(KeyError_(user_id=current_user.id, char=char, count=count))

    gained_xp = int(wpm * (accuracy / 100.0))
    current_user.xp += gained_xp

    leveled_up = False
    while True:
        next_level_xp = current_user.level * 100
        if current_user.xp >= next_level_xp:
            current_user.xp -= next_level_xp
            current_user.level += 1
            leveled_up = True
        else:
            break

    lesson_id = _current_lesson_id(current_user.id)
    lesson = get_lesson(lesson_id)
    lesson_completed_now = False
    exercise_passed = False

    if lesson and not lesson.is_free_practice:
        progress = _get_progress(current_user.id, lesson_id)
        if accuracy > progress.best_accuracy:
            progress.best_accuracy = accuracy

        if accuracy >= EXERCISE_PASS_ACCURACY:
            exercise_passed = True
            progress.completed_exercises += 1
            if progress.completed_exercises >= EXERCISES_PER_LESSON:
                progress.is_completed = True
                lesson_completed_now = True

    streak_event = _update_streak(current_user)

    newly_earned_codes = _check_achievements(current_user, {
        'user': current_user,
        'wpm': wpm,
        'accuracy': accuracy,
        'text_length': text_length,
        'lesson_id': lesson_id,
    })
    newly_earned = [
        {
            'code': code,
            'title': ACHIEVEMENTS[code]['title'],
            'description': ACHIEVEMENTS[code]['description'],
            'icon': ACHIEVEMENTS[code]['icon'],
        }
        for code in newly_earned_codes
    ]

    db.session.commit()

    response = {
        'success': True,
        'gained_xp': gained_xp,
        'new_level': current_user.level,
        'new_xp': current_user.xp,
        'leveled_up': leveled_up,
        'lesson_id': lesson_id,
        'exercise_passed': exercise_passed,
        'lesson_completed': lesson_completed_now,
        'streak_current': current_user.current_streak,
        'streak_longest': current_user.longest_streak,
        'streak_event': streak_event,
        'new_achievements': newly_earned,
    }
    if lesson and not lesson.is_free_practice:
        response['pass_threshold'] = EXERCISE_PASS_ACCURACY

    return jsonify(response)


@app.route('/api/weak_keys')
@login_required
def api_weak_keys():
    rows = KeyError_.query.filter_by(user_id=current_user.id).all()
    errors = {row.char: row.count for row in rows}
    return jsonify({
        'errors': errors,
        'max': max(errors.values(), default=0),
    })


def main():
    with app.app_context():
        db.create_all()
    app.run(debug=True, port=5000)


if __name__ == '__main__':
    main()
