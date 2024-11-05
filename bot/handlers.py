import json
import os
import tempfile
import google.generativeai as genai

import requests
import stripe
from aiogram import Bot, Router
from aiogram.filters import Command, CommandStart
from aiogram.types import (
    FSInputFile,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
    PreCheckoutQuery,
)

from bot.constants import (
    AUDIO_QUESTIONS,
    BASIC_QUESTIONS,
    BASIC_QUESTIONS_CHOICES,
    BASIC_QUESTIONS_CHOICES_ANSWERS,
    ESSAY_QUESTIONS,
    get_report_text,
)

# Create PDF for mini report
from bot.pdf_generator import generate_pdf_content
from bot.question_utils import (
    get_audio_question_number,
    get_essay_question_number,
    is_audio_question,
    is_essay_question,
)
from bot.validators import (
    validate_age,
    validate_email,
    validate_essay_length,
    validate_name,
    validate_text_message,
    validate_voice_message,
)
from config.logger_config import logger
from test_data import agent_data

# Configure structured logging
logger = logger.getChild("handlers")


async def handle_voice_message(message: Message, tg_bot_token):
    out = await message.bot.get_file(message.voice.file_id)
    return f"https://api.telegram.org/file/bot{tg_bot_token}/{out.file_path}"


async def create_payment_button(username: str, bot_username: str):
    """Create Stripe payment session and return payment button markup."""
    # Create Stripe payment session
    session = stripe.checkout.Session.create(
        payment_method_types=["card"],
        line_items=[
            {
                "price_data": {
                    "currency": "usd",
                    "product_data": {
                        "name": "Full English Assessment Report",
                        "description": "Comprehensive English language assessment report with personalized study plan",
                    },
                    "unit_amount": 1999,  # $19.99 in cents
                },
                "quantity": 1,
            }
        ],
        mode="payment",
        success_url=f"https://t.me/{bot_username}?start=payment_success_{username}",
        cancel_url=f"https://t.me/{bot_username}?start=payment_cancel_{username}",
        client_reference_id=username,
    )

    # Create payment button with direct Stripe URL
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Получить полный отчет за $19.99", url=session.url
                )
            ]
        ]
    )


async def mini_report_handler(db_manager, general_agent, username, bot_username):
    logger.info(f"Generating mini report for user {username}")
    # Get raw responses
    raw_responses = db_manager.get_all_user_responses(username)
    logger.debug(f"Raw responses: {raw_responses}")

    # Format responses as question-answer pairs
    formatted_responses = {}
    for i, response in enumerate(raw_responses[: len(ESSAY_QUESTIONS)]):
        formatted_responses[ESSAY_QUESTIONS[i]] = response
    logger.debug(f"Formatted responses: {formatted_responses}")
    # Get analysis from general agent
    general_response = general_agent.handle_message(str(formatted_responses))
    logger.debug(f"General agent response: {general_response}")
    general_analysis = json.loads(
        general_response.split("<evaluation>")[1].split("</evaluation>")[0]
    )
    logger.debug(f"General agent analysis: {general_analysis}")

    english_level = general_analysis["english_level"]
    mistake_count = general_analysis["mistakes_count"]
    problem_areas = general_analysis["weakest_areas"]
    months_to_fix = general_analysis["months_to_improve"]

    payment_button = await create_payment_button(username, bot_username)

    return (
        get_report_text(english_level, mistake_count, problem_areas, months_to_fix),
        payment_button,
    )


def process_assistant_response(response):
    logger.debug(f"Processing assistant response: {response}")
    eval_start = response.find("<evaluation>") + len("<evaluation>")
    eval_end = response.find("</evaluation>")
    feedback_start = response.find("<feedback>") + len("<feedback>")
    feedback_end = response.find("</feedback>")

    evaluation = json.loads(response[eval_start:eval_end])
    feedback = json.loads(response[feedback_start:feedback_end])
    return evaluation, feedback


