import json
import os

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


async def handle_voice_message(message: Message, tg_bot_token, audio_assistant_manager):
    username = message.from_user.username
    logger.info(f"Processing voice message from user {username}")

    out = await message.bot.get_file(message.voice.file_id)
    file_url = f"https://api.telegram.org/file/bot{tg_bot_token}/{out.file_path}"

    response = requests.get(file_url)
    if response.status_code != 200:
        logger.error(
            f"Failed to download audio file for user {username}: Status code {response.status_code}"
        )
        raise Exception("Failed to download the audio file.")

    audio_file_path = f"{message.voice.file_unique_id}.ogg"
    with open(audio_file_path, "wb") as file:
        file.write(response.content)

    logger.debug(f"Transcribing audio for user {username}")
    transcribed_text = audio_assistant_manager.transcribe_audio(audio_file_path)
    os.remove(audio_file_path)
    logger.debug(f"Audio transcription completed for user {username}")
    logger.debug(f"Transcribed text: {transcribed_text}")
    return transcribed_text


async def mini_report_handler(db_manager, general_agent, username):
    logger.info(f"Generating mini report for user {username}")
    # Get raw responses
    raw_responses = db_manager.get_all_user_responses(username)
    logger.debug(f"Raw responses: {raw_responses}")

    # Format responses as question-answer pairs
    formatted_responses = {}
    for i, response in enumerate(raw_responses):
        formatted_responses[
            (
                ESSAY_QUESTIONS[i]
                if i < len(ESSAY_QUESTIONS)
                else AUDIO_QUESTIONS[i - len(ESSAY_QUESTIONS)]
            )
        ] = response

    logger.debug(f"Formatted responses: {str(formatted_responses)}")
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

    # Create payment button
    payment_button = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Получить полный отчет за $19.99",
                    callback_data="request_full_report",
                )
            ]
        ]
    )

    return (
        get_report_text(english_level, mistake_count, problem_areas, months_to_fix),
        payment_button,
    )


def process_assistant_response(response):
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
    audio_assistant_manager,
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

    # Join the pairs with clear separation
    formatted_responses = "\n---\n".join(question_response_pairs)

    logger.debug(f"Formatted responses: {formatted_responses}")

    # Get all audio responses
    audio_responses = responses_list[-len(AUDIO_QUESTIONS) :]

    # Create paired question-response format for audio responses
    audio_question_response_pairs = [
        f"{AUDIO_QUESTIONS[i]}:{response}" for i, response in enumerate(audio_responses)
    ]

    # Join the audio pairs with clear separation
    formatted_audio_responses = "\n---\n".join(audio_question_response_pairs)

    logger.debug(f"Formatted audio responses: {formatted_audio_responses}")

    # Process all analyses
    vocabulary_evaluation, vocabulary_feedback = process_assistant_response(
        vocabulary_assistant_manager.handle_message(formatted_responses)
    )
    tense_evaluation, tense_feedback = process_assistant_response(
        tense_assistant_manager.handle_message(formatted_responses)
    )
    style_evaluation, style_feedback = process_assistant_response(
        style_assistant_manager.handle_message(formatted_responses)
    )
    grammar_evaluation, grammar_feedback = process_assistant_response(
        grammar_assistant_manager.handle_message(formatted_responses)
    )
    audio_evaluation, audio_feedback = process_assistant_response(
        audio_assistant_manager.handle_message(formatted_audio_responses)
    )
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
    logger.debug(f"Vocab evaluation: {vocabulary_evaluation}")
    logger.debug(f"Vocab feedback: {vocabulary_feedback}")
    logger.debug(f"Tense evaluation: {tense_evaluation}")
    logger.debug(f"Tense feedback: {tense_feedback}")
    logger.debug(f"Style evaluation: {style_evaluation}")
    logger.debug(f"Style feedback: {style_feedback}")
    logger.debug(f"Grammar evaluation: {grammar_evaluation}")
    logger.debug(f"Grammar feedback: {grammar_feedback}")
    logger.debug(f"Audio evaluation: {audio_evaluation}")
    logger.debug(f"Audio feedback: {audio_feedback}")

    study_plan = study_plan_assistant_manager.handle_message(
        json.dumps(study_plan_response)
    )
    logger.debug(f"Study plan: {study_plan}")
    eval_start = study_plan.find("<output>") + len("<output>")
    eval_end = study_plan.find("</output>")
    study_plan = json.loads(study_plan[eval_start:eval_end])

    logger.debug(f"Study plan: {study_plan}")

    # """MOCK DATA"""
    # vocabulary_evaluation = agent_data.vocabulary_evaluation
    # vocabulary_feedback = agent_data.vocabulary_feedback
    # grammar_evaluation = agent_data.grammar_evaluation
    # grammar_feedback = agent_data.grammar_feedback
    # audio_evaluation = agent_data.audio_evaluation
    # audio_feedback = agent_data.audio_feedback
    # tense_evaluation = agent_data.tense_evaluation
    # tense_feedback = agent_data.tense_feedback
    # style_evaluation = agent_data.style_evaluation
    # style_feedback = agent_data.style_feedback
    # study_plan = agent_data.study_plan
    # """MOCK DATA"""

    logger.debug("Completed AI analysis for user {username}")

    return {
        "user_info": {"name": name, "age": age, "email": email},
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
    audio_assistant_manager,
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
        audio_assistant_manager,
        study_plan_assistant_manager,
    )

    # Create PDF
    pdf_path = f"reports/{username}_full_report.pdf"

    # Generate PDF content
    generate_pdf_content(analysis_data, pdf_path)

    # Save report path in database
    db_manager.mark_report_sent(username)
    return pdf_path


