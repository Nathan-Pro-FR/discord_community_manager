import os
from datetime import date, timedelta
import discord
from discord import app_commands
from discord.ext import commands
from sqlalchemy import select, func
from database.connection import AsyncSessionLocal
from database.models import MemberDailyStat, ChannelDailyStat
from services.analytics import get_period_summary, compute_evolution
from services.scheduler import generate_and_send_report

class StatsCommands(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="stats", description="Affiche les statistiques des 7 derniers jours avec évolution.")
    async def stats(self, interaction: discord.Interaction):
        today = date.today()
        curr = await get_period_summary(interaction.guild.id, today - timedelta(days=6), today)
        prev = await get_period_summary(interaction.guild.id, today - timedelta(days=13), today - timedelta(days=7))
        evo = compute_evolution(curr["total_messages"], prev["total_messages"])

        embed = discord.Embed(title="📈 Statistiques sur 7 jours", color=discord.Color.blue())
        embed.add_field(name="Messages", value=f"**{curr['total_messages']}** ({evo})", inline=True)
        embed.add_field(name="Médias", value=str(curr["media_posts"]), inline=True)
        embed.add_field(name="Membres actifs", value=str(curr["active_members"]), inline=True)
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="stats-member", description="Affiche la fiche d'activité d'un membre (7 derniers jours).")
    async def stats_member(self, interaction: discord.Interaction, membre: discord.Member):
        since = date.today() - timedelta(days=6)
        async with AsyncSessionLocal() as session:
            row = (
                await session.execute(
                    select(
                        func.coalesce(func.sum(MemberDailyStat.messages), 0),
                        func.coalesce(func.sum(MemberDailyStat.media_posts), 0),
                        func.count(func.distinct(MemberDailyStat.stat_date)),
                    ).where(
                        MemberDailyStat.guild_id == interaction.guild.id,
                        MemberDailyStat.user_id == membre.id,
                        MemberDailyStat.stat_date >= since,
                    )
                )
            ).one()

        embed = discord.Embed(title=f"👤 Profil statistique · {membre.display_name}", color=discord.Color.teal())
        embed.add_field(name="Messages (7j)", value=str(row[0]), inline=True)
        embed.add_field(name="Médias (7j)", value=str(row[1]), inline=True)
        embed.add_field(name="Jours actifs", value=f"{row[2]} / 7", inline=True)
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="stats-channel", description="Affiche les statistiques d'un salon sur 7 jours.")
    async def stats_channel(self, interaction: discord.Interaction, salon: discord.TextChannel):
        since = date.today() - timedelta(days=6)
        async with AsyncSessionLocal() as session:
            row = (
                await session.execute(
                    select(
                        func.coalesce(func.sum(ChannelDailyStat.messages), 0),
                        func.coalesce(func.sum(ChannelDailyStat.media_posts), 0),
                    ).where(
                        ChannelDailyStat.guild_id == interaction.guild.id,
                        ChannelDailyStat.channel_id == salon.id,
                        ChannelDailyStat.stat_date >= since,
                    )
                )
            ).one()
        await interaction.response.send_message(
            f"📊 **#{salon.name}** (7 derniers jours) : **{row[0]}** messages dont **{row[1]}** médias."
        )

    @app_commands.command(name="report-now", description="Génère immédiatement un bilan (weekly, monthly, quarterly).")
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.choices(periode=[
        app_commands.Choice(name="Hebdomadaire", value="weekly"),
        app_commands.Choice(name="Mensuel", value="monthly"),
        app_commands.Choice(name="Trimestriel", value="quarterly"),
    ])
    async def report_now(self, interaction: discord.Interaction, periode: str):
        await interaction.response.defer(ephemeral=True)
        await generate_and_send_report(self.bot, interaction.guild.id, periode)
        await interaction.followup.send("✅ Rapport généré et publié dans le salon des rapports.")

    @app_commands.command(name="dashboard", description="Obtient le lien vers le tableau de bord Web.")
    async def dashboard_link(self, interaction: discord.Interaction):
        url = os.getenv("DASHBOARD_URL", "http://localhost:8000")
        await interaction.response.send_message(f"🌐 Tableau de bord communautaire : {url}", ephemeral=True)

async def setup(bot: commands.Bot):
    await bot.add_cog(StatsCommands(bot))