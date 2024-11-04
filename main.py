import asyncio
import os
import sqlite3

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
audio_assistant_manager = AssistantManager(
    api_key=OPENAI_API_KEY, assistant_id=AUDIO_AGENT_ID
)
mini_report_assistant_manager = AssistantManager(
    api_key=OPENAI_API_KEY, assistant_id=MINI_REPORT_AGENT_ID
)
study_plan_assistant_manager = AssistantManager(
    api_key=OPENAI_API_KEY, assistant_id=STUDY_PLAN_AGENT_ID
)
# Initialize database manager
logger.debug("Initializing database manager")
db_manager = DatabaseManager(DATABASE_URL)

# Create and configure the bot
logger.debug("Creating Telegram bot instance")
bot = Bot(token=tg_bot_token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()

# Setup router with dependencies
logger.debug("Setting up router with dependencies")
router = setup_router(
    vocabulary_assistant_manager,
    tense_assistant_manager,
    style_assistant_manager,
    grammar_assistant_manager,
    audio_assistant_manager,
    mini_report_assistant_manager,
    study_plan_assistant_manager,
    db_manager,
    tg_bot_token,
    STRIPE_SECRET_KEY,
)
dp.include_router(router)


async def main() -> None:
    logger.info("Starting bot polling...")
    try:
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