async def get_analysis_data(
    db_manager,
    username,
    vocabulary_assistant_manager,
    tense_assistant_manager,
    style_assistant_manager,
    grammar_assistant_manager,
    audio_model_genai,
    study_plan_assistant_manager,
):
    logger.info(f"Getting analysis data for user {username}")
    REMOVE_LATER = 1
    user_info = db_manager.get_user_info(username, len(BASIC_QUESTIONS) + REMOVE_LATER)
    logger.debug(f"User info: {user_info}")

    name = user_info[0]
    age = user_info[1]
    email = user_info[2]

    # Extract user responses into a dictionary
    responses_list = db_manager.get_all_user_responses(username)
    logger.debug(f"Responses list: {responses_list}")
    # Get analysis from each AI agent
    logger.debug(f"Starting AI analysis for user {username}")
    # Get all responses except the last one (audio response) for text analysis

    filtered_responses = responses_list[: len(ESSAY_QUESTIONS)]
    # Create paired question-response format
    question_response_pairs = [
        f"{ESSAY_QUESTIONS[i]}:{response}"
        for i, response in enumerate(filtered_responses)
    ]
    formatted_responses = str(question_response_pairs)

    logger.debug(f"Formatted responses: {formatted_responses}")

    # Process all analyses
    vocabulary_evaluation, vocabulary_feedback = process_assistant_response(
        vocabulary_assistant_manager.handle_message(formatted_responses)
    )
    logger.debug(f"Vocab evaluation: {vocabulary_evaluation}")
    logger.debug(f"Vocab feedback: {vocabulary_feedback}")
    tense_evaluation, tense_feedback = process_assistant_response(
        tense_assistant_manager.handle_message(formatted_responses)
    )
    logger.debug(f"Tense evaluation: {tense_evaluation}")
    logger.debug(f"Tense feedback: {tense_feedback}")
    style_evaluation, style_feedback = process_assistant_response(
        style_assistant_manager.handle_message(formatted_responses)
    )
    logger.debug(f"Style evaluation: {style_evaluation}")
    logger.debug(f"Style feedback: {style_feedback}")
    grammar_evaluation, grammar_feedback = process_assistant_response(
        grammar_assistant_manager.handle_message(formatted_responses)
    )
    logger.debug(f"Grammar evaluation: {grammar_evaluation}")
    logger.debug(f"Grammar feedback: {grammar_feedback}")

    # Get all audio responses
    audio_files = responses_list[-len(AUDIO_QUESTIONS) :]
    logger.debug(f"Audio files: {audio_files}")
    prompts = []

    for i, url in enumerate(audio_files):
        response = requests.get(url)
        if response.status_code == 200:
            # Create a temporary file
            with tempfile.NamedTemporaryFile(delete=False, suffix=".ogg") as temp_file:
                temp_file.write(response.content)
                temp_file_path = temp_file.name
            logger.debug(f"Temporary file path: {temp_file_path}")

            try:
                # Upload the temporary file
                audio_file = genai.upload_file(temp_file_path)
                logger.debug(f"Uploaded audio file: {audio_file}")
                prompts.append(f"{AUDIO_QUESTIONS[i]}: {audio_file}")
                logger.debug(f"{AUDIO_QUESTIONS[i]}: {audio_file}")
            finally:
                # Clean up the temporary file
                os.unlink(temp_file_path)

    logger.debug(f"Prompts: {prompts}")

    audio_response = audio_model_genai.generate_content(prompts).text
    audio_evaluation, audio_feedback = process_assistant_response(audio_response)
    logger.debug(f"Audio evaluation: {audio_evaluation}")
    logger.debug(f"Audio feedback: {audio_feedback}")

    # """MOCK DATA"""
    # vocabulary_evaluation = agent_data.vocabulary_evaluation
    # vocabulary_feedback = agent_data.vocabulary_feedback
    # grammar_evaluation = agent_data.grammar_evaluation
    # grammar_feedback = agent_data.grammar_feedback
    # tense_evaluation = agent_data.tense_evaluation
    # tense_feedback = agent_data.tense_feedback
    # style_evaluation = agent_data.style_evaluation
    # style_feedback = agent_data.style_feedback
    # study_plan = agent_data.study_plan
    # audio_evaluation = agent_data.audio_evaluation
    # audio_feedback = agent_data.audio_feedback
    # """MOCK DATA"""

    study_plan_response = {
        "vocabulary": {
            "evaluation": vocabulary_evaluation,
            "feedback": vocabulary_feedback,
        },
        "tenses": {"evaluation": tense_evaluation, "feedback": tense_feedback},
        "style": {"evaluation": style_evaluation, "feedback": style_feedback},
        "grammar": {"evaluation": grammar_evaluation, "feedback": grammar_feedback},
        "pronunciation": {
            "evaluation": audio_evaluation,
            "feedback": audio_feedback,
        },
    }

    study_plan = study_plan_assistant_manager.handle_message(
        json.dumps(study_plan_response)
    )
    logger.debug(f"Study plan before JSON: {study_plan}")
    eval_start = study_plan.find("<output>") + len("<output>")
    eval_end = study_plan.find("</output>")
    study_plan = json.loads(study_plan[eval_start:eval_end])

    logger.debug(f"Study plan after JSON: {study_plan}")

    logger.debug("Completed AI analysis for user {username}")

    return {
        "user_info": {"name": name, "age": age, "email": email, "username": username},
        "vocabulary": {
            "evaluation": vocabulary_evaluation,
            "feedback": vocabulary_feedback,
        },
        "grammar": {"evaluation": grammar_evaluation, "feedback": grammar_feedback},
        "audio": {"evaluation": audio_evaluation, "feedback": audio_feedback},
        "tense": {"evaluation": tense_evaluation, "feedback": tense_feedback},
        "style": {"evaluation": style_evaluation, "feedback": style_feedback},
        "study_plan": study_plan,
    }


