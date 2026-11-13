from datetime import date, datetime, timedelta
import discord
from database.connection import AsyncSessionLocal
from database.models import ServerConfig
from services.analytics import get_period_summary, compute_evolution

def build_live_embed(guild_name: str, today_stats: dict, yesterday_stats: dict) -> discord.Embed:
    evo = compute_evolution(today_stats["total_messages"], yesterday_stats["total_messages"])
    embed = discord.Embed(
        title=f"📊 ACTIVITÉ DU SERVEUR · {guild_name}",
        description=f"**{today_stats['total_messages']}** messages comptabilisés aujourd'hui ({evo} vs hier)",
        color=discord.Color.blurple(),
        timestamp=datetime.utcnow(),
    )
    embed.add_field(name="💬 Messages texte", value=str(today_stats["text_messages"]), inline=True)
    embed.add_field(name="🖼️ Publications médias", value=str(today_stats["media_posts"]), inline=True)
    embed.add_field(name="👥 Membres actifs", value=str(today_stats["active_members"]), inline=True)
    embed.add_field(name="📸 Images", value=str(today_stats["images"]), inline=True)
    embed.add_field(name="🎬 Vidéos", value=str(today_stats["videos"]), inline=True)
    embed.add_field(name="🎞️ GIF / Fichiers", value=f"{today_stats['gifs']} / {today_stats['files']}", inline=True)

    if today_stats["top_channels"]:
        top_txt = "\n".join(f"• **#{c['name']}** : {c['messages']} msg" for c in today_stats["top_channels"])
        embed.add_field(name="🔥 Salons les plus actifs", value=top_txt, inline=False)

    embed.set_footer(text="Mise à jour automatique groupée • Confidentialité respectée (aucun contenu stocké)")
    return embed

async def refresh_live_embed(bot: discord.Client, guild_id: int):
    async with AsyncSessionLocal() as session:
        cfg = await session.get(ServerConfig, guild_id)
        if not cfg or not cfg.live_channel_id:
            return

        guild = bot.get_guild(guild_id)
        if not guild:
            return
        channel = guild.get_channel(cfg.live_channel_id)
        if not channel:
            return

        today = date.today()
        today_stats = await get_period_summary(guild_id, today, today)
        yesterday_stats = await get_period_summary(guild_id, today - timedelta(days=1), today - timedelta(days=1))
        embed = build_live_embed(guild.name, today_stats, yesterday_stats)

        try:
            if cfg.live_message_id:
                msg = await channel.fetch_message(cfg.live_message_id)
                await msg.edit(embed=embed)
                return
        except discord.NotFound:
            pass

        sent = await channel.send(embed=embed)
        cfg.live_message_id = sent.id
        await session.commit()