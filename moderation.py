from datetime import timedelta
import discord
from discord.ext import commands
import re

LINK_PATTERN = re.compile(
    r"(https?://\S+|www\.\S+|t\.me/\S+|telegram\.me/\S+|discord\.gg/\S+|bit\.ly/\S+|tinyurl\.com/\S+)",
    re.IGNORECASE,
)


def contains_link(text: str) -> bool:
  if not text:
    return False
  return bool(LINK_PATTERN.search(text))


class Moderation(commands.Cog):

  def __init__(self, bot):
    self.bot = bot

  @commands.Cog.listener()
  async def on_message(self, message: discord.Message):
    if message.author.bot or not message.guild:
      return

    content = message.content or ""
    content_lower = content.lower()

    # 1. Check for links, channel promotions, or "link in bio" / asking for DMs
    has_link_flag = contains_link(content)
    evasion_phrases = [
        "link in bio",
        "check bio",
        "dm me",
        "add me",
        "telegram.me",
        "t.me",
    ]
    is_evading = any(phrase in content_lower for phrase in evasion_phrases)

    if has_link_flag or is_evading:
      try:
        await message.delete()
        await message.author.timeout(
            timedelta(hours=1),
            reason=(
                "Policy violation: Unauthorized links, link in bio, or DM"
                " promotion."
            ),
        )
        await message.channel.send(
            f"{message.author.mention}, sharing links, asking for DMs, or promoting"
            " channels is not allowed.",
            delete_after=6,
        )
      except discord.Forbidden:
        print("Missing permissions to delete message or timeout user.")
      except discord.HTTPException as e:
        print(f"Failed to apply moderation action: {e}")
      return

    # 2. Check for stickers or attachments (GIFs/images containing sexual/NSFW content)
    if message.stickers or message.attachments:
      # If using an external AI filter or keyword check on attachment file names/metadata:
      for attachment in message.attachments:
        file_name = attachment.filename.lower()
        # Add basic extension block or hook into ai_filter.py here if available
        if any(
            ext in file_name for ext in [".gif", ".png", ".jpg", ".jpeg"]
        ):
          # Example: Pass attachment URL to your ai_filter.py or external scanner
          pass


async def setup(bot):
  await bot.add_cog(Moderation(bot))
