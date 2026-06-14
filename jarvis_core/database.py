import sqlite3
import os
import json
import logging

logger = logging.getLogger(__name__)

class JarvisDatabase:
    def __init__(self, db_path="jarvis.db"):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                # Settings table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS settings (
                        key TEXT PRIMARY KEY,
                        value TEXT
                    )
                ''')
                
                # Memory table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS memory (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        topic TEXT,
                        content TEXT,
                        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                # Default settings
                cursor.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('wake_word', 'jarvis')")
                cursor.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('picovoice_key', '')")
                
                conn.commit()
                logger.info("Database initialized successfully.")
        except Exception as e:
            logger.error(f"Database initialization failed: {e}")

    def get_setting(self, key, default=None):
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT value FROM settings WHERE key = ?", (key,))
                row = cursor.fetchone()
                return row[0] if row else default
        except Exception as e:
            logger.error(f"Error getting setting {key}: {e}")
            return default

    def set_setting(self, key, value):
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (key, str(value)))
                conn.commit()
        except Exception as e:
            logger.error(f"Error setting {key}: {e}")

    def remember(self, topic, content):
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("INSERT INTO memory (topic, content) VALUES (?, ?)", (topic, content))
                conn.commit()
        except Exception as e:
            logger.error(f"Error saving memory: {e}")

    def recall(self, topic=None):
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                if topic:
                    cursor.execute("SELECT content FROM memory WHERE topic = ? ORDER BY timestamp DESC", (topic,))
                else:
                    cursor.execute("SELECT topic, content FROM memory ORDER BY timestamp DESC LIMIT 50")
                return cursor.fetchall()
        except Exception as e:
            logger.error(f"Error recalling memory: {e}")
            return []
