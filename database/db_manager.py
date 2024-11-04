import datetime
import sqlite3
from contextlib import contextmanager

from config.logger_config import logger

# import psycopg2

# Configure structured logging
logger = logger.getChild("database_manager")


class DatabaseManager:
    def __init__(self, db_url):
        self.db_url = db_url
        self.initialize_db()

    def initialize_db(self):
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
                    username TEXT PRIMARY KEY
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
            logger.info("Database tables initialized")

    @contextmanager
    def get_connection(self):
        """Provide a transactional scope around a series of operations."""
        conn = sqlite3.connect(self.db_url)
        try:
            yield conn
        except sqlite3.Error as e:
            logger.error(f"Database error: {e}")
            raise
        finally:
            conn.close()

    def get_current_question(self, username):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT current_question FROM user_progress WHERE username = ?",
                (username,),
            )
            result = cursor.fetchone()
            if result is None:
                cursor.execute(
                    "INSERT INTO user_progress (username, current_question) VALUES (?, 0)",
                    (username,),
                )
                conn.commit()
                logger.info(f"Initialized progress for new user {username}")
                return 0
            return result[0]

    def update_current_question(self, username, question_number):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT OR REPLACE INTO user_progress (username, current_question) 
                VALUES (?, ?)
                """,
                (username, question_number),
            )
            conn.commit()
            logger.debug(f"Updated question {question_number} for user {username}")

    def save_user_response(self, username, question_number, response):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT OR REPLACE INTO user_responses (username, question_number, response)
                VALUES (?, ?, ?)
                """,
                (username, question_number, response),
            )
            conn.commit()
            logger.debug(
                f"Saved response for user {username}, question {question_number}"
            )

    def get_all_user_responses(self, username):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT response 
                FROM user_responses 
                WHERE username = ?
                ORDER BY question_number
                """,
                (username,),
            )
            return [row[0] for row in cursor.fetchall()]

    def mark_report_sent(self, username):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO user_reports (username) VALUES (?)", (username,)
            )
            conn.commit()
            logger.info(f"Report marked as sent for user {username}")

    def save_user_info(self, username, question_number, info):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO user_info (username, question_number, info) VALUES (?, ?, ?)",
                (username, question_number, info),
            )
            conn.commit()
            logger.info(
                f"User info saved for user {username}, question {question_number}"
            )

    def get_user_info(self, username, question_number):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT question_number, info 
                FROM user_info 
                WHERE username = ? AND question_number < ?
                ORDER BY question_number
                """,
                (username, question_number),
            )
            results = cursor.fetchall()
            if not results:
                return None

            return [info for _, info in results]

    def save_report_text(self, username, report_type, report_text):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO user_reports (username, report_type, report_text) VALUES (?, ?, ?)",
                (username, report_type, report_text),
            )
            conn.commit()
            logger.info(
                f"Report text saved for user {username}, report type {report_type}"
            )

    def check_report_sent(self, username):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT 1 FROM user_reports WHERE username = ?", (username,))
            return bool(cursor.fetchone())

    def mark_report_sent(self, username):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO user_reports (username) VALUES (?)", (username,)
            )
            conn.commit()

    def check_payment_status(self, username):
        """Check if user has paid for the full report"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT has_paid FROM user_payments WHERE username = ?", (username,)
            )
            result = cursor.fetchone()
            return result[0] if result else False

    def update_payment_status(self, username, status):
        """Update payment status for user"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO user_payments (username, has_paid) 
                VALUES (?, ?)
                ON CONFLICT(username) 
                DO UPDATE SET has_paid = ?
                """,
                (username, status, status),
            )
            conn.commit()
            logger.info(f"Payment status updated for user {username}: {status}")
