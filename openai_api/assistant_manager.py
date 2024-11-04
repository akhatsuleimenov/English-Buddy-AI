import time

from openai import OpenAI

from config.logger_config import logger

# Configure structured logging
logger = logger.getChild("assistant_manager")


class AssistantManager:
    def __init__(self, api_key, assistant_id):
        self.client = OpenAI(api_key=api_key)
        self.assistant = self.client.beta.assistants.retrieve(assistant_id)
        logger.info(f"Initialized AssistantManager with assistant ID: {assistant_id}")

    def create_thread(self):
        return self.client.beta.threads.create()

    def create_thread_message(self, thread_id, user_message):
        self.client.beta.threads.messages.create(
            thread_id=thread_id,
            role="user",
            content=[{"type": "text", "text": user_message}],
        )

    def create_run(self, thread_id):
        run = self.client.beta.threads.runs.create(
            thread_id=thread_id, assistant_id=self.assistant.id
        )
        logger.info(f"Started run in thread {thread_id}")

        while run.status == "queued" or run.status == "in_progress":
            time.sleep(1)
            run = self.client.beta.threads.runs.retrieve(
                thread_id=thread_id, run_id=run.id
            )

        if run.status == "failed":
            error_msg = f"Run failed in thread {thread_id}: {run.last_error.message}"
            logger.error(error_msg)
            raise Exception(error_msg)

        logger.info(f"Completed run in thread {thread_id} with status: {run.status}")

    def get_answer(self, thread_id):
        resp = self.client.beta.threads.messages.list(thread_id=thread_id)
        return resp.data[0].content[0].text.value

    def transcribe_audio(self, audio_file_path):
        logger.info(f"Starting audio transcription for file: {audio_file_path}")
        with open(audio_file_path, "rb") as audio_file:
            transcription = self.client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file,
            ).text
        logger.info("Audio transcription completed successfully")
        return transcription

    def handle_message(self, responses):
        logger.debug(f"Formatted message: {responses}")
        thread = self.create_thread()
        logger.info(f"Created new conversation thread: {thread.id}")

        self.create_thread_message(thread.id, responses)
        self.create_run(thread.id)

        answer = self.get_answer(thread.id)
        logger.info(f"Successfully processed message in thread {thread.id}")
        return answer
