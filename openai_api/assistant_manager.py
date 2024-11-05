import time

from openai import OpenAI


class AssistantManager:
    def __init__(self, api_key, assistant_id):
        self.client = OpenAI(api_key=api_key)
        self.assistant = self.client.beta.assistants.retrieve(assistant_id)

    def create_thread(self):
        return self.client.beta.threads.create()

    def create_thread_message(self, thread_id, user_message):
        self.client.beta.threads.messages.create(
            thread_id=thread_id,
            role="user",
            content=[{"type": "text", "text": user_message}],
        )

    def create_run(self, thread_id):
        max_retries = 3
        attempt = 0

        while attempt < max_retries:
            try:
                run = self.client.beta.threads.runs.create(
                    thread_id=thread_id, assistant_id=self.assistant.id
                )

                while run.status == "queued" or run.status == "in_progress":
                    time.sleep(1)
                    run = self.client.beta.threads.runs.retrieve(
                        thread_id=thread_id, run_id=run.id
                    )

                if run.status == "failed":
                    attempt += 1
                    error_msg = (
                        f"Run failed in thread {thread_id}: {run.last_error.message}"
                    )
                    if attempt >= max_retries:
                        raise Exception(error_msg)
                    time.sleep(2**attempt)  # Exponential backoff
                    continue

                return  # Success - exit the retry loop

            except Exception as e:
                attempt += 1
                if attempt >= max_retries:
                    raise
                time.sleep(2**attempt)  # Exponential backoff

    def get_answer(self, thread_id):
        resp = self.client.beta.threads.messages.list(thread_id=thread_id)
        return resp.data[0].content[0].text.value

    def transcribe_audio(self, audio_file_path):
        with open(audio_file_path, "rb") as audio_file:
            transcription = self.client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file,
            ).text
        return transcription

    def handle_message(self, responses):
        thread = self.create_thread()
        self.create_thread_message(thread.id, responses)
        self.create_run(thread.id)
        answer = self.get_answer(thread.id)
        return answer
