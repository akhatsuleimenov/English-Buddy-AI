import psycopg2
from contextlib import contextmanager

from config.logger_config import logger

# Configure structured logging
logger = logger.getChild("database_manager")


class DatabaseManager:
    def __init__(self, db_url):
        logger.info(f"Initializing DatabaseManager with db_url: {db_url}")
        self.db_url = db_url
        self.initialize_db()

    def initialize_db(self):
        logger.info("Starting database initialization")
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS user_progress (
                    username TEXT PRIMARY KEY,
                    current_question INTEGER DEFAULT 0
                )
                """
            )
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS user_responses (
                    username TEXT,
                    question_number INTEGER,
                    response TEXT,
                    PRIMARY KEY (username, question_number)
                )
                """
            )
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS user_reports (
                    username TEXT PRIMARY KEY,
                    mini_report_sent BOOLEAN DEFAULT FALSE,
                    full_report_sent BOOLEAN DEFAULT FALSE,
                    report_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS user_info (
                    username TEXT,
                    question_number INTEGER,
                    info TEXT,
                    PRIMARY KEY (username, question_number)
                ) 
                """
            )
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS user_payments (
                    username TEXT PRIMARY KEY,
                    has_paid BOOLEAN DEFAULT FALSE,
                    payment_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            conn.commit()
            logger.info("Database tables initialized successfully")

    @contextmanager
    def get_connection(self):
        """Provide a transactional scope around a series of operations."""
        logger.debug("Attempting database connection")
        conn = psycopg2.connect(self.db_url)
        try:
            yield conn
            logger.debug("Database connection successful")
        except psycopg2.Error as e:
            logger.error(f"Database connection error: {e}", exc_info=True)
            raise
        finally:
            conn.close()
            logger.debug("Database connection closed")

    def get_current_question(self, username):
        logger.debug(f"Getting current question for user: {username}")
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT current_question FROM user_progress WHERE username = %s",
                (username,),
            )
            result = cursor.fetchone()
            if result is None:
                cursor.execute(
                    "INSERT INTO user_progress (username, current_question) VALUES (%s, 0)",
                    (username,),
                )
                conn.commit()
                logger.info(f"Initialized progress for new user {username}")
                return 0
            logger.debug(f"Retrieved current question {result[0]} for user {username}")
            return result[0]

    def update_current_question(self, username, question_number):
        logger.debug(f"Updating question to {question_number} for user {username}")
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO user_progress (username, current_question) 
                VALUES (%s, %s)
                ON CONFLICT (username) DO UPDATE 
                SET current_question = EXCLUDED.current_question
                """,
                (username, question_number),
            )
            conn.commit()
            logger.info(f"Updated question {question_number} for user {username}")

    def save_user_response(self, username, question_number, response):
        logger.debug(
            f"Saving response for user {username} on question {question_number}"
        )
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO user_responses (username, question_number, response)
                VALUES (%s, %s, %s)
                ON CONFLICT (username, question_number) DO UPDATE 
                SET response = EXCLUDED.response
                """,
                (username, question_number, response),
            )
            conn.commit()
            logger.info(
                f"Successfully saved response for user {username}, question {question_number}"
            )

    def get_all_user_responses(self, username):
        logger.debug(f"Retrieving all responses for user: {username}")
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT response 
                FROM user_responses 
                WHERE username = %s
                ORDER BY question_number
                """,
                (username,),
            )
            responses = [row[0] for row in cursor.fetchall()]
            logger.debug(f"Retrieved {len(responses)} responses for user {username}")
            return responses

    def save_user_info(self, username, question_number, info):
        logger.debug(f"Saving user info for {username} on question {question_number}")
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO user_info (username, question_number, info) VALUES (%s, %s, %s)",
                (username, question_number, info),
            )
            conn.commit()
            logger.info(
                f"Successfully saved user info for {username}, question {question_number}"
            )

    def get_user_info(self, username, question_number):
        logger.debug(
            f"Retrieving user info for {username} up to question {question_number}"
        )
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT question_number, info 
                FROM user_info 
                WHERE username = %s AND question_number < %s
                ORDER BY question_number
                """,
                (username, question_number),
            )
            results = cursor.fetchall()
            if not results:
                logger.debug(f"No user info found for {username}")
                return None

            logger.debug(f"Retrieved {len(results)} info entries for user {username}")
            return [info for _, info in results]

    def check_report_sent(self, username):
        logger.debug(f"Checking if report was sent for user: {username}")
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT full_report_sent FROM user_reports WHERE username = %s",
                (username,),
            )
            result = bool(cursor.fetchone())
            logger.debug(f"Report sent status for {username}: {result}")
            return result

    def mark_report_sent(self, username):
        logger.debug(f"Marking report as sent for user: {username}")
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO user_reports (username, full_report_sent) 
                VALUES (%s, TRUE)
                ON CONFLICT (username) DO UPDATE 
                SET full_report_sent = TRUE
                """,
                (username,),
            )
            conn.commit()
            logger.info(f"Successfully marked report as sent for user {username}")

    def check_payment_status(self, username):
        """Check if user has paid for the full report"""
        logger.debug(f"Checking payment status for user: {username}")
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT has_paid FROM user_payments WHERE username = %s", (username,)
            )
            result = cursor.fetchone()
            status = result[0] if result else False
            logger.debug(f"Payment status for {username}: {status}")
            return status

    def update_payment_status(self, username, status):
        """Update payment status for user"""
        logger.debug(f"Updating payment status to {status} for user: {username}")
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO user_payments (username, has_paid) 
                VALUES (%s, %s)
                ON CONFLICT (username) DO UPDATE 
                SET has_paid = EXCLUDED.has_paid
                """,
                (username, status),
            )
            conn.commit()
            logger.info(
                f"Successfully updated payment status for user {username} to {status}"
            )

    def mark_mini_report_sent(self, username):
        logger.debug(f"Marking mini report as sent for user: {username}")
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO user_reports (username, mini_report_sent) 
                VALUES (%s, TRUE)
                ON CONFLICT (username) DO UPDATE 
                SET mini_report_sent = TRUE
                """,
                (username,),
            )
            conn.commit()
            logger.info(f"Successfully marked mini report as sent for user {username}")

    def check_mini_report_sent(self, username):
        logger.debug(f"Checking if mini report was sent for user: {username}")
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT mini_report_sent FROM user_reports WHERE username = %s",
                (username,),
            )
            result = bool(cursor.fetchone())
            logger.debug(f"Mini report sent status for {username}: {result}")
            return result
