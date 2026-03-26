import discord
from discord.ext import commands
import os

ROLE_NAME = "Member"  # Rollenname hier anpassen!

intents = discord.Intents.default()
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f"✅ Bot ist online als {bot.user}")

@bot.event
async def on_member_join(member: discord.Member):
    guild = member.guild
    role = discord.utils.get(guild.roles, name=ROLE_NAME)
    if role is None:
        print(f"⚠️ Rolle '{ROLE_NAME}' nicht gefunden!")
        return
    try:
        await member.add_roles(role)
        print(f"✅ Rolle '{role.name}' wurde {member} vergeben.")
    except discord.Forbidden:
        print(f"❌ Keine Berechtigung!")

bot.run(os.environ.get("BOT_TOKEN"))