def setup_router(
    vocabulary_assistant_manager,
    tense_assistant_manager,
    style_assistant_manager,
    grammar_assistant_manager,
    audio_assistant_manager,
    mini_report_assistant_manager,
    study_plan_assistant_manager,
    db_manager,
    tg_bot_token,
    stripe_secret_key,
):
    router = Router()
    logger.info("Initializing router and handlers")

    # Move this here to ensure it's set before any Stripe operations
    # stripe.api_key = stripe_secret_key

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

    @router.message(Command(commands=["full_report"]))
    async def full_report(message: Message):
        username = message.from_user.username
        logger.info(f"Full report requested by user {username}")

        # Check if user has already paid
        # if db_manager.check_payment_status(username):
        # logger.debug(f"User {username} has already paid, generating report")
        report_sent = db_manager.check_report_sent(username)
        if report_sent:
            await message.answer("Отчет уже был отправлен ранее.")
            return

        await message.reply(
            "Генерация полного отчета... Это может занять около минуты."
        )
        pdf_path = await full_report_handler(
            db_manager,
            username,
            vocabulary_assistant_manager,
            tense_assistant_manager,
            style_assistant_manager,
            grammar_assistant_manager,
            audio_assistant_manager,
            study_plan_assistant_manager,
        )
        await message.answer_document(FSInputFile(pdf_path))
        return

        # # Create Stripe payment intent
        # try:

        #     # Create payment button
        #     payment_url = "https://buy.stripe.com/test_eVa6s33UH2G26UE288"
        #     keyboard = InlineKeyboardMarkup(
        #         inline_keyboard=[
        #             [InlineKeyboardButton(text="Оплатить $19.99", url=payment_url)]
        #         ]
        #     )

        #     await message.answer(
        #         "Для получения полного отчета нобходимо произвести оплату.",
        #         reply_markup=keyboard,
        #     )

        # except stripe.error.StripeError as e:
        #     logger.error(f"Stripe error for user {username}: {str(e)}")
        #     await message.reply(
        #         "Произошла ошибка при создании платежа. Пожалуйста, попробуйте позже."
        #     )

    # @router.pre_checkout_query()
    # async def process_pre_checkout_query(pre_checkout_query: PreCheckoutQuery):
    #     """Handle the pre-checkout query"""
    #     try:
    #         await pre_checkout_query.answer(ok=True)
    #     except Exception as e:
    #         logger.error(f"Error in pre-checkout: {str(e)}")
    #         await pre_checkout_query.answer(
    #             ok=False, error_message="Ошибка при обработке платежа"
    #         )

    # @router.message(F.text == "/stripe-webhook")
    # async def handle_stripe_webhook(message: Message):
    #     """Handle Stripe webhook events"""
    #     try:
    #         event = stripe.Event.construct_from(await request.json(), stripe.api_key)

    #         if event.type == "payment_intent.succeeded":
    #             payment_intent = event.data.object
    #             username = payment_intent.metadata.get("username")

    #             if username:
    #                 # Update payment status in database
    #                 db_manager.update_payment_status(username, True)

    #                 # Generate and send report
    #                 pdf_path = await full_report_handler(
    #                     db_manager,
    #                     username,
    #                     vocabulary_assistant_manager,
    #                     tense_assistant_manager,
    #                     style_assistant_manager,
    #                     grammar_assistant_manager,
    #                     audio_assistant_manager,
    #                     study_plan_assistant_manager,
    #                 )

    #                 # Send report to user
    #                 bot = Bot(token=tg_bot_token)
    #                 await bot.send_document(username, FSInputFile(pdf_path))
    #                 await bot.close()

    #         return {"status": "success"}

    #     except Exception as e:
    #         logger.error(f"Error processing webhook: {str(e)}")
    #         return {"status": "error", "message": str(e)}

    async def mini_report(message: Message):
        username = message.from_user.username
        logger.info(f"Mini report started for user {username}")

        # Generate new report if none exists
        await message.reply("Генерация краткого отчета... Пжалуйста, подождите.")
        report_text, payment_button = await mini_report_handler(
            db_manager, mini_report_assistant_manager, message.from_user.username
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
            await message.answer(AUDIO_QUESTIONS[0])
        else:
            await message.answer(ESSAY_QUESTIONS[essay_q_num + 1])

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

        text = await handle_voice_message(
            message, tg_bot_token, audio_assistant_manager
        )
        db_manager.save_user_response(
            username, audio_q_num + len(ESSAY_QUESTIONS), text
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
            await message.answer(
                "Вы уже заполнили опросник!\n\n"
                "Для приобретения полного отчета используйте команду /full_report"
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
        logger.debug(f"1")

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
                logger.debug(f"2")
                next_is_multi = choice_q_num + 1 >= len(BASIC_QUESTIONS_CHOICES) - 2
                logger.debug(f"3")
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
                logger.debug(f"4")
                if choice_q_num == len(BASIC_QUESTIONS_CHOICES) - 1:
                    logger.debug(f"5")
                    await callback_query.message.answer(ESSAY_QUESTIONS[0])
                else:
                    logger.debug(f"6")
                    try:
                        logger.debug(f"7")
                        await callback_query.message.edit_text(
                            BASIC_QUESTIONS_CHOICES[choice_q_num + 1],
                            reply_markup=keyboard,
                        )
                    except Exception:
                        logger.debug(f"8")
                        await callback_query.message.answer(
                            BASIC_QUESTIONS_CHOICES[choice_q_num + 1],
                            reply_markup=keyboard,
                        )
                logger.debug(f"9")
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
                await callback_query.message.answer(ESSAY_QUESTIONS[0])
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
