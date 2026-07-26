from database import get_connection
from config import ADMIN_LOG_CHAT_ID


def save_log(chat_id, user_id, action, reason, severity):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        """
        INSERT INTO logs(
            chat_id,
            user_id,
            action,
            reason,
            severity
        )
        VALUES(?,?,?,?,?)
        """,
        (
            chat_id,
            user_id,
            action,
            reason,
            severity,
        ),
    )

    conn.commit()
    conn.close()


async def send_log(context, username, user_id, action, reason, severity):

    if ADMIN_LOG_CHAT_ID == 0:
        return

    text = f"""
🚨 Moderation Action

👤 User: {username}

🆔 ID: {user_id}

⚠ Action: {action}

📌 Reason: {reason}

🔥 Severity: {severity}
"""

    await context.bot.send_message(
        ADMIN_LOG_CHAT_ID,
        text
    )