async def full_report_handler(
    db_manager,
    username,
    vocabulary_assistant_manager,
    tense_assistant_manager,
    style_assistant_manager,
    grammar_assistant_manager,
    audio_model_genai,
    study_plan_assistant_manager,
):
    # Get analysis data
    analysis_data = await get_analysis_data(
        db_manager,
        username,
        vocabulary_assistant_manager,
        tense_assistant_manager,
        style_assistant_manager,
        grammar_assistant_manager,
        audio_model_genai,
        study_plan_assistant_manager,
    )

    # Generate PDF content
    pdf_path = generate_pdf_content(analysis_data)
    return pdf_path


async def generate_full_report(
    message: Message, username: str, db_manager, **assistants
):
    """Generate and send full report to user after successful payment."""
    try:
        await message.answer(
            "Генерация полного отчета... Это может занять около минуты."
        )
        pdf_path = await full_report_handler(
            db_manager,
            username,
            assistants["vocabulary_assistant_manager"],
            assistants["tense_assistant_manager"],
            assistants["style_assistant_manager"],
            assistants["grammar_assistant_manager"],
            assistants["audio_model_genai"],
            assistants["study_plan_assistant_manager"],
        )

        # Send the PDF report
        await message.answer_document(
            FSInputFile(pdf_path),
            caption="Ваш полный отчет готов! Спасибо за использование English Buddy AI.",
        )

        # Mark report as sent
        db_manager.mark_report_sent(username)

        # Clean up the file
        os.remove(pdf_path)
        return True

    except Exception as e:
        logger.error(f"Error generating full report: {str(e)}")
        await message.answer(
            "Произошла ошибка при генерации отчета. Пожалуйста, напишите в поддержку."
        )
        return False


