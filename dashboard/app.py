import os
import csv
import io
from datetime import date, timedelta
from fastapi import FastAPI, Request, Query, HTTPException
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from database.connection import AsyncSessionLocal, init_db
from database.models import DailyStat, ReportRecord, ServerConfig
from services.analytics import get_period_summary, compute_evolution

app = FastAPI(title="Discord Community Manager Dashboard")
templates = Jinja2Templates(directory="dashboard/templates")
ADMIN_TOKEN = os.getenv("DASHBOARD_ADMIN_TOKEN", "")

@app.on_event("startup")
async def startup():
    await init_db()

@app.get("/", response_class=HTMLResponse)
async def index(request: Request, token: str = Query(default="")):
    if ADMIN_TOKEN and token != ADMIN_TOKEN:
        raise HTTPException(status_code=403, detail="Accès réservé aux administrateurs (?token=...)")

    today = date.today()
    start_7d = today - timedelta(days=6)
    prev_start = today - timedelta(days=13)
    prev_end = today - timedelta(days=7)

    async with AsyncSessionLocal() as session:
        server = await session.scalar(select(ServerConfig).limit(1))
        guild_id = server.guild_id if server else 0
        guild_name = server.guild_name if server else "Aucun serveur configuré"

        curr = await get_period_summary(guild_id, start_7d, today)
        prev = await get_period_summary(guild_id, prev_start, prev_end)

        rows = (
            await session.scalars(
                select(DailyStat)
                .where(DailyStat.guild_id == guild_id, DailyStat.stat_date >= start_7d)
                .order_by(DailyStat.stat_date.asc())
            )
        ).all()

        reports = (
            await session.scalars(
                select(ReportRecord).where(ReportRecord.guild_id == guild_id).order_by(ReportRecord.created_at.desc()).limit(10)
            )
        ).all()

    by_day = {r.stat_date: r.total_messages for r in rows}
    labels = [(start_7d + timedelta(days=i)).strftime("%d/%m") for i in range(7)]
    values = [by_day.get(start_7d + timedelta(days=i), 0) for i in range(7)]

    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "guild_name": guild_name,
            "curr": curr,
            "msg_evo": compute_evolution(curr["total_messages"], prev["total_messages"]),
            "med_evo": compute_evolution(curr["media_posts"], prev["media_posts"]),
            "chart_labels": labels,
            "chart_values": values,
            "reports": reports,
            "token": token,
        },
    )

@app.get("/export/csv")
async def export_csv(token: str = Query(default="")):
    if ADMIN_TOKEN and token != ADMIN_TOKEN:
        raise HTTPException(status_code=403, detail="Non autorisé")

    async with AsyncSessionLocal() as session:
        rows = (await session.scalars(select(DailyStat).order_by(DailyStat.stat_date.desc()).limit(90))).all()

    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["Date", "Messages_Totaux", "Texte", "Medias", "Images", "Videos", "GIF", "Arrives", "Departs"])
    for r in rows:
        writer.writerow([r.stat_date, r.total_messages, r.text_messages, r.media_posts, r.images, r.videos, r.gifs, r.joins, r.leaves])

    buf.seek(0)
    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=statistiques_discord.csv"},
    )