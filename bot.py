import discord
from discord.ext import commands
from datetime import datetime, timedelta, timezone
import os

# ============================================================
#  KONFIGURATION – Umgebungsvariablen
#  BOT_TOKEN   = dein Bot Token
#  ROLE_NAME   = Name der Rolle die neue Member bekommen
# ============================================================

ROLE_NAME = os.environ.get("ROLE_NAME", "Member")  # Standard: "Member"

intents = discord.Intents.default()
intents.members = True
intents.message_content = True

bot = commands.Bot(command_prefix="/", intents=intents)


# ── Bot online ───────────────────────────────────────────────
@bot.event
async def on_ready():
    print(f"✅ Bot ist online als {bot.user} (ID: {bot.user.id})")
    print(f"   Rolle bei Beitritt: '{ROLE_NAME}'")


# ── Automatische Rollenvergabe ───────────────────────────────
@bot.event
async def on_member_join(member: discord.Member):
    guild = member.guild
    role = discord.utils.get(guild.roles, name=ROLE_NAME)

    if role is None:
        print(f"⚠️  Rolle '{ROLE_NAME}' auf Server '{guild.name}' nicht gefunden!")
        return

    try:
        await member.add_roles(role, reason="Automatische Rollenvergabe beim Beitreten")
        print(f"✅ Rolle '{role.name}' wurde {member} ({member.id}) vergeben.")
    except discord.Forbidden:
        print(f"❌ Keine Berechtigung für Rolle '{role.name}'.")
    except discord.HTTPException as e:
        print(f"❌ Fehler: {e}")


# ── /clear Befehl ────────────────────────────────────────────
# Verwendung:
#   /clear 30m   → löscht Nachrichten der letzten 30 Minuten
#   /clear 2h    → löscht Nachrichten der letzten 2 Stunden
#   /clear 1d    → löscht Nachrichten des letzten Tages
#   /clear 50    → löscht die letzten 50 Nachrichten

@bot.command(name="clear")
@commands.has_permissions(manage_messages=True)
async def clear(ctx, amount: str):
    await ctx.message.delete()

    now = datetime.now(timezone.utc)

    # Zeit-Angabe parsen (z.B. 2h, 30m, 1d)
    if amount[-1] in ("h", "m", "d") and amount[:-1].isdigit():
        value = int(amount[:-1])
        unit = amount[-1]

        if unit == "m":
            delta = timedelta(minutes=value)
            label = f"{value} Minute(n)"
        elif unit == "h":
            delta = timedelta(hours=value)
            label = f"{value} Stunde(n)"
        elif unit == "d":
            delta = timedelta(days=value)
            label = f"{value} Tag(e)"

        cutoff = now - delta

        def is_old_enough(msg):
            return msg.created_at >= cutoff

        deleted = await ctx.channel.purge(limit=1000, check=is_old_enough)
        msg = await ctx.send(f"🗑️ {len(deleted)} Nachrichten der letzten {label} gelöscht.")

    # Anzahl-Angabe (z.B. 50)
    elif amount.isdigit():
        count = int(amount)
        deleted = await ctx.channel.purge(limit=count)
        msg = await ctx.send(f"🗑️ {len(deleted)} Nachrichten gelöscht.")

    else:
        msg = await ctx.send("❌ Ungültige Eingabe! Beispiele: `/clear 2h` `/clear 30m` `/clear 50`")

    # Bestätigungsnachricht nach 5 Sekunden löschen
    await msg.delete(delay=5)


@clear.error
async def clear_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send("❌ Du hast keine Berechtigung zum Löschen von Nachrichten!", delete_after=5)
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send("❌ Bitte gib eine Zeit oder Anzahl an! Beispiel: `/clear 2h`", delete_after=5)


bot.run(os.environ.get("BOT_TOKEN"))