def setup_router(
    vocabulary_assistant_manager,
    tense_assistant_manager,
    style_assistant_manager,
    grammar_assistant_manager,
    audio_model_genai,
    mini_report_assistant_manager,
    study_plan_assistant_manager,
    db_manager,
    tg_bot_token,
    bot_username,
    stripe_secret_key,
):
    router = Router()
    logger.info("Initializing router and handlers")

    # Set Stripe API key
    stripe.api_key = stripe_secret_key

    @router.message(
        lambda message: message.text and message.text.startswith("/start payment_")
    )
    async def handle_payment_status(message: Message):
        username = message.from_user.username
        status = message.text.split("_")[1]  # success or cancel

        if status == "success":
            logger.info(f"Payment successful for user {username}")
            db_manager.update_payment_status(username, True)

            await message.answer("Спасибо за оплату! Генерирую ваш полный отчет...")

            await generate_full_report(
                message,
                username,
                db_manager,
                vocabulary_assistant_manager=vocabulary_assistant_manager,
                tense_assistant_manager=tense_assistant_manager,
                style_assistant_manager=style_assistant_manager,
                grammar_assistant_manager=grammar_assistant_manager,
                audio_model_genai=audio_model_genai,
                study_plan_assistant_manager=study_plan_assistant_manager,
            )

        elif status == "cancel":
            logger.info(f"Payment cancelled for user {username}")
            await message.answer("Оплата была отменена. Вы можете попробовать снова")

    @router.message(CommandStart())
    async def send_welcome(message: Message):
        username = message.from_user.username
        logger.info(f"User {username} started the bot")
        await message.answer(
            "Привет! Я бот English Buddy AI. Давайте оценим ваши навыки английского языка и создадим персонализированный план обучения."
        )
        await message.answer(BASIC_QUESTIONS[0])
        db_manager.update_current_question(username, 1)
        logger.debug(f"Initial question sent to user {username}")

    async def mini_report(message: Message):
        username = message.from_user.username
        logger.info(f"Mini report started for user {username}")

        # Generate new report if none exists
        await message.answer("Генерация краткого отчета... Пожалуйста, подождите.")
        report_text, payment_button = await mini_report_handler(
            db_manager,
            mini_report_assistant_manager,
            message.from_user.username,
            bot_username,
        )

        await message.answer(report_text, reply_markup=payment_button)

    @router.message()
    async def handle_user_interaction(message: Message):
        username = message.from_user.username
        logger.info(
            f"Received {'voice' if message.voice else 'text'} message from user {username}"
        )

        try:
            await process_user_message(message, username)
        except Exception as e:
            logger.error(
                f"Error processing message from user {username}: {str(e)}",
                exc_info=True,
            )
            await message.answer(
                "Извините, что-то пошло не так. Пожалуйста, попробуйте еще раз."
            )

    async def process_user_message(message: Message, username: str):
        current_question = db_manager.get_current_question(username)

        if current_question == 0:
            logger.debug(f"User {username} hasn't started questionnaire")
            await message.reply(
                "Пожалуйста, используйте команду /start, чтобы начать опрос."
            )
            return

        handlers = {
            lambda q: q <= len(BASIC_QUESTIONS): handle_basic_questions,
            lambda q: is_essay_question(
                q,
                len(BASIC_QUESTIONS),
                len(BASIC_QUESTIONS_CHOICES),
                len(ESSAY_QUESTIONS),
            ): handle_essay_questions,
            lambda q: is_audio_question(
                q,
                len(BASIC_QUESTIONS),
                len(BASIC_QUESTIONS_CHOICES),
                len(ESSAY_QUESTIONS),
                len(AUDIO_QUESTIONS),
            ): handle_audio_questions,
            lambda q: True: handle_completed_questionnaire,
        }

        for condition, handler in handlers.items():
            if condition(current_question):
                await handler(message, username, current_question)
                return

    async def handle_basic_questions(
        message: Message, username: str, current_question: int
    ):
        if not validate_text_message(message):
            await message.reply("Пожалуйста, предоставьте текстовый ответ.")
            return

        validators = {1: validate_name, 2: validate_age, 3: validate_email}
        error_messages = {
            1: "Пожалуйста, введите имя и фамилию, используя только буквы и пробелы.",
            2: "Пожалуйста, введите корректный возраст от 10 до 100 лет.",
            3: "Пожалуйста, введите действительный email адрес.",
        }

        if current_question in validators:
            if not validators[current_question](message.text):
                await message.reply(error_messages[current_question])
                return

        db_manager.save_user_info(username, current_question, message.text)

        if current_question == len(BASIC_QUESTIONS):
            keyboard = InlineKeyboardMarkup(
                inline_keyboard=[
                    [InlineKeyboardButton(text=answer, callback_data=answer)]
                    for answer in BASIC_QUESTIONS_CHOICES_ANSWERS[0]
                ]
            )
            await message.answer(BASIC_QUESTIONS_CHOICES[0], reply_markup=keyboard)
        else:
            await message.answer(BASIC_QUESTIONS[current_question])

        db_manager.update_current_question(username, current_question + 1)

    async def handle_essay_questions(
        message: Message, username: str, current_question: int
    ):
        if not validate_text_message(message):
            await message.reply("Пожалуйста, предоставьте текстовый ответ.")
            return

        is_valid, error_message = validate_essay_length(message.text)
        if not is_valid:
            await message.reply(error_message)
            return

        essay_q_num = get_essay_question_number(
            current_question, len(BASIC_QUESTIONS), len(BASIC_QUESTIONS_CHOICES)
        )
        db_manager.save_user_response(username, essay_q_num, message.text)

        if essay_q_num == len(ESSAY_QUESTIONS) - 1:
            await message.answer(
                "Пожалуйста, запишите аудио ответ на следующий вопрос:\n\n"
                + AUDIO_QUESTIONS[0]
            )
        else:
            await message.answer(
                "Пожалуйста, ответьте на английском.\n"
                + ESSAY_QUESTIONS[essay_q_num + 1]
            )

        db_manager.update_current_question(username, current_question + 1)

    async def handle_audio_questions(
        message: Message, username: str, current_question: int
    ):
        is_valid, error_message = validate_voice_message(message)
        if not is_valid:
            await message.reply(error_message)
            return

        audio_q_num = get_audio_question_number(
            current_question,
            len(BASIC_QUESTIONS),
            len(BASIC_QUESTIONS_CHOICES),
            len(ESSAY_QUESTIONS),
        )

        # Save the file URL to database
        file_url = await handle_voice_message(message, tg_bot_token)
        db_manager.save_user_response(
            username, audio_q_num + len(ESSAY_QUESTIONS), file_url
        )

        db_manager.update_current_question(username, current_question + 1)

        if audio_q_num == len(AUDIO_QUESTIONS) - 1:
            await message.answer("Спасибо за заполнение анкеты!\n\n")
            await mini_report(message)
        else:
            await message.answer(
                "Пожалуйста, запишите аудио ответ на следующий вопрос:\n\n"
                + AUDIO_QUESTIONS[audio_q_num + 1]
            )

    async def handle_completed_questionnaire(
        message: Message, username: str, current_question: int
    ):
        if not message.text or not message.text.startswith("/"):
            # Check if user has already paid
            has_paid = db_manager.get_payment_status(username)
            if has_paid:
                await message.answer(
                    "Вы уже приобрели полный отчет. Если вам нужна помощь, напишите в поддержку @akhatsuleimenov."
                )
            else:
                payment_button = await create_payment_button(username, bot_username)
                await message.answer(
                    "Вы уже заполнили опросник!\n\n"
                    "Чтобы получить полный отчет, нажмите кнопку ниже:",
                    reply_markup=payment_button,
                )

    @router.callback_query()
    async def handle_callback(callback_query):
        username = callback_query.from_user.username
        logger.info(f"Received callback from user {username}: {callback_query.data}")

        try:
            current_question = db_manager.get_current_question(username)
            choice_q_num = current_question - len(BASIC_QUESTIONS) - 1

            # Determine if this is one of the last two questions
            is_multi_select = choice_q_num >= len(BASIC_QUESTIONS_CHOICES) - 2

            if callback_query.data == "SUBMIT_CHOICES" and is_multi_select:
                await process_choices_submission(callback_query, username)
            else:
                await process_choice_selection(
                    callback_query, username, is_multi_select
                )
        except Exception as e:
            logger.error(
                f"Error processing callback from user {username}: {str(e)}",
                exc_info=True,
            )
            await callback_query.answer(
                "Произошла ошибка. Пожалуйста, попробуйте еще раз.", show_alert=True
            )

    async def process_choice_selection(
        callback_query, username: str, is_multi_select: bool
    ):
        current_question = db_manager.get_current_question(username)
        choice_q_num = current_question - len(BASIC_QUESTIONS) - 1

        if not (choice_q_num >= 0 and choice_q_num < len(BASIC_QUESTIONS_CHOICES)):
            return

        # Extract the actual answer from the callback data
        if callback_query.data.startswith("choice_"):
            index = int(callback_query.data.split("_")[1])
            actual_answer = BASIC_QUESTIONS_CHOICES_ANSWERS[choice_q_num][index]
        else:
            actual_answer = callback_query.data

        if is_multi_select:
            # Multi-select logic
            current_markup = callback_query.message.reply_markup
            new_keyboard = []

            for row in current_markup.inline_keyboard:
                if row[0].callback_data == "SUBMIT_CHOICES":
                    continue

                if row[0].callback_data == callback_query.data:
                    # Toggle selection
                    text = row[0].text
                    new_text = (
                        f"{text} ✓" if "✓" not in text else text.replace(" ✓", "")
                    )
                    new_keyboard.append(
                        [
                            InlineKeyboardButton(
                                text=new_text, callback_data=row[0].callback_data
                            )
                        ]
                    )
                else:
                    new_keyboard.append(row)

            # Add submit button
            new_keyboard.append(
                [
                    InlineKeyboardButton(
                        text="Подтвердить выбор", callback_data="SUBMIT_CHOICES"
                    )
                ]
            )

            try:
                await callback_query.message.edit_reply_markup(
                    reply_markup=InlineKeyboardMarkup(inline_keyboard=new_keyboard)
                )
                await callback_query.answer()
            except Exception as e:
                logger.error(f"Error updating keyboard: {str(e)}")
                await callback_query.answer(
                    "Произошла ошибка. Пожалуйста, попробуйте еще раз.", show_alert=True
                )

        else:
            # Single-select logic - immediately process and move to next question
            try:
                # Prepare keyboard for next question before updating DB
                next_is_multi = choice_q_num + 1 >= len(BASIC_QUESTIONS_CHOICES) - 2
                keyboard = InlineKeyboardMarkup(
                    inline_keyboard=[
                        [InlineKeyboardButton(text=answer, callback_data=f"choice_{i}")]
                        for i, answer in enumerate(
                            BASIC_QUESTIONS_CHOICES_ANSWERS[choice_q_num + 1]
                        )
                    ]
                    + (
                        [
                            [
                                InlineKeyboardButton(
                                    text="Подтвердить выбор",
                                    callback_data="SUBMIT_CHOICES",
                                )
                            ]
                        ]
                        if next_is_multi
                        else []
                    )
                )
                if choice_q_num == len(BASIC_QUESTIONS_CHOICES) - 1:
                    await callback_query.message.answer(
                        "Пожалуйста, ответьте на английском.\n" + ESSAY_QUESTIONS[0]
                    )
                else:
                    try:
                        await callback_query.message.edit_text(
                            BASIC_QUESTIONS_CHOICES[choice_q_num + 1],
                            reply_markup=keyboard,
                        )
                    except Exception:
                        await callback_query.message.answer(
                            BASIC_QUESTIONS_CHOICES[choice_q_num + 1],
                            reply_markup=keyboard,
                        )
                # Only update DB if message edit/send was successful
                db_manager.save_user_info(username, current_question, actual_answer)
                db_manager.update_current_question(username, current_question + 1)
                await callback_query.answer()

            except Exception as e:
                logger.error(f"Error processing single selection: {str(e)}")
                await callback_query.answer(
                    "Произошла ошибка. Пожалуйста, попробуйте еще раз.", show_alert=True
                )

    async def process_choices_submission(callback_query, username: str):
        current_question = db_manager.get_current_question(username)
        choice_q_num = current_question - len(BASIC_QUESTIONS) - 1

        # Collect all selected options
        selected_options = []
        for row in callback_query.message.reply_markup.inline_keyboard:
            if row[0].callback_data != "SUBMIT_CHOICES" and "✓" in row[0].text:
                selected_options.append(row[0].text.replace(" ✓", ""))

        if not selected_options:
            await callback_query.answer(
                "Пожалуйста, выберите хотя бы один вариант", show_alert=True
            )
            return

        try:
            # Prepare next keyboard before updating DB
            next_keyboard = None
            if choice_q_num != len(BASIC_QUESTIONS_CHOICES) - 1:
                next_is_multi = choice_q_num + 1 >= len(BASIC_QUESTIONS_CHOICES) - 2
                next_keyboard = InlineKeyboardMarkup(
                    inline_keyboard=[
                        [InlineKeyboardButton(text=answer, callback_data=f"choice_{i}")]
                        for i, answer in enumerate(
                            BASIC_QUESTIONS_CHOICES_ANSWERS[choice_q_num + 1]
                        )
                    ]
                    + (
                        [
                            [
                                InlineKeyboardButton(
                                    text="Подтвердить выбор",
                                    callback_data="SUBMIT_CHOICES",
                                )
                            ]
                        ]
                        if next_is_multi
                        else []
                    )
                )

            if choice_q_num == len(BASIC_QUESTIONS_CHOICES) - 1:
                await callback_query.message.answer(
                    "Пожалуйста, ответьте на английском.\n" + ESSAY_QUESTIONS[0]
                )
            else:
                try:
                    await callback_query.message.edit_text(
                        BASIC_QUESTIONS_CHOICES[choice_q_num + 1],
                        reply_markup=next_keyboard,
                    )
                except Exception:
                    await callback_query.message.answer(
                        BASIC_QUESTIONS_CHOICES[choice_q_num + 1],
                        reply_markup=next_keyboard,
                    )

            # Only update DB if message edit/send was successful
            db_manager.save_user_info(
                username, current_question, ", ".join(selected_options)
            )
            db_manager.update_current_question(username, current_question + 1)
            await callback_query.answer()

        except Exception as e:
            logger.error(f"Error processing choices submission: {str(e)}")
            await callback_query.answer(
                "Произошла ошибка. Пожалуйста, попробуйте еще раз.", show_alert=True
            )

    logger.info("Router setup completed successfully")
    return router
