def is_essay_question(
    current_question: int,
    basic_questions_len: int,
    basic_choices_len: int,
    essay_questions_len: int,
) -> bool:
    """Check if current question is an essay question"""
    essay_q_num = current_question - basic_questions_len - basic_choices_len - 1
    return essay_q_num < essay_questions_len


def is_audio_question(
    current_question: int,
    basic_questions_len: int,
    basic_choices_len: int,
    essay_questions_len: int,
    audio_questions_len: int,
) -> bool:
    """Check if current question is an audio question"""
    audio_q_num = (
        current_question
        - basic_questions_len
        - basic_choices_len
        - essay_questions_len
        - 1
    )
    return audio_q_num < audio_questions_len


def get_essay_question_number(
    current_question: int, basic_questions_len: int, basic_choices_len: int
) -> int:
    """Get the essay question number based on current question"""
    return current_question - basic_questions_len - basic_choices_len - 1


def get_audio_question_number(
    current_question: int,
    basic_questions_len: int,
    basic_choices_len: int,
    essay_questions_len: int,
) -> int:
    """Get the audio question number based on current question"""
    return (
        current_question
        - basic_questions_len
        - basic_choices_len
        - essay_questions_len
        - 1
    )
