import discord
from discord import app_commands
from discord.ext import commands
from database.connection import AsyncSessionLocal
from database.models import ServerConfig
from services.embeds import refresh_live_embed

SFW_STRUCTURE = {
    "📌 ACCUEIL": {"text": ["règlement", "annonces", "présentation"], "voice": [], "private": False},
    "💬 COMMUNAUTÉ": {"text": ["général", "discussions", "questions"], "voice": [], "private": False},
    "🖼️ MÉDIAS": {"text": ["photos", "vidéos", "créations", "gif"], "voice": [], "private": False},
    "🎮 DIVERTISSEMENT": {"text": ["jeux", "sondages", "événements"], "voice": [], "private": False},
    "🤖 BOTS": {"text": ["commandes", "interactions"], "voice": [], "private": False},
    "📊 STATISTIQUES": {"text": ["activité", "rapports"], "voice": [], "private": False},
    "🛡️ MODÉRATION": {"text": ["signalements", "journal"], "voice": [], "private": True},
    "🔊 VOCAL": {"text": [], "voice": ["Général", "Détente", "Musique"], "private": False},
}

class ServerSetup(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="setup", description="Installe automatiquement l'architecture communautaire SFW sans doublons.")
    @app_commands.checks.has_permissions(administrator=True)
    async def setup_server(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        guild = interaction.guild

        # Création des rôles de base s'ils n'existent pas
        mod_role = discord.utils.get(guild.roles, name="Modérateur")
        if not mod_role:
            mod_role = await guild.create_role(name="Modérateur", color=discord.Color.orange(), reason="Setup automatique")
        if not discord.utils.get(guild.roles, name="Membre"):
            await guild.create_role(name="Membre", color=discord.Color.blue(), reason="Setup automatique")

        created_count = 0
        tracked_channels = {}

        for cat_name, spec in SFW_STRUCTURE.items():
            category = discord.utils.get(guild.categories, name=cat_name)
            if not category:
                overwrites = {}
                if spec["private"]:
                    overwrites = {
                        guild.default_role: discord.PermissionOverwrite(view_channel=False),
                        mod_role: discord.PermissionOverwrite(view_channel=True, send_messages=True),
                        guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True),
                    }
                category = await guild.create_category(cat_name, overwrites=overwrites)
                created_count += 1

            for ch_name in spec["text"]:
                existing = discord.utils.get(category.text_channels, name=ch_name)
                if not existing:
                    read_only = ch_name in ("règlement", "annonces", "activité", "rapports")
                    overwrites = {}
                    if read_only:
                        overwrites = {
                            guild.default_role: discord.PermissionOverwrite(send_messages=False, view_channel=True),
                            guild.me: discord.PermissionOverwrite(send_messages=True, view_channel=True),
                        }
                    existing = await guild.create_text_channel(ch_name, category=category, overwrites=overwrites)
                    created_count += 1
                tracked_channels[ch_name] = existing.id

            for v_name in spec["voice"]:
                if not discord.utils.get(category.voice_channels, name=v_name):
                    await guild.create_voice_channel(v_name, category=category)
                    created_count += 1

        async with AsyncSessionLocal() as session:
            cfg = await session.get(ServerConfig, guild.id)
            if not cfg:
                cfg = ServerConfig(guild_id=guild.id, guild_name=guild.name)
                session.add(cfg)
            cfg.guild_name = guild.name
            cfg.live_channel_id = tracked_channels.get("activité")
            cfg.report_channel_id = tracked_channels.get("rapports")
            cfg.alert_channel_id = tracked_channels.get("journal")
            await session.commit()

        await refresh_live_embed(self.bot, guild.id)
        await interaction.followup.send(
            f"✅ Configuration terminée ({created_count} éléments créés, doublons ignorés). "
            f"L'embed en direct est active dans <#{tracked_channels.get('activité')}>."
        )

    @app_commands.command(name="setup-check", description="Vérifie l'intégrité des salons configurés.")
    @app_commands.checks.has_permissions(administrator=True)
    async def setup_check(self, interaction: discord.Interaction):
        missing = []
        for cat_name, spec in SFW_STRUCTURE.items():
            cat = discord.utils.get(interaction.guild.categories, name=cat_name)
            if not cat:
                missing.append(f"Catégorie `{cat_name}`")
                continue
            for ch in spec["text"]:
                if not discord.utils.get(cat.text_channels, name=ch):
                    missing.append(f"Salon `#{ch}`")
        if not missing:
            await interaction.response.send_message("✅ Tous les éléments de la structure sont présents.", ephemeral=True)
        else:
            await interaction.response.send_message(
                "⚠️ Éléments manquants (lancez `/setup` pour réparer) :\n" + "\n".join(f"• {m}" for m in missing),
                ephemeral=True,
            )

async def setup(bot: commands.Bot):
    await bot.add_cog(ServerSetup(bot))