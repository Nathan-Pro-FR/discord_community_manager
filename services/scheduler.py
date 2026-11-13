from datetime import date, datetime, timedelta
import discord
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy import select
from database.connection import AsyncSessionLocal
from database.models import ServerConfig, ReportRecord
from services.analytics import get_period_summary, compute_evolution

async def generate_and_send_report(bot: discord.Client, guild_id: int, period_type: str):
    today = date.today()
    days = {"weekly": 7, "monthly": 30, "quarterly": 90}[period_type]
    labels = {"weekly": "Hebdomadaire", "monthly": "Mensuel", "quarterly": "Trimestriel"}

    end_curr = today - timedelta(days=1)
    start_curr = end_curr - timedelta(days=days - 1)
    end_prev = start_curr - timedelta(days=1)
    start_prev = end_prev - timedelta(days=days - 1)

    curr = await get_period_summary(guild_id, start_curr, end_curr)
    prev = await get_period_summary(guild_id, start_prev, end_prev)

    msg_evo = compute_evolution(curr["total_messages"], prev["total_messages"])
    med_evo = compute_evolution(curr["media_posts"], prev["media_posts"])

    async with AsyncSessionLocal() as session:
        record = ReportRecord(
            guild_id=guild_id,
            period_type=period_type,
            start_date=start_curr,
            end_date=end_curr,
            summary_data={"current": curr, "previous": prev, "msg_evo": msg_evo, "med_evo": med_evo},
        )
        session.add(record)
        await session.commit()

        cfg = await session.get(ServerConfig, guild_id)
        if not cfg or not cfg.report_channel_id:
            return
        guild = bot.get_guild(guild_id)
        channel = guild.get_channel(cfg.report_channel_id) if guild else None
        if not channel:
            return

        embed = discord.Embed(
            title=f"📑 Rapport {labels[period_type]} ({start_curr} → {end_curr})",
            color=discord.Color.green(),
            timestamp=datetime.utcnow(),
        )
        embed.add_field(
            name="Messages totaux",
            value=f"**{curr['total_messages']}** ({msg_evo} vs période préc.)",
            inline=True,
        )
        embed.add_field(
            name="Publications médias",
            value=f"**{curr['media_posts']}** ({med_evo} vs période préc.)",
            inline=True,
        )
        embed.add_field(
            name="Membres (Arrivées / Départs)",
            value=f"+{curr['joins']} / -{curr['leaves']}",
            inline=True,
        )
        await channel.send(embed=embed)

async def check_activity_spikes(bot: discord.Client):
    """Détecte les pics d'activité inhabituels par rapport à la moyenne des 7 derniers jours."""
    today = date.today()
    async with AsyncSessionLocal() as session:
        configs = (await session.scalars(select(ServerConfig))).all()
        for cfg in configs:
            if not cfg.alert_channel_id:
                continue
            today_data = await get_period_summary(cfg.guild_id, today, today)
            week_data = await get_period_summary(cfg.guild_id, today - timedelta(days=7), today - timedelta(days=1))
            avg_daily = week_data["total_messages"] / 7.0
            if avg_daily >= 10:
                increase_pct = ((today_data["total_messages"] - avg_daily) / avg_daily) * 100
                if increase_pct >= cfg.spike_threshold_pct:
                    guild = bot.get_guild(cfg.guild_id)
                    ch = guild.get_channel(cfg.alert_channel_id) if guild else None
                    if ch:
                        await ch.send(
                            f"⚠️ **Pic d'activité détecté** : **{today_data['total_messages']}** messages aujourd'hui "
                            f"(+{increase_pct:.1f} % par rapport à la moyenne des 7 derniers jours)."
                        )

def setup_scheduler(bot: discord.Client) -> AsyncIOScheduler:
    scheduler = AsyncIOScheduler()

    async def run_all(period: str):
        async with AsyncSessionLocal() as session:
            configs = (await session.scalars(select(ServerConfig))).all()
            for cfg in configs:
                await generate_and_send_report(bot, cfg.guild_id, period)

    scheduler.add_job(run_all, "cron", day_of_week="mon", hour=8, minute=0, args=["weekly"])
    scheduler.add_job(run_all, "cron", day=1, hour=8, minute=15, args=["monthly"])
    scheduler.add_job(run_all, "cron", month="1,4,7,10", day=1, hour=8, minute=30, args=["quarterly"])
    scheduler.add_job(check_activity_spikes, "interval", hours=2, args=[bot])
    scheduler.start()
    return scheduler