import random
from datetime import datetime
from flask import Flask, render_template, redirect, url_for, request, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.config.update(
    SECRET_KEY='dev-secret-key',
    SQLALCHEMY_DATABASE_URI='sqlite:///typist.db',
    SQLALCHEMY_TRACK_MODIFICATIONS=False
)

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(120), nullable=False)
    xp = db.Column(db.Integer, default=0)
    level = db.Column(db.Integer, default=1)
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
    date = db.Column(db.DateTime, default=datetime.utcnow)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

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

@app.route('/')
@login_required
def index():
    return render_template('index.html', text=random.choice(TEXTS), user=current_user)

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
    return render_template('stats.html', stats=user_stats)

@app.route('/save_stats', methods=['POST'])
@login_required
def save_stats():
    data = request.get_json()
    wpm = data.get('wpm', 0)
    accuracy = data.get('accuracy', 0)

    db.session.add(Stat(user_id=current_user.id, wpm=wpm, accuracy=accuracy))

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

    db.session.commit()

    return jsonify({
        'success': True,
        'gained_xp': gained_xp,
        'new_level': current_user.level,
        'leveled_up': leveled_up
    })

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True, port=5000)