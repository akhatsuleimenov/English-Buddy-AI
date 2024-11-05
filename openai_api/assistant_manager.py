import time
import logging

from openai import OpenAI

# Configure logger
logger = logging.getLogger(__name__)


class AssistantManager:
    def __init__(self, api_key, assistant_id):
        logger.info(f"Initializing AssistantManager with assistant_id: {assistant_id}")
        self.client = OpenAI(api_key=api_key)
        self.assistant = self.client.beta.assistants.retrieve(assistant_id)

    def create_thread(self):
        logger.debug("Creating new thread")
        return self.client.beta.threads.create()

    def create_thread_message(self, thread_id, user_message):
        logger.debug(f"Creating message in thread {thread_id}")
        self.client.beta.threads.messages.create(
            thread_id=thread_id,
            role="user",
            content=[{"type": "text", "text": user_message}],
        )

    def create_run(self, thread_id):
        max_retries = 5
        attempt = 0

        while attempt < max_retries:
            try:
                logger.debug(
                    f"Creating run for thread {thread_id} (attempt {attempt + 1}/{max_retries})"
                )
                run = self.client.beta.threads.runs.create(
                    thread_id=thread_id, assistant_id=self.assistant.id
                )

                while run.status == "queued" or run.status == "in_progress":
                    logger.debug(f"Run status: {run.status}")
                    time.sleep(1)
                    run = self.client.beta.threads.runs.retrieve(
                        thread_id=thread_id, run_id=run.id
                    )

                if run.status == "failed":
                    attempt += 1
                    error_msg = (
                        f"Run failed in thread {thread_id}: {run.last_error.message}"
                    )
                    logger.error(error_msg)
                    if attempt >= max_retries:
                        raise Exception(error_msg)
                    logger.info(f"Retrying in {2**attempt} seconds")
                    time.sleep(2**attempt)  # Exponential backoff
                    continue

                logger.info("Run completed successfully")
                return  # Success - exit the retry loop

            except Exception as e:
                attempt += 1
                logger.error(f"Error during run creation: {str(e)}", exc_info=True)
                if attempt >= max_retries:
                    raise
                logger.info(f"Retrying in {2**attempt} seconds")
                time.sleep(2**attempt)  # Exponential backoff

    def get_answer(self, thread_id):
        logger.debug(f"Getting answer from thread {thread_id}")
        resp = self.client.beta.threads.messages.list(thread_id=thread_id)
        return resp.data[0].content[0].text.value

    def transcribe_audio(self, audio_file_path):
        logger.debug(f"Transcribing audio file: {audio_file_path}")
        with open(audio_file_path, "rb") as audio_file:
            transcription = self.client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file,
            ).text
        logger.debug("Audio transcription completed")
        return transcription

    def handle_message(self, responses):
        logger.info("Starting message handling process")
        thread = self.create_thread()
        self.create_thread_message(thread.id, responses)
        self.create_run(thread.id)
        answer = self.get_answer(thread.id)
        logger.info("Message handling completed")
        return answer
