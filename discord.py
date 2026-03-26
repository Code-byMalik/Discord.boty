import discord
from discord.ext import commands
import os

# ============================================================
#  KONFIGURATION – hier anpassen!
# ============================================================
BOT_TOKEN   = "DEIN_BOT_TOKEN_HIER"   # Bot-Token aus dem Discord Developer Portal
ROLE_NAME   = "🌤"                 # Name der Rolle, die vergeben werden soll
# ============================================================

intents = discord.Intents.default()
intents.members = True   # Server Members Intent muss im Developer Portal aktiviert sein!

bot = commands.Bot(command_prefix="!", intents=intents)


@bot.event
async def on_ready():
    print(f"✅ Bot ist online als {bot.user} (ID: {bot.user.id})")
    print(f"   Verteile Rolle '{ROLE_NAME}' automatisch bei jedem Beitritt.")


@bot.event
async def on_member_join(member: discord.Member):
    """Wird ausgelöst, sobald ein neues Mitglied dem Server beitritt."""
    guild = member.guild

    # Rolle anhand des Namens suchen
    role = discord.utils.get(guild.roles, name=ROLE_NAME)

    if role is None:
        print(f"⚠️  Rolle '{ROLE_NAME}' wurde auf Server '{guild.name}' nicht gefunden!")
        return

    try:
        await member.add_roles(role, reason="Automatische Rollenvergabe beim Beitreten")
        print(f"✅ Rolle '{role.name}' wurde {member} ({member.id}) vergeben.")
    except discord.Forbidden:
        print(f"❌ Keine Berechtigung, um {member} die Rolle '{role.name}' zu geben.")
    except discord.HTTPException as e:
        print(f"❌ Fehler beim Vergeben der Rolle: {e}")


# Bot starten
bot.run(BOT_TOKEN)
