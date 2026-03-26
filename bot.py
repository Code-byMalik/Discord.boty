import discord
from discord.ext import commands
from datetime import datetime, timedelta, timezone
import os
import asyncio
import yt_dlp
import ctypes
import ctypes.util
import ctypes
import ctypes.util


discord.opus.load_opus(ctypes.util.find_library('opus'))
#  KONFIGURATION – Umgebungsvariablen in Railway:
#  BOT_TOKEN  = dein Bot Token
#  ROLE_NAME  = Rolle die neue Member bekommen (Standard: Member)
# ============================================================

ROLE_NAME = os.environ.get("ROLE_NAME", "Member")

intents = discord.Intents.default()
intents.members = True
intents.message_content = True

bot = commands.Bot(command_prefix="/", intents=intents)

# ── Musik Queue ──────────────────────────────────────────────
music_queues = {}
now_playing  = {}

YTDL_OPTIONS = {
    "format": "bestaudio/best",
    "noplaylist": False,
    "quiet": True,
    "default_search": "ytsearch",
    "source_address": "0.0.0.0",
}

FFMPEG_OPTIONS = {
    "before_options": "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5",
    "options": "-vn",
}

warns = {}


# ── Audio Info holen ─────────────────────────────────────────
async def get_audio_info(query: str):
    loop = asyncio.get_event_loop()
    with yt_dlp.YoutubeDL(YTDL_OPTIONS) as ydl:
        info = await loop.run_in_executor(None, lambda: ydl.extract_info(query, download=False))
        if "entries" in info:
            info = info["entries"][0]
        return info["url"], info.get("title", "Unbekannt")


async def play_next(ctx):
    guild_id = ctx.guild.id
    queue = music_queues.get(guild_id, [])

    if not queue:
        now_playing.pop(guild_id, None)
        await ctx.send("✅ Queue ist leer – Wiedergabe beendet.")
        return

    url, title = queue.pop(0)
    music_queues[guild_id] = queue
    now_playing[guild_id] = title

    try:
        source = discord.FFmpegPCMAudio(url, **FFMPEG_OPTIONS)
    except Exception as e:
        await ctx.send(f"❌ FFmpeg Fehler: {e}")
        return

    def after_playing(error):
        if error:
            print(f"Player error: {error}")
        asyncio.run_coroutine_threadsafe(play_next(ctx), bot.loop)

    ctx.voice_client.play(source, after=after_playing)
    await ctx.send(f"🎵 Spielt jetzt: **{title}**")


# ════════════════════════════════════════════════════════════
#  EVENTS
# ════════════════════════════════════════════════════════════

@bot.event
async def on_ready():
    print(f"✅ Bot ist online als {bot.user} (ID: {bot.user.id})")
    print(f"   Auto-Rolle: '{ROLE_NAME}'")


@bot.event
async def on_member_join(member: discord.Member):
    guild = member.guild
    role = discord.utils.get(guild.roles, name=ROLE_NAME)
    if role is None:
        print(f"⚠️  Rolle '{ROLE_NAME}' nicht gefunden!")
        return
    try:
        await member.add_roles(role, reason="Auto-Rolle beim Beitreten")
        print(f"✅ Rolle '{role.name}' → {member}")
    except discord.Forbidden:
        print("❌ Keine Berechtigung für Auto-Rolle.")


# ════════════════════════════════════════════════════════════
#  MUSIK COMMANDS
# ════════════════════════════════════════════════════════════

@bot.command(name="join")
async def join(ctx):
    if not ctx.author.voice:
        return await ctx.send("❌ Du bist in keinem Voice-Channel!")
    channel = ctx.author.voice.channel
    try:
        if ctx.voice_client:
            await ctx.voice_client.move_to(channel)
        else:
            await channel.connect()
        await ctx.send(f"🔊 Beigetreten: **{channel.name}**")
    except Exception as e:
        await ctx.send(f"❌ Fehler beim Beitreten: `{e}`")


@bot.command(name="leave")
async def leave(ctx):
    if ctx.voice_client:
        await ctx.voice_client.disconnect()
        music_queues.pop(ctx.guild.id, None)
        await ctx.send("👋 Voice-Channel verlassen.")
    else:
        await ctx.send("❌ Ich bin in keinem Voice-Channel.")


@bot.command(name="play")
async def play(ctx, *, query: str):
    if not ctx.author.voice:
        return await ctx.send("❌ Du bist in keinem Voice-Channel!")

    # Voice beitreten falls nötig
    if not ctx.voice_client:
        try:
            await ctx.author.voice.channel.connect()
            await ctx.send(f"🔊 Verbunden mit **{ctx.author.voice.channel.name}**")
        except Exception as e:
            return await ctx.send(f"❌ Konnte Voice nicht beitreten: `{e}`")

    await ctx.send(f"🔍 Suche: `{query}`...")

    try:
        url, title = await get_audio_info(query)
        await ctx.send(f"✅ Gefunden: **{title}**")
    except Exception as e:
        return await ctx.send(f"❌ Fehler beim Laden: `{e}`")

    guild_id = ctx.guild.id
    if guild_id not in music_queues:
        music_queues[guild_id] = []

    if ctx.voice_client.is_playing() or ctx.voice_client.is_paused():
        music_queues[guild_id].append((url, title))
        await ctx.send(f"➕ Zur Queue hinzugefügt: **{title}** (Position {len(music_queues[guild_id])})")
    else:
        music_queues[guild_id].insert(0, (url, title))
        try:
            await play_next(ctx)
        except Exception as e:
            await ctx.send(f"❌ Fehler beim Abspielen: `{e}`")


@bot.command(name="skip")
async def skip(ctx):
    if ctx.voice_client and ctx.voice_client.is_playing():
        ctx.voice_client.stop()
        await ctx.send("⏭️ Song übersprungen.")
    else:
        await ctx.send("❌ Es wird gerade nichts abgespielt.")


@bot.command(name="pause")
async def pause(ctx):
    if ctx.voice_client and ctx.voice_client.is_playing():
        ctx.voice_client.pause()
        await ctx.send("⏸️ Pausiert.")
    else:
        await ctx.send("❌ Es wird gerade nichts abgespielt.")


@bot.command(name="resume")
async def resume(ctx):
    if ctx.voice_client and ctx.voice_client.is_paused():
        ctx.voice_client.resume()
        await ctx.send("▶️ Fortgesetzt.")
    else:
        await ctx.send("❌ Nichts pausiert.")


@bot.command(name="queue")
async def queue_cmd(ctx):
    guild_id = ctx.guild.id
    queue = music_queues.get(guild_id, [])
    current = now_playing.get(guild_id)

    if not current and not queue:
        return await ctx.send("📭 Queue ist leer.")

    msg = ""
    if current:
        msg += f"🎵 **Jetzt:** {current}\n\n"
    if queue:
        msg += "📋 **Queue:**\n"
        for i, (_, title) in enumerate(queue, 1):
            msg += f"`{i}.` {title}\n"
    await ctx.send(msg)


@bot.command(name="nowplaying")
async def nowplaying(ctx):
    current = now_playing.get(ctx.guild.id)
    if current:
        await ctx.send(f"🎵 Spielt gerade: **{current}**")
    else:
        await ctx.send("❌ Es wird gerade nichts abgespielt.")


# ════════════════════════════════════════════════════════════
#  ADMIN COMMANDS
# ════════════════════════════════════════════════════════════

@bot.command(name="timeout")
@commands.has_permissions(moderate_members=True)
async def timeout_cmd(ctx, member: discord.Member, duration: str, *, reason: str = "Kein Grund angegeben"):
    if not duration[:-1].isdigit() or duration[-1] not in ("m", "h", "d"):
        return await ctx.send("❌ Beispiel: `/timeout @User 10m Spam`")

    value = int(duration[:-1])
    unit = duration[-1]

    if unit == "m":
        delta, label = timedelta(minutes=value), f"{value} Minute(n)"
    elif unit == "h":
        delta, label = timedelta(hours=value), f"{value} Stunde(n)"
    elif unit == "d":
        delta, label = timedelta(days=value), f"{value} Tag(e)"

    try:
        until = datetime.now(timezone.utc) + delta
        await member.timeout(until, reason=reason)
        await ctx.send(f"🔇 **{member.display_name}** für **{label}** getimeouted.\n📝 Grund: {reason}")
    except discord.Forbidden:
        await ctx.send("❌ Keine Berechtigung für Timeout.")


@bot.command(name="untimeout")
@commands.has_permissions(moderate_members=True)
async def untimeout_cmd(ctx, member: discord.Member):
    try:
        await member.timeout(None)
        await ctx.send(f"✅ Timeout von **{member.display_name}** aufgehoben.")
    except discord.Forbidden:
        await ctx.send("❌ Keine Berechtigung.")


@bot.command(name="kick")
@commands.has_permissions(kick_members=True)
async def kick(ctx, member: discord.Member, *, reason: str = "Kein Grund angegeben"):
    try:
        await member.kick(reason=reason)
        await ctx.send(f"👢 **{member.display_name}** wurde gekickt.\n📝 Grund: {reason}")
    except discord.Forbidden:
        await ctx.send("❌ Keine Berechtigung.")


@bot.command(name="ban")
@commands.has_permissions(ban_members=True)
async def ban(ctx, member: discord.Member, *, reason: str = "Kein Grund angegeben"):
    try:
        await member.ban(reason=reason)
        await ctx.send(f"🔨 **{member.display_name}** wurde gebannt.\n📝 Grund: {reason}")
    except discord.Forbidden:
        await ctx.send("❌ Keine Berechtigung.")


@bot.command(name="unban")
@commands.has_permissions(ban_members=True)
async def unban(ctx, *, username: str):
    banned = [entry async for entry in ctx.guild.bans()]
    for entry in banned:
        if str(entry.user) == username:
            await ctx.guild.unban(entry.user)
            return await ctx.send(f"✅ **{username}** wurde entbannt.")
    await ctx.send(f"❌ **{username}** nicht in der Bannliste.")


@bot.command(name="warn")
@commands.has_permissions(manage_messages=True)
async def warn(ctx, member: discord.Member, *, reason: str = "Kein Grund angegeben"):
    guild_id = str(ctx.guild.id)
    user_id = str(member.id)

    if guild_id not in warns:
        warns[guild_id] = {}
    if user_id not in warns[guild_id]:
        warns[guild_id][user_id] = []

    warns[guild_id][user_id].append(reason)
    count = len(warns[guild_id][user_id])

    await ctx.send(f"⚠️ **{member.display_name}** verwarnt! (Gesamt: {count})\n📝 Grund: {reason}")
    try:
        await member.send(f"⚠️ Du wurdest auf **{ctx.guild.name}** verwarnt!\n📝 Grund: {reason}\nVerwarnungen gesamt: {count}")
    except discord.Forbidden:
        pass


@bot.command(name="warnings")
@commands.has_permissions(manage_messages=True)
async def warnings(ctx, member: discord.Member):
    guild_id = str(ctx.guild.id)
    user_id = str(member.id)
    user_warns = warns.get(guild_id, {}).get(user_id, [])

    if not user_warns:
        return await ctx.send(f"✅ **{member.display_name}** hat keine Verwarnungen.")

    msg = f"⚠️ Verwarnungen von **{member.display_name}** ({len(user_warns)}):\n"
    for i, reason in enumerate(user_warns, 1):
        msg += f"`{i}.` {reason}\n"
    await ctx.send(msg)


@bot.command(name="clearwarns")
@commands.has_permissions(administrator=True)
async def clearwarns(ctx, member: discord.Member):
    guild_id = str(ctx.guild.id)
    user_id = str(member.id)
    if guild_id in warns and user_id in warns[guild_id]:
        warns[guild_id][user_id] = []
    await ctx.send(f"✅ Alle Verwarnungen von **{member.display_name}** gelöscht.")


# ════════════════════════════════════════════════════════════
#  CLEAR COMMAND
# ════════════════════════════════════════════════════════════

@bot.command(name="clear")
@commands.has_permissions(manage_messages=True)
async def clear(ctx, amount: str):
    await ctx.message.delete()
    now = datetime.now(timezone.utc)

    if amount[-1] in ("h", "m", "d") and amount[:-1].isdigit():
        value = int(amount[:-1])
        unit = amount[-1]
        if unit == "m":
            delta, label = timedelta(minutes=value), f"{value} Minute(n)"
        elif unit == "h":
            delta, label = timedelta(hours=value), f"{value} Stunde(n)"
        elif unit == "d":
            delta, label = timedelta(days=value), f"{value} Tag(e)"

        cutoff = now - delta
        deleted = await ctx.channel.purge(limit=1000, check=lambda m: m.created_at >= cutoff)
        msg = await ctx.send(f"🗑️ {len(deleted)} Nachrichten der letzten {label} gelöscht.")

    elif amount.isdigit():
        deleted = await ctx.channel.purge(limit=int(amount))
        msg = await ctx.send(f"🗑️ {len(deleted)} Nachrichten gelöscht.")
    else:
        msg = await ctx.send("❌ Beispiele: `/clear 2h` `/clear 30m` `/clear 50`")

    await msg.delete(delay=5)


# ════════════════════════════════════════════════════════════
#  HILFE
# ════════════════════════════════════════════════════════════

@bot.command(name="hilfe")
async def hilfe(ctx):
    embed = discord.Embed(title="📖 Bot Befehle", color=0x5865F2)
    embed.add_field(name="🎵 Musik", value="""
`/play <Link/Suche>` – Musik abspielen
`/skip` – Song überspringen
`/pause` – Pausieren
`/resume` – Fortsetzen
`/queue` – Queue anzeigen
`/nowplaying` – Aktueller Song
`/join` – Voice beitreten
`/leave` – Voice verlassen
""", inline=False)
    embed.add_field(name="🛡️ Moderation", value="""
`/timeout @User 10m Grund` – Timeout
`/untimeout @User` – Timeout aufheben
`/kick @User Grund` – Kicken
`/ban @User Grund` – Bannen
`/unban User#1234` – Entbannen
`/warn @User Grund` – Verwarnen
`/warnings @User` – Verwarnungen anzeigen
`/clearwarns @User` – Verwarnungen löschen
`/clear 2h` – Chat löschen
""", inline=False)
    await ctx.send(embed=embed)


# ── Error Handler ────────────────────────────────────────────
@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send("❌ Du hast keine Berechtigung!", delete_after=5)
    elif isinstance(error, commands.MemberNotFound):
        await ctx.send("❌ Mitglied nicht gefunden!", delete_after=5)
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send("❌ Fehlende Argumente! Nutze `/hilfe`", delete_after=5)
    elif isinstance(error, commands.CommandNotFound):
        pass


bot.run(os.environ.get("BOT_TOKEN"))
