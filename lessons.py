import random
from dataclasses import dataclass, field


@dataclass
class Lesson:
    id: int
    title: str
    description: str
    chars: str
    is_free_practice: bool = False
    words: list[str] = field(default_factory=list)
    new_chars: str = ''


LESSONS: list[Lesson] = [
    Lesson(
        id=1,
        title='Урок 1. Левая рука, домашний ряд',
        description='Фыва — основа основ. Осваиваем позицию левой руки.',
        chars='фыва',
        words=['вы', 'фа', 'вал', 'ваза', 'фыва'],
    ),
    Lesson(
        id=2,
        title='Урок 2. Правая рука, домашний ряд',
        description='Олдж — зеркало для правой руки.',
        chars='олдж',
        words=['до', 'од', 'ол', 'жало', 'долж'],
    ),
    Lesson(
        id=3,
        title='Урок 3. Обе руки, домашний ряд',
        description='Соединяем руки: фыва + олдж.',
        chars='фыва олдж',
        new_chars='фыва олдж',
        words=['вода', 'дело', 'жало', 'овал', 'овод', 'давал', 'живой'],
    ),
    Lesson(
        id=4,
        title='Урок 4. Верхний ряд, левая',
        description='Тянемся мизинцем-безымянным-средним-указательным наверх.',
        chars='фыва олдж йцуке',
        new_chars='йцуке',
        words=['дом', 'вид', 'код', 'клад', 'доклад', 'лекало', 'увижу'],
    ),
    Lesson(
        id=5,
        title='Урок 5. Верхний ряд, правая',
        description='Теперь правая рука тянется наверх: нгшщ.',
        chars='фыва олдж йцукенгшщ',
        new_chars='нгшщ',
        words=['книга', 'школа', 'ношу', 'гений', 'нужно', 'щенок', 'лежу'],
    ),
    Lesson(
        id=6,
        title='Урок 6. Нижний ряд',
        description='Опускаемся к нижнему ряду: ячсмит, ьбю.',
        chars='фыва олдж йцукенгшщ ячсмитьбю',
        new_chars='ячсмитьбю',
        words=['мысль', 'быть', 'любой', 'чистый', 'жить', 'часто', 'итого'],
    ),
    Lesson(
        id=7,
        title='Урок 7. Цифры и пунктуация',
        description='Финальная раскладка: числа, запятые, точки.',
        chars='фыва олдж йцукенгшщ ячсмитьбю 1234567890.,',
        new_chars='1234567890.,',
        words=['дом 12', 'код 404', 'ночь, сон', 'жить, любить', '2024 год'],
    ),
    Lesson(
        id=8,
        title='Свободная практика',
        description='Настоящие тексты. Работай над скоростью и слабыми клавишами.',
        chars='',
        is_free_practice=True,
    ),
]


def get_lesson(lesson_id: int) -> Lesson | None:
    for lesson in LESSONS:
        if lesson.id == lesson_id:
            return lesson
    return None


EXERCISES_PER_LESSON = 4


def _clean_chars(chars: str) -> list[str]:
    return [c for c in chars if c != ' ']


def _repeat_drill(chunk_chars: str, length: int = 40) -> str:
    clean = _clean_chars(chunk_chars)
    if not clean:
        return ''
    chunk = ''.join(clean[:4])
    parts = []
    while len(' '.join(parts)) < length:
        parts.append(chunk)
    return ' '.join(parts)[:length].strip()


def _pseudo_words(chars: str, length: int = 45) -> str:
    pool = _clean_chars(chars)
    if not pool:
        return ''
    words = []
    total = 0
    while total < length:
        word_len = random.randint(2, 4)
        word = ''.join(random.choice(pool) for _ in range(word_len))
        words.append(word)
        total += len(word) + 1
    return ' '.join(words)[:length].strip()


def _real_words(words: list[str], length: int = 50) -> str:
    if not words:
        return ''
    chosen = []
    total = 0
    while total < length:
        word = random.choice(words)
        chosen.append(word)
        total += len(word) + 1
    return ' '.join(chosen)[:length].strip()


def generate_exercises(lesson: Lesson) -> list[str]:
    if lesson.is_free_practice:
        return []

    drill_chars = lesson.new_chars or lesson.chars

    exercises = [
        _repeat_drill(drill_chars),
        _pseudo_words(lesson.chars),
    ]
    if lesson.words:
        exercises.append(_real_words(lesson.words))
        exercises.append(_real_words(lesson.words))
    else:
        exercises.append(_pseudo_words(lesson.chars))
        exercises.append(_pseudo_words(lesson.chars))

    return exercises[:EXERCISES_PER_LESSON]
