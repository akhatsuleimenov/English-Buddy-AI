import asyncio
import os
import google.generativeai as genai

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from dotenv import load_dotenv

from bot.handlers import setup_router
from database.db_manager import DatabaseManager
from openai_api.assistant_manager import AssistantManager

if os.path.exists(".env"):
    load_dotenv()

# Load environment variables
tg_bot_token = os.getenv("TG_BOT_TOKEN")
if not tg_bot_token:
    raise ValueError("TG_BOT_TOKEN environment variable is required")

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY environment variable is required")

# Load assistant IDs
VOCABULARY_AGENT_ID = os.getenv("VOCABULARY_AGENT_ID")
TENSE_AGENT_ID = os.getenv("TENSE_AGENT_ID")
STYLE_AGENT_ID = os.getenv("STYLE_AGENT_ID")
GRAMMAR_AGENT_ID = os.getenv("GRAMMAR_AGENT_ID")
AUDIO_AGENT_ID = os.getenv("AUDIO_AGENT_ID")
MINI_REPORT_AGENT_ID = os.getenv("MINI_REPORT_AGENT_ID")
STUDY_PLAN_AGENT_ID = os.getenv("STUDY_PLAN_AGENT_ID")

# Database configuration
DATABASE_URL = "database.db"
STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY")

# Initialize assistant managers
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
    system_instruction="...",  # System instruction remains unchanged
)

# Initialize database manager
db_manager = DatabaseManager(DATABASE_URL)

# Create and configure the bot
bot = Bot(token=tg_bot_token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()


async def main() -> None:
    try:
        # Get bot username
        bot_username = (await bot.get_me()).username

        # Setup router with dependencies
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
        raise


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
    except Exception as e:
        raise
