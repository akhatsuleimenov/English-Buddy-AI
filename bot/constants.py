from datetime import datetime, timedelta

BASIC_QUESTIONS = [
    "Как вас зовут?",
    "Сколько вам лет?",
    "Какой у вас email?",
]

BASIC_QUESTIONS_CHOICES = [
    "Для чего вам необходимо овладеть английским?",
    "Каков ваш текущий уровень владения английским?",
    "Когда вам нужно овладеть английским?",
    "Какие проблемы мешают вам овладеть английским?",
    "Как вы оцениваете свою дисциплинированность в изучении английского?",
    "Какой формат обучения вам нравится?",
    "Выберите свои интересы (можно выбрать несколько)",
    "Какие экзамены вам необходимо сдать? (можно выбрать несколько)",
]

BASIC_QUESTIONS_CHOICES_ANSWERS = [
    ["Оценки в учебных заведениях", "Путешествий", "Для себя", "Работы", "Другое"],
    [
        "Начинающий",
        "Ниже среднего",
        "Средний",
        "Выше среднего",
        "Уровень носителя",
        "Продвинутый",
    ],
    ["1-3 месяца", "3-6 месяцев", "6-12 месяцев", "1-2 года", "Нет сроков"],
    [
        "Нехватка практики",
        "Не могу найти подходящего преподавателя",
        "Проблемы с грамматикой",
        "Ограниченный словарный запас",
        "Не понимаю речь носителей или англоязычный контент",
        "Не могу найти время на английский",
    ],
    [
        "Постоянно начинаю и забрасываю",
        "Дисциплина есть, но её хватает ненадолго",
        "Я гуру дисциплины, всегда довожу до конца",
    ],
    [
        "Групповые занятия",
        "Индивидуальные занятия",
        "Онлайн",
        "Офлайн",
    ],
    [
        "Аниме",
        "Дорамы",
        "Американские сериалы",
        "Худ. литература",
        "Научная литература",
        "Бизнес-литература",
        "Манга/Комиксы",
        "Фитнес",
        "Футбол",
        "Баскетбол",
        "Теннис",
        "Шахматы",
        "Киберспорт",
        "Йога и медитация",
        "Рукоделие",
    ],
    [
        "IELTS",
        "TOEFL",
        "SAT",
        "GMAT",
        "Duolingo",
        "NUFIP",
    ],
]

ESSAY_QUESTIONS = [
    "Где вы родились и когда, где живете сейчас и чем занимаетесь.",
    "Чем вы больше всего любите заниматься? Какие у вас хобби?",
    "Почему вы хотите изучать английский язык?",
]

AUDIO_QUESTIONS = [
    "Можете ли вы описать свой распорядок дня и как выглядит ваш типичный день?",
    "Расскажите о запоминающейся поездке или опыте, который у ас был в прошлом.",
    "Каковы ваши планы или цели на будущее? Как вы думаете, как вы их достигнете?",
]


def get_report_text(english_level, mistake_count, problem_areas, months_to_fix):
    # Get current time and add 15 minutes
    current_time = datetime.now()
    expiry_time = current_time + timedelta(minutes=15)
    formatted_time = expiry_time.strftime("%H:%M")
    return (
        "Ваш отчет готов! 🎉\n\n"
        f"📚 Уровень Языка: {english_level}\n"
        f"❌ Найдено ошибок: {mistake_count}\n"
        f"❗️ Главная трудность: {' / '.join(problem_areas)}\n"
        f"⭐️ Возможность исправить всё за: {months_to_fix} месяцев\n"
        "--------------------------------------------------------------------------------\n\n"
        "🎁 Вам доступна скидка!\n\n"
        "В течение ближайших 15 минут вы можете получить полный отчет от нашего авторского искусственного интеллекта (ИИ) со скидкой $130! 📉\n\n"
        "Полный отчет включает:\n\n"
        "🎯 Точная оценка вашего уровня языка\n"
        "     💰 обычная цена 10$\n\n"
        "🗣 Анализ акцента с персональными упражнениями\n"
        "     💰 обычная цена 20$\n\n"
        "⏰ Полный анализ понимания времен\n"
        "     💰 обычная цена 15$\n\n"
        "🎓 Оценка произношения по методике Кембриджа\n"
        "     💰 обычная цена 30$\n\n"
        "📋 Индивидуальный план обучения (1-3-12 месяцев)\n"
        "     💰 обычная цена 40$\n\n"
        "📚 Подборка книг, фильмов и сериалов\n"
        "     💰 обычная цена 10$\n\n"
        "📝 Доступ к 5 гайдам по изучению английского\n"
        "     💰 обычная цена 25$\n\n"
        "--------------------------------------------------------------------------------\n\n"
        f"🔥 Эксклюзивная Цена Только До {formatted_time}:\n\n"
        "$̶1̶5̶0̶ ➔ $19.99 (10.000 тенге)"
    )
