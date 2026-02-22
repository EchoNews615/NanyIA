import os
import sqlite3
from datetime import timedelta

import discord
from discord import app_commands
from discord.ext import commands
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("DISCORD_BOT_TOKEN", "")
GUILD_ID = int(os.getenv("DISCORD_GUILD_ID", "0") or 0)
ADMIN_ALERT_CHANNEL_ID = int(os.getenv("DISCORD_ADMIN_ALERT_CHANNEL_ID", "0") or 0)
TICKET_CATEGORY_ID = int(os.getenv("DISCORD_TICKET_CATEGORY_ID", "0") or 0)
MUTED_ROLE_NAME = os.getenv("DISCORD_MUTED_ROLE_NAME", "Mutado")

BAD_WORDS = {"idiota", "burro", "lixo", "fdp", "merda"}
CLAN_ROLES = [
    "Lider",
    "SubLider",
    "Admin",
    "Moderador",
    "Recrutador",
    "Estrategista",
    "Membro Elite",
    "Membro",
    "Visitante",
]

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
bot = commands.Bot(command_prefix="!", intents=intents)

conn = sqlite3.connect("new_clan_tickets.sqlite3")
conn.execute(
    """
    CREATE TABLE IF NOT EXISTS tickets (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      user_id TEXT NOT NULL,
      channel_id TEXT NOT NULL,
      reason TEXT,
      status TEXT NOT NULL DEFAULT 'open'
    )
    """
)
conn.commit()


@bot.event
async def on_ready():
    if GUILD_ID:
        guild = discord.Object(id=GUILD_ID)
        bot.tree.copy_global_to(guild=guild)
        await bot.tree.sync(guild=guild)
    else:
        await bot.tree.sync()
    print(f"Bot online como {bot.user}")


@bot.event
async def on_message(message: discord.Message):
    if message.author.bot:
        return

    lowered = message.content.lower()
    if "bot" in lowered:
        await message.channel.send(f"Fala, {message.author.mention}! Tô online e de olho 👀")

    if any(word in lowered for word in BAD_WORDS):
        alert = bot.get_channel(ADMIN_ALERT_CHANNEL_ID) if ADMIN_ALERT_CHANNEL_ID else None
        if alert:
            await alert.send(
                f"⚠️ Linguagem tóxica detectada em {message.channel.mention} por {message.author.mention}:\n{message.content}"
            )

    await bot.process_commands(message)


@bot.tree.command(name="setup_clan_roles", description="Cria os cargos padrão do New Clan")
async def setup_clan_roles(interaction: discord.Interaction):
    guild = interaction.guild
    if guild is None:
        return await interaction.response.send_message("Use dentro de um servidor.", ephemeral=True)

    created = []
    for role_name in CLAN_ROLES + [MUTED_ROLE_NAME]:
        if discord.utils.get(guild.roles, name=role_name) is None:
            await guild.create_role(name=role_name)
            created.append(role_name)

    await interaction.response.send_message(
        f"Cargos criados: {', '.join(created) if created else 'nenhum (já existiam)'}"
    )


@bot.tree.command(name="ticket", description="Abre um ticket para suporte")
@app_commands.describe(reason="Motivo do ticket")
async def ticket(interaction: discord.Interaction, reason: str):
    guild = interaction.guild
    if guild is None:
        return await interaction.response.send_message("Use dentro de um servidor.", ephemeral=True)

    category = guild.get_channel(TICKET_CATEGORY_ID) if TICKET_CATEGORY_ID else None
    overwrite = {
        guild.default_role: discord.PermissionOverwrite(view_channel=False),
        interaction.user: discord.PermissionOverwrite(view_channel=True, send_messages=True),
    }

    channel = await guild.create_text_channel(
        name=f"ticket-{interaction.user.name}"[:90],
        category=category,
        overwrites=overwrite,
    )

    conn.execute(
        "INSERT INTO tickets(user_id, channel_id, reason, status) VALUES (?, ?, ?, 'open')",
        (str(interaction.user.id), str(channel.id), reason),
    )
    conn.commit()

    await channel.send(f"🎫 Ticket aberto por {interaction.user.mention}\nMotivo: {reason}")
    await interaction.response.send_message(f"Ticket criado: {channel.mention}", ephemeral=True)


@bot.tree.command(name="close_ticket", description="Fecha o ticket atual")
async def close_ticket(interaction: discord.Interaction):
    channel = interaction.channel
    if channel is None:
        return
    conn.execute("UPDATE tickets SET status='closed' WHERE channel_id=?", (str(channel.id),))
    conn.commit()
    await interaction.response.send_message("Ticket fechado. Canal será removido em 5s.")
    await channel.send("Encerrando...")
    await discord.utils.sleep_until(discord.utils.utcnow() + timedelta(seconds=5))
    await channel.delete()


@bot.tree.command(name="mute", description="Muta um usuário")
@app_commands.describe(user="Usuário", minutes="Tempo em minutos")
async def mute(interaction: discord.Interaction, user: discord.Member, minutes: int = 10):
    guild = interaction.guild
    if guild is None:
        return await interaction.response.send_message("Use dentro de um servidor.", ephemeral=True)

    muted_role = discord.utils.get(guild.roles, name=MUTED_ROLE_NAME)
    if muted_role is None:
        muted_role = await guild.create_role(name=MUTED_ROLE_NAME)

    await user.add_roles(muted_role, reason=f"Mute de {minutes} min")
    await interaction.response.send_message(f"{user.mention} mutado por {minutes} minuto(s).")


@bot.tree.command(name="ban", description="Bane um usuário")
@app_commands.describe(user="Usuário", reason="Motivo")
async def ban(interaction: discord.Interaction, user: discord.Member, reason: str = "Sem motivo"):
    await interaction.guild.ban(user, reason=reason)
    await interaction.response.send_message(f"{user} banido. Motivo: {reason}")


if __name__ == "__main__":
    if not TOKEN:
        raise RuntimeError("Defina DISCORD_BOT_TOKEN no .env")
    bot.run(TOKEN)
