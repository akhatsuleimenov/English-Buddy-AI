def validate_name(name: str) -> bool:
    """Validate that name contains only letters and spaces and has at least two words."""
    name = name.strip()
    return all(x.isalpha() or x.isspace() for x in name) and len(name.split()) >= 2


def validate_age(age: str) -> bool:
    """Validate that age is a number between 10 and 100."""
    try:
        age_num = int(age)
        return 10 <= age_num <= 100
    except ValueError:
        return False


def validate_email(email: str) -> bool:
    """Validate basic email format."""
    email = email.strip()
    return "@" in email and "." in email and len(email.split("@")) == 2


def validate_text_message(message):
    """Validate that message contains text"""
    return bool(message.text)


def validate_voice_message(message):
    """Validate that message contains voice and meets duration requirements"""
    if not message.voice:
        return False, "Пожалуйста, отправьте голосовое сообщение."
    if message.voice.duration < 10:
        return (
            False,
            "Ваше голосовое сообщение должно быть не менее 10 секунд. Пожалуйста, попробуйте еще раз.",
        )
    return True, ""


def validate_essay_length(text):
    """Validate that essay meets minimum length requirement"""
    if len(text) < 400:
        return (
            False,
            "Ваш ответ должен содержать не менее 50 слов(400 символов). Пожалуйста, попробуйте еще раз.",
        )
    return True, ""
