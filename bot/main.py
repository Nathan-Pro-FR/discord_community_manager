import os
import asyncio
import discord
from discord.ext import commands
from dotenv import load_dotenv
from database.connection import init_db
from services.scheduler import setup_scheduler

load_dotenv()

class CommunityManagerBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.guilds = True
        intents.members = True
        intents.messages = True
        intents.message_content = True  # Requis uniquement pour détecter les liens GIF dans les embeds
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        await init_db()
        await self.load_extension("bot.events.messages")
        await self.load_extension("bot.commands.setup")
        await self.load_extension("bot.commands.stats")
        await self.tree.sync()
        setup_scheduler(self)

    async def on_ready(self):
        print(f"✅ Connecté en tant que {self.user} (ID: {self.user.id})")

async def main():
    token = os.getenv("DISCORD_TOKEN")
    if not token:
        raise RuntimeError("Variable DISCORD_TOKEN manquante dans .env")
    bot = CommunityManagerBot()
    async with bot:
        await bot.start(token)

if __name__ == "__main__":
    asyncio.run(main())