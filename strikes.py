from database import get_connection
from config import MAX_STRIKES


def get_strikes(chat_id, user_id):

    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        """
        SELECT strikes
        FROM users
        WHERE chat_id=? AND user_id=?
        """,
        (chat_id, user_id),
    )

    row = cur.fetchone()

    conn.close()

    if row:
        return row[0]

    return 0


def add_strike(chat_id, user_id, username, reason):

    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        """
        INSERT INTO users(chat_id,user_id,username,strikes)
        VALUES(?,?,?,1)

        ON CONFLICT(chat_id,user_id)

        DO UPDATE SET

        strikes = strikes + 1,
        username = excluded.username
        """,
        (chat_id, user_id, username),
    )

    conn.commit()

    cur.execute(
        """
        SELECT strikes
        FROM users
        WHERE chat_id=? AND user_id=?
        """,
        (chat_id, user_id),
    )

    strikes = cur.fetchone()[0]

    conn.close()

    action = "warn"

    if strikes >= MAX_STRIKES:
        action = "ban"

    elif strikes >= 3:
        action = "mute30"

    elif strikes >= 2:
        action = "mute5"

    return strikes, action


def reset_strikes(chat_id, user_id):

    conn = get_connection()

    cur = conn.cursor()

    cur.execute(
        """
        UPDATE users
        SET strikes=0
        WHERE chat_id=? AND user_id=?
        """,
        (chat_id, user_id),
    )

    conn.commit()

    conn.close()


def remove_strike(chat_id, user_id):

    conn = get_connection()

    cur = conn.cursor()

    cur.execute(
        """
        UPDATE users
        SET strikes = MAX(strikes-1,0)
        WHERE chat_id=? AND user_id=?
        """,
        (chat_id, user_id),
    )

    conn.commit()

    conn.close()
