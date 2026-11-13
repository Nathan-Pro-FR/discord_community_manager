from datetime import date
import discord
from discord.ext import commands, tasks
from sqlalchemy import select
from database.connection import AsyncSessionLocal
from database.models import DailyStat
from services.analytics import record_message_event
from services.embeds import refresh_live_embed

class ActivityTracker(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.dirty_guilds: set[int] = set()
        self.batch_embed_updater.start()

    def cog_unload(self):
        self.batch_embed_updater.cancel()

    @tasks.loop(seconds=30)
    async def batch_embed_updater(self):
        """Mise à jour groupée toutes les 30s pour respecter les rate-limits Discord."""
        if not self.dirty_guilds:
            return
        guilds_to_update = list(self.dirty_guilds)
        self.dirty_guilds.clear()
        for guild_id in guilds_to_update:
            await refresh_live_embed(self.bot, guild_id)

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or not message.guild:
            return
        await record_message_event(message)
        self.dirty_guilds.add(message.guild.id)

    @commands.Cog.listener()
    async def on_message_edit(self, before: discord.Message, after: discord.Message):
        if after.author.bot or not after.guild or before.content == after.content:
            return
        async with AsyncSessionLocal() as session:
            stat = await session.scalar(
                select(DailyStat).where(DailyStat.guild_id == after.guild.id, DailyStat.stat_date == date.today())
            )
            if stat:
                stat.edited_messages += 1
                await session.commit()

    @commands.Cog.listener()
    async def on_message_delete(self, message: discord.Message):
        if not message.guild or (message.author and message.author.bot):
            return
        async with AsyncSessionLocal() as session:
            stat = await session.scalar(
                select(DailyStat).where(DailyStat.guild_id == message.guild.id, DailyStat.stat_date == date.today())
            )
            if stat:
                stat.deleted_messages += 1
                await session.commit()

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        if member.bot:
            return
        async with AsyncSessionLocal() as session:
            stat = await session.scalar(
                select(DailyStat).where(DailyStat.guild_id == member.guild.id, DailyStat.stat_date == date.today())
            )
            if not stat:
                stat = DailyStat(guild_id=member.guild.id, stat_date=date.today())
                session.add(stat)
            stat.joins += 1
            await session.commit()

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        if member.bot:
            return
        async with AsyncSessionLocal() as session:
            stat = await session.scalar(
                select(DailyStat).where(DailyStat.guild_id == member.guild.id, DailyStat.stat_date == date.today())
            )
            if not stat:
                stat = DailyStat(guild_id=member.guild.id, stat_date=date.today())
                session.add(stat)
            stat.leaves += 1
            await session.commit()

async def setup(bot: commands.Bot):
    await bot.add_cog(ActivityTracker(bot))