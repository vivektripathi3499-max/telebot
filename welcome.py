from telegram import Update
from telegram.ext import ContextTypes
import asyncio
import random

# A list of unique, surprising, and fun welcome messages
WELCOME_MESSAGES = [
    "🚨 Hold on everyone, {mention} just dropped into the chat! Quick, hide the snacks. Welcome aboard! 🎉",
    "✨ Look what the cat dragged in... Welcome, {mention}! Grab a virtual seat and don't touch the red button. 🔴",
    "🛸 A wild {mention} has appeared! Type /rules or just stay out of trouble. Welcome to the crew! 🚀",
    "🎉 Sound the alarms! {mention} has officially joined the sanctuary. Welcome! Let us know if you bring good vibes. 🌟",
    "⚡ Look alive, squad! {mention} just spawned in. Welcome to the chat—may your ping be low and your warnings be zero! 🎮"
]

async def welcome(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not update.message:
        return

    if not update.message.new_chat_members:
        return

    for user in update.message.new_chat_members:
        # Skip if the new member is a bot
        if user.is_bot:
            continue

        # Pick a random surprise message template
        template = random.choice(WELCOME_MESSAGES)
        
        # Format it with the user's HTML mention and include the rules block
        body = template.format(mention=user.mention_html())
        
        text = f"""
{body}

📜 Please read the group rules:
❌ No spam
❌ No links
❌ No abuse

Enjoy your stay 😊
"""

        # Send the message
        msg = await update.message.reply_html(text)

        # Wait 60 seconds then clean it up
        await asyncio.sleep(60)

        try:
            await msg.delete()
        except:
            pass
