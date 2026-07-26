import sqlite3
import os

DB_PATH = "data/bot.db"

os.makedirs("data", exist_ok=True)

conn = sqlite3.connect(DB_PATH)

cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS users(

    chat_id INTEGER,

    user_id INTEGER,

    username TEXT,

    strikes INTEGER DEFAULT 0,

    warnings INTEGER DEFAULT 0,

    last_message TEXT,

    last_message_time REAL,

    PRIMARY KEY(chat_id,user_id)

)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS logs(

    id INTEGER PRIMARY KEY AUTOINCREMENT,

    chat_id INTEGER,

    user_id INTEGER,

    action TEXT,

    reason TEXT,

    severity INTEGER,

    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP

)
""")

conn.commit()


def get_connection():
    return sqlite3.connect(DB_PATH)
