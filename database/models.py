from datetime import datetime, date
from sqlalchemy import BigInteger, String, Integer, Float, Boolean, Date, DateTime, JSON, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from database.connection import Base

class ServerConfig(Base):
    __tablename__ = "bot_config"
    guild_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    guild_name: Mapped[str] = mapped_column(String(120))
    live_channel_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    live_message_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    report_channel_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    alert_channel_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    track_member_stats: Mapped[bool] = mapped_column(Boolean, default=True)
    spike_threshold_pct: Mapped[float] = mapped_column(Float, default=50.0)

class DailyStat(Base):
    __tablename__ = "message_stats"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    guild_id: Mapped[int] = mapped_column(BigInteger, index=True)
    stat_date: Mapped[date] = mapped_column(Date, index=True)
    total_messages: Mapped[int] = mapped_column(Integer, default=0)
    text_messages: Mapped[int] = mapped_column(Integer, default=0)
    media_posts: Mapped[int] = mapped_column(Integer, default=0)
    images: Mapped[int] = mapped_column(Integer, default=0)
    videos: Mapped[int] = mapped_column(Integer, default=0)
    gifs: Mapped[int] = mapped_column(Integer, default=0)
    files: Mapped[int] = mapped_column(Integer, default=0)
    edited_messages: Mapped[int] = mapped_column(Integer, default=0)
    deleted_messages: Mapped[int] = mapped_column(Integer, default=0)
    joins: Mapped[int] = mapped_column(Integer, default=0)
    leaves: Mapped[int] = mapped_column(Integer, default=0)
    __table_args__ = (UniqueConstraint("guild_id", "stat_date", name="uq_guild_date"),)

class ChannelDailyStat(Base):
    __tablename__ = "channel_stats"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    guild_id: Mapped[int] = mapped_column(BigInteger, index=True)
    channel_id: Mapped[int] = mapped_column(BigInteger, index=True)
    channel_name: Mapped[str] = mapped_column(String(100))
    stat_date: Mapped[date] = mapped_column(Date, index=True)
    messages: Mapped[int] = mapped_column(Integer, default=0)
    media_posts: Mapped[int] = mapped_column(Integer, default=0)
    __table_args__ = (UniqueConstraint("guild_id", "channel_id", "stat_date", name="uq_channel_date"),)

class MemberDailyStat(Base):
    __tablename__ = "member_stats"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    guild_id: Mapped[int] = mapped_column(BigInteger, index=True)
    user_id: Mapped[int] = mapped_column(BigInteger, index=True)
    username: Mapped[str] = mapped_column(String(100))
    stat_date: Mapped[date] = mapped_column(Date, index=True)
    messages: Mapped[int] = mapped_column(Integer, default=0)
    media_posts: Mapped[int] = mapped_column(Integer, default=0)
    last_active: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    __table_args__ = (UniqueConstraint("guild_id", "user_id", "stat_date", name="uq_member_date"),)

class ReportRecord(Base):
    __tablename__ = "reports"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    guild_id: Mapped[int] = mapped_column(BigInteger, index=True)
    period_type: Mapped[str] = mapped_column(String(20))  # weekly, monthly, quarterly
    start_date: Mapped[date] = mapped_column(Date)
    end_date: Mapped[date] = mapped_column(Date)
    summary_data: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)