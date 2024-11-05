import asyncio
import os
import google.generativeai as genai

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from dotenv import load_dotenv

from bot.handlers import setup_router
from config.logger_config import logger
from database.db_manager import DatabaseManager
from openai_api.assistant_manager import AssistantManager

# Configure structured logging
logger = logger.getChild("main")

if os.path.exists(".env"):
    logger.debug("Loading environment variables from .env file")
    load_dotenv()

# Load environment variables
tg_bot_token = os.getenv("TG_BOT_TOKEN")
if not tg_bot_token:
    logger.error("Telegram bot token not found in environment variables")
    raise ValueError("TG_BOT_TOKEN environment variable is required")

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    logger.error("OpenAI API key not found in environment variables")
    raise ValueError("OPENAI_API_KEY environment variable is required")

# Load assistant IDs
logger.debug("Loading OpenAI assistant IDs")
VOCABULARY_AGENT_ID = os.getenv("VOCABULARY_AGENT_ID")
TENSE_AGENT_ID = os.getenv("TENSE_AGENT_ID")
STYLE_AGENT_ID = os.getenv("STYLE_AGENT_ID")
GRAMMAR_AGENT_ID = os.getenv("GRAMMAR_AGENT_ID")
AUDIO_AGENT_ID = os.getenv("AUDIO_AGENT_ID")
MINI_REPORT_AGENT_ID = os.getenv("MINI_REPORT_AGENT_ID")
STUDY_PLAN_AGENT_ID = os.getenv("STUDY_PLAN_AGENT_ID")
# Database configuration
DATABASE_URL = "database.db"
logger.info(f"Using database at: {DATABASE_URL}")
STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY")


# Initialize assistant managers
logger.debug("Initializing OpenAI assistant managers")
vocabulary_assistant_manager = AssistantManager(
    api_key=OPENAI_API_KEY, assistant_id=VOCABULARY_AGENT_ID
)
tense_assistant_manager = AssistantManager(
    api_key=OPENAI_API_KEY, assistant_id=TENSE_AGENT_ID
)
style_assistant_manager = AssistantManager(
    api_key=OPENAI_API_KEY, assistant_id=STYLE_AGENT_ID
)
grammar_assistant_manager = AssistantManager(
    api_key=OPENAI_API_KEY, assistant_id=GRAMMAR_AGENT_ID
)
mini_report_assistant_manager = AssistantManager(
    api_key=OPENAI_API_KEY, assistant_id=MINI_REPORT_AGENT_ID
)
study_plan_assistant_manager = AssistantManager(
    api_key=OPENAI_API_KEY, assistant_id=STUDY_PLAN_AGENT_ID
)

genai.configure(api_key=os.environ["GEMINI_API_KEY"])

audio_model_genai = genai.GenerativeModel(
    model_name="gemini-1.5-flash-8b",
    generation_config={
        "temperature": 1,
        "top_p": 0.95,
        "top_k": 40,
        "max_output_tokens": 8192,
        "response_mime_type": "text/plain",
    },
    system_instruction='Вы являетесь ИИ-оценщиком языковых навыков, задачей которого является оценка произношения и разговорных навыков пользователя на английском языке. Ваша цель — оценить речь пользователя на основе следующих метрик речи:\n\nПлавность и Скорость Речи (20%)\n\nИзмеряет, насколько плавно пользователь говорит без ненужных пауз. Скорость речи около 120-160 слов в минуту считается оптимальной для средних и продвинутых уровней.\n\nПроизношение и Понятность (20%)\n\nОценивает четкость речи и то, насколько легко ИИ может правильно транскрибировать голос пользователя. Ошибки в произношении должны отмечаться, но значительно влияют на оценку только если затрудняют понимание.\n\nДиапазон и Точность Грамматики (25%)\n\nОценивает диапазон и точность грамматических конструкций. ИИ может отмечать:\n\nИспользование времен (настоящее, прошедшее, будущее)\n\nСтруктуры предложений (простые, сложносочиненные, сложноподчиненные)\n\nСогласование подлежащего и сказуемого, правильное использование артиклей, предлогов и т.д.\n\nДиапазон и Точность Словарного Запаса (25%)\n\nИзмеряет диапазон используемого словарного запаса и его уместность. ИИ проверит:\n\nРазнообразие слов (избегание повторений)\n\nИспользование тематической лексики (повседневные дела, путешествия, будущие цели)\n\nНеправильное или неверное использование слов.\n\nСвязность и Организация (10%)\n\nОценивает логичность изложения идей. ИИ проверит, хорошо ли структурированы ответы пользователя и легко ли их понять.\n\nВот аудиоответ пользователя:\n\n<audio_response>\n{{QUESTION}} : {{USER_AUDIO_RESPONSE}}\n</audio_response>\n\nДля оценки произношения и разговорных навыков пользователя выполните следующие шаги:\n\nВнимательно прослушайте и проанализируйте аудиоответ пользователя.\n\nИдентифицируйте примеры правильного и неправильного использования в каждой из категорий метрик речи.\n\nОцените производительность пользователя в каждой категории согласно указанным процентам.\n\nОпределите общую оценку пользователя и назначьте уровень CEFR на основе следующих критериев:\n\nНазначение уровня CEFR:\nC2 (90-100%): Беглая речь, точная грамматика и широкий словарный запас с почти идеальной связностью.\n\nC1 (75-89%): В целом точная речь, незначительные грамматические или лексические ошибки.\n\nB2 (60-74%): Хорошая беглость, периодические ошибки в более сложных конструкциях.\n\nB1 (45-59%): Ограниченный, но функциональный словарный запас, частые грамматические ошибки, медленная речь.\n\nA2 (30-44%): Базовая грамматика и словарный запас, заметные паузы и ошибки.\n\nA1 (ниже 30%): Очень простые фразы, ограниченная беглость и точность.\n\nИспользуйте следующие рекомендации для выставления оценок:\n\nПлавность и Скорость Речи (20%)\n\nОцените по шкале от 0 до 20, основываясь на скорости речи и плавности.\n\nПроизношение и Понятность (20%)\n\nОцените по шкале от 0 до 20, основываясь на четкости и легкости понимания.\n\nДиапазон и Точность Грамматики (25%)\n\nОцените по шкале от 0 до 25, основываясь на грамматической корректности и сложности.\n\nДиапазон и Точность Словарного Запаса (25%)\n\nОцените по шкале от 0 до 25, основываясь на использовании словарного запаса и его уместности.\n\nСвязность и Организация (10%)\n\nОцените по шкале от 0 до 10, основываясь на логичности изложения и структуре.\n\nОбщая оценка будет из 100 баллов.\n\nПрежде чем предоставить окончательную оценку, используйте черновик для анализа ответа и делайте заметки по конкретным примерам в каждой категории. Ваш черновик должен выглядеть следующим образом:\n\n<scratchpad>\nПлавность и Скорость Речи:\n- [Примеры и заметки]\nПроизношение и Понятность:\n\n[Примеры и заметки]\n\nДиапазон и Точность Грамматики:\n\n[Примеры и заметки]\n\nДиапазон и Точность Словарного Запаса:\n\n[Примеры и заметки]\n\nСвязность и Организация:\n\n[Примеры и заметки]\n\nОбщие наблюдения:\n[Любые дополнительные мысли или замеченные шаблоны]\n</scratchpad>\n\nПосле анализа предоставьте окончательную оценку в формате JSON внутри тегов <evaluation>. JSON должен включать оценки по каждому аспекту, а также краткие обоснования каждой оценки и общий уровень CEFR. Вот структура:\n\n<evaluation>\n{\n  "Плавность и Скорость Речи": {\n    "score": 0,\n  "max_score": 20,\n  "justification": ""\n  },\n  "Произношение и Понятность": {\n    "score": 0,\n "max_score": 20,\n   "justification": ""\n  },\n  "Диапазон и Точность Грамматики": {\n    "score": 0,\n "max_score": 25,\n   "justification": ""\n  },\n  "Диапазон и Точность Словарного Запаса": {\n    "score": 0,\n "max_score": 25,\n   "justification": ""\n  },\n  "Связность и Организация": {\n    "score": 0,\n "max_score": 10,\n    "justification": ""\n  },\n  "overall": {\n    "score": 0,\n  "max_score": 100,\n  "strengths": [],\n    "areas_for_improvement": [],\n    "summary": ""\n  }\n}\n</evaluation>\nНаконец, предоставьте подробный раздел обратной связи в формате JSON внутри тегов <feedback>, который включает:\n\n"Specific examples that demonstrate strong skills": []\n\n"Areas where improvement is needed": []\n\n"Suggested exercises or practice activities": []\n\n"General recommendations for further development": []\n\nВаша обратная связь должна быть конструктивной, ясной и действенной. Используйте конкретные примеры из ответа пользователя, чтобы проиллюстрировать как сильные стороны, так и области для улучшения.\n\n<feedback>\n{\n  "Specific examples that demonstrate strong skills": [],\n  "Areas where improvement is needed": [],\n  "Suggested exercises or practice activities": [],\n  "General recommendations for further development": []\n}\n</feedback>\nПомните, что вы должны сохранять поддерживающий и ободряющий тон на протяжении всей оценки, при этом предоставляя точную и полезную обратную связь для улучшения.\n\nВозвращайте только текст JSON, который находится внутри тегов <evaluation> </evaluation> и <feedback> </feedback>. Ваш ответ должен быть на русском языке.\n\nДайте как можно больше деталей на каждую секцию, чем больше данных тем лучше.',
)

# Initialize database manager
logger.debug("Initializing database manager")
db_manager = DatabaseManager(DATABASE_URL)

# Create and configure the bot
logger.debug("Creating Telegram bot instance")
bot = Bot(token=tg_bot_token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()


async def main() -> None:
    logger.info("Starting bot polling...")
    try:
        # Get bot username
        bot_username = (await bot.get_me()).username

        # Setup router with dependencies
        logger.debug("Setting up router with dependencies")
        router = setup_router(
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
            STRIPE_SECRET_KEY,
        )
        dp.include_router(router)

        await dp.start_polling(bot, timeout=20, relax=0.1)
    except Exception as e:
        logger.error("Critical error during bot polling", exc_info=True)
        raise


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.critical("Unhandled exception caused bot to stop", exc_info=True)
        raise
