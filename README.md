# English Buddy AI Bot

A sophisticated Telegram bot that evaluates English language proficiency through interactive questionnaires and voice message analysis, powered by OpenAI's AI capabilities. The bot provides comprehensive language assessment and personalized learning plans.

## Features

- **Multi-Dimensional Assessment**
  - Interactive questionnaire for background evaluation
  - Voice message analysis for pronunciation assessment
  - Essay writing evaluation
  - Comprehensive language proficiency scoring

- **AI-Powered Analysis**
  - Specialized AI agents for:
    - Vocabulary assessment
    - Grammar analysis
    - Speaking style evaluation
    - Tense usage patterns
    - Audio transcription and analysis
    - Study plan generation

- **Detailed Reporting**
  - Mini report summary with key metrics
  - Comprehensive PDF reports including:
    - Detailed skill analysis
    - Personalized study plans
    - Resource recommendations
    - Progress tracking
    - Improvement strategies

## Technical Requirements

- Python 3.8+
- Telegram account
- OpenAI API access
- Google Gemini Flash API access
- PostgreSQL database
- Required Python packages (see `requirements.txt`)

## Installation

1. **Clone the Repository:**
   ```bash
   git clone https://github.com/akhatsuleimenov/english-buddy-ai.git
   cd english-buddy-ai
   ```

2. **Install Dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Environment Configuration:**
   Create a `.env` file with:
   ```plaintext
   TG_BOT_TOKEN='your_telegram_bot_token'
   OPENAI_API_KEY='your_openai_api_key'
   VOCABULARY_AGENT_ID='your_vocabulary_assistant_id'
   TENSE_AGENT_ID='your_tense_assistant_id'
   STYLE_AGENT_ID='your_style_assistant_id'
   GRAMMAR_AGENT_ID='your_grammar_assistant_id'
   AUDIO_AGENT_ID='your_audio_assistant_id'
   ADMIN_USERNAMES='comma_separated_admin_usernames'
   ```

## System Architecture

- **Database Management**: PostgreSQL for robust user data management and response tracking
- **AI Integration**: 
  - OpenAI assistants for text analysis and study planning
  - Gemini Flash for advanced audio processing and pronunciation analysis
- **PDF Report Generation**: Custom report generation with detailed analysis and study plans
- **Telegram Bot Interface**: Interactive user interface with support for text and voice inputs

## Assessment Process

1. **Initial Questionnaire**
   - Personal information collection
   - English background assessment
   - Learning goals identification

2. **Skill Evaluation**
   - Text-based responses (OpenAI)
   - Voice message analysis (Gemini Flash)
   - Essay writing assessment (OpenAI)

3. **Analysis & Reporting**
   - AI-powered response analysis
   - Comprehensive skill evaluation
   - Personalized study plan generation
   - Detailed PDF report creation

## Report Features

The generated PDF reports include:
- Detailed language skill analysis
- Personalized study plans (1, 3, 6, and 12 months)
- Recommended learning resources
- Specific improvement strategies
- Daily/weekly/monthly action plans

## Development

- Built with Python and aiogram framework
- Implements structured logging for debugging
- Uses ReportLab for PDF generation
- Includes comprehensive input validation
- Features modular architecture for easy maintenance

## License

Distributed under the MIT License. See `LICENSE` for more information.

## Support

For access and technical support:
- Contact: @akhatsuleimenov on Telegram
- Required: Authorization for bot access
