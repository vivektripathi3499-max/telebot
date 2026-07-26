from telegram import Update
from telegram.ext import ContextTypes
import asyncio


async def welcome(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not update.message:
        return

    if not update.message.new_chat_members:
        return

    for user in update.message.new_chat_members:

        text = f"""
👋 Welcome {user.mention_html()}!

📜 Please read the group rules.

❌ No spam

❌ No links

❌ No abuse

Enjoy your stay 😊
"""

        msg = await update.message.reply_html(text)

        await asyncio.sleep(60)

        try:
            await msg.delete()
        except:
            pass
