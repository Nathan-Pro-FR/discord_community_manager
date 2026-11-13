from datetime import date, datetime, timedelta
from sqlalchemy import select, func
from database.connection import AsyncSessionLocal
from database.models import DailyStat, ChannelDailyStat, MemberDailyStat, ServerConfig

def classify_attachments(message) -> dict:
    """Distingue images, vidéos, GIF et fichiers joints sans lire le texte."""
    counts = {"image": 0, "video": 0, "gif": 0, "file": 0}
    for att in message.attachments:
        ctype = (att.content_type or "").lower()
        fname = att.filename.lower()
        if fname.endswith(".gif") or "gif" in ctype:
            counts["gif"] += 1
        elif ctype.startswith("image/"):
            counts["image"] += 1
        elif ctype.startswith("video/"):
            counts["video"] += 1
        else:
            counts["file"] += 1

    # Détection des liens GIF intégrés (Tenor / Giphy)
    for embed in message.embeds:
        if embed.type in ("gifv", "image") and embed.url and "gif" in embed.url.lower():
            counts["gif"] += 1
    return counts

def compute_evolution(current: int, previous: int) -> str:
    """Calcule l'évolution en pourcentage en gérant la division par zéro."""
    if previous == 0:
        return "Nouvelle activité" if current > 0 else "0,0 %"
    pct = ((current - previous) / previous) * 100
    sign = "+" if pct > 0 else ""
    return f"{sign}{pct:.1f} %".replace(".", ",")

async def record_message_event(message):
    today = date.today()
    guild_id = message.guild.id
    media = classify_attachments(message)
    has_media = sum(media.values()) > 0

    async with AsyncSessionLocal() as session:
        # 1. Statistiques globales du serveur
        daily = await session.scalar(
            select(DailyStat).where(DailyStat.guild_id == guild_id, DailyStat.stat_date == today)
        )
        if not daily:
            daily = DailyStat(guild_id=guild_id, stat_date=today)
            session.add(daily)

        daily.total_messages += 1
        if has_media:
            daily.media_posts += 1
            daily.images += media["image"]
            daily.videos += media["video"]
            daily.gifs += media["gif"]
            daily.files += media["file"]
        else:
            daily.text_messages += 1

        # 2. Statistiques par salon
        ch_stat = await session.scalar(
            select(ChannelDailyStat).where(
                ChannelDailyStat.guild_id == guild_id,
                ChannelDailyStat.channel_id == message.channel.id,
                ChannelDailyStat.stat_date == today,
            )
        )
        if not ch_stat:
            ch_stat = ChannelDailyStat(
                guild_id=guild_id,
                channel_id=message.channel.id,
                channel_name=message.channel.name,
                stat_date=today,
            )
            session.add(ch_stat)
        ch_stat.channel_name = message.channel.name
        ch_stat.messages += 1
        if has_media:
            ch_stat.media_posts += 1

        # 3. Statistiques par membre (si activées)
        cfg = await session.get(ServerConfig, guild_id)
        if not cfg or cfg.track_member_stats:
            m_stat = await session.scalar(
                select(MemberDailyStat).where(
                    MemberDailyStat.guild_id == guild_id,
                    MemberDailyStat.user_id == message.author.id,
                    MemberDailyStat.stat_date == today,
                )
            )
            if not m_stat:
                m_stat = MemberDailyStat(
                    guild_id=guild_id,
                    user_id=message.author.id,
                    username=message.author.display_name,
                    stat_date=today,
                )
                session.add(m_stat)
            m_stat.username = message.author.display_name
            m_stat.messages += 1
            if has_media:
                m_stat.media_posts += 1
            m_stat.last_active = datetime.utcnow()

        await session.commit()

async def get_period_summary(guild_id: int, start_dt: date, end_dt: date) -> dict:
    async with AsyncSessionLocal() as session:
        row = (
            await session.execute(
                select(
                    func.coalesce(func.sum(DailyStat.total_messages), 0),
                    func.coalesce(func.sum(DailyStat.text_messages), 0),
                    func.coalesce(func.sum(DailyStat.media_posts), 0),
                    func.coalesce(func.sum(DailyStat.images), 0),
                    func.coalesce(func.sum(DailyStat.videos), 0),
                    func.coalesce(func.sum(DailyStat.gifs), 0),
                    func.coalesce(func.sum(DailyStat.files), 0),
                    func.coalesce(func.sum(DailyStat.joins), 0),
                    func.coalesce(func.sum(DailyStat.leaves), 0),
                ).where(
                    DailyStat.guild_id == guild_id,
                    DailyStat.stat_date >= start_dt,
                    DailyStat.stat_date <= end_dt,
                )
            )
        ).one()

        active_members = await session.scalar(
            select(func.count(func.distinct(MemberDailyStat.user_id))).where(
                MemberDailyStat.guild_id == guild_id,
                MemberDailyStat.stat_date >= start_dt,
                MemberDailyStat.stat_date <= end_dt,
            )
        )

        top_channels = (
            await session.execute(
                select(
                    ChannelDailyStat.channel_name,
                    func.sum(ChannelDailyStat.messages).label("total"),
                )
                .where(
                    ChannelDailyStat.guild_id == guild_id,
                    ChannelDailyStat.stat_date >= start_dt,
                    ChannelDailyStat.stat_date <= end_dt,
                )
                .group_by(ChannelDailyStat.channel_name)
                .order_by(func.sum(ChannelDailyStat.messages).desc())
                .limit(5)
            )
        ).all()

        return {
            "total_messages": row[0],
            "text_messages": row[1],
            "media_posts": row[2],
            "images": row[3],
            "videos": row[4],
            "gifs": row[5],
            "files": row[6],
            "joins": row[7],
            "leaves": row[8],
            "active_members": active_members or 0,
            "top_channels": [{"name": c[0], "messages": c[1]} for c in top_channels],
        }