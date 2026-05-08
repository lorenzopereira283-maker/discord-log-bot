import discord
from discord.ext import commands
import os
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")

# Canais separados para cada tipo de log
JOIN_CHANNEL_ID  = int(os.getenv("JOIN_CHANNEL_ID"))   # canal: #entradas
LEAVE_CHANNEL_ID = int(os.getenv("LEAVE_CHANNEL_ID"))  # canal: #saídas
LOG_CHANNEL_ID   = int(os.getenv("LOG_CHANNEL_ID"))    # canal: #logs-gerais

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)


# ──────────────────────────────────────────────
#  FUNÇÕES AUXILIARES
# ──────────────────────────────────────────────
def embed_log(title, description, color, author=None):
    embed = discord.Embed(
        title=title,
        description=description,
        color=color,
        timestamp=datetime.utcnow()
    )
    if author:
        embed.set_author(name=str(author), icon_url=author.display_avatar.url)
    embed.set_footer(text="LogBot")
    return embed


async def send_to(guild, channel_id, embed):
    channel = guild.get_channel(channel_id)
    if channel:
        await channel.send(embed=embed)


# ──────────────────────────────────────────────
#  BOT READY
# ──────────────────────────────────────────────
@bot.event
async def on_ready():
    print(f"✅ Bot online como {bot.user}")
    print(f"   📥 Canal de entradas : {JOIN_CHANNEL_ID}")
    print(f"   📤 Canal de saídas   : {LEAVE_CHANNEL_ID}")
    print(f"   📋 Canal de logs     : {LOG_CHANNEL_ID}")


# ──────────────────────────────────────────────
#  MEMBRO ENTROU  →  canal #entradas
# ──────────────────────────────────────────────
@bot.event
async def on_member_join(member):
    embed = embed_log(
        "📥 Bem-vindo ao servidor!",
        f"👤 {member.mention} entrou no servidor.\n"
        f"🆔 **ID:** `{member.id}`\n"
        f"📅 **Conta criada:** {discord.utils.format_dt(member.created_at, 'R')}\n"
        f"👥 **Total de membros:** {member.guild.member_count}",
        discord.Color.green(),
        member
    )
    embed.set_thumbnail(url=member.display_avatar.url)
    await send_to(member.guild, JOIN_CHANNEL_ID, embed)


# ──────────────────────────────────────────────
#  MEMBRO SAIU  →  canal #saídas
# ──────────────────────────────────────────────
@bot.event
async def on_member_remove(member):
    roles = [r.mention for r in member.roles if r.name != "@everyone"]
    roles_text = ", ".join(roles) if roles else "Nenhum"

    embed = embed_log(
        "📤 Membro Saiu",
        f"👤 **{member}** saiu do servidor.\n"
        f"🆔 **ID:** `{member.id}`\n"
        f"📅 **Entrou em:** {discord.utils.format_dt(member.joined_at, 'R') if member.joined_at else 'Desconhecido'}\n"
        f"🏷️ **Cargos que tinha:** {roles_text}\n"
        f"👥 **Total de membros:** {member.guild.member_count}",
        discord.Color.red(),
        member
    )
    embed.set_thumbnail(url=member.display_avatar.url)
    await send_to(member.guild, LEAVE_CHANNEL_ID, embed)


# ──────────────────────────────────────────────
#  BANIMENTO  →  logs gerais
# ──────────────────────────────────────────────
@bot.event
async def on_member_ban(guild, user):
    embed = embed_log(
        "🔨 Membro Banido",
        f"**{user}** (`{user.id}`) foi banido do servidor.",
        discord.Color.dark_red(),
        user
    )
    await send_to(guild, LOG_CHANNEL_ID, embed)


@bot.event
async def on_member_unban(guild, user):
    embed = embed_log(
        "✅ Ban Removido",
        f"**{user}** (`{user.id}`) foi desbanido do servidor.",
        discord.Color.teal(),
        user
    )
    await send_to(guild, LOG_CHANNEL_ID, embed)


# ──────────────────────────────────────────────
#  ATUALIZAÇÃO DE MEMBRO  →  logs gerais
# ──────────────────────────────────────────────
@bot.event
async def on_member_update(before, after):
    changes = []

    if before.nick != after.nick:
        changes.append(f"**Nickname:** `{before.nick or 'Nenhum'}` → `{after.nick or 'Nenhum'}`")

    if before.roles != after.roles:
        added   = [r.mention for r in after.roles  if r not in before.roles]
        removed = [r.mention for r in before.roles if r not in after.roles]
        if added:   changes.append(f"**Cargos adicionados:** {', '.join(added)}")
        if removed: changes.append(f"**Cargos removidos:** {', '.join(removed)}")

    if changes:
        embed = embed_log("✏️ Membro Atualizado", "\n".join(changes), discord.Color.blue(), after)
        await send_to(after.guild, LOG_CHANNEL_ID, embed)


# ──────────────────────────────────────────────
#  MENSAGENS  →  logs gerais
# ──────────────────────────────────────────────
@bot.event
async def on_message_delete(message):
    if message.author.bot or not message.guild:
        return
    content = message.content or "*[sem conteúdo de texto]*"
    embed = embed_log(
        "🗑️ Mensagem Apagada",
        f"**Autor:** {message.author.mention}\n"
        f"**Canal:** {message.channel.mention}\n"
        f"**Conteúdo:** {content[:1024]}",
        discord.Color.red(),
        message.author
    )
    await send_to(message.guild, LOG_CHANNEL_ID, embed)


@bot.event
async def on_message_edit(before, after):
    if before.author.bot or not before.guild:
        return
    if before.content == after.content:
        return
    embed = embed_log(
        "✏️ Mensagem Editada",
        f"**Autor:** {before.author.mention}\n"
        f"**Canal:** {before.channel.mention}\n"
        f"**Antes:** {before.content[:512]}\n"
        f"**Depois:** {after.content[:512]}\n"
        f"[Ver mensagem]({after.jump_url})",
        discord.Color.gold(),
        before.author
    )
    await send_to(before.guild, LOG_CHANNEL_ID, embed)


# ──────────────────────────────────────────────
#  VOZ  →  logs gerais
# ──────────────────────────────────────────────
@bot.event
async def on_voice_state_update(member, before, after):
    if before.channel == after.channel:
        return
    if before.channel is None:
        title, desc, color = "🎙️ Entrou em Voz", f"{member.mention} entrou em **{after.channel.name}**", discord.Color.green()
    elif after.channel is None:
        title, desc, color = "🔇 Saiu de Voz", f"{member.mention} saiu de **{before.channel.name}**", discord.Color.red()
    else:
        title, desc, color = "🔀 Mudou de Canal de Voz", f"{member.mention} moveu-se de **{before.channel.name}** → **{after.channel.name}**", discord.Color.blue()
    embed = embed_log(title, desc, color, member)
    await send_to(member.guild, LOG_CHANNEL_ID, embed)


# ──────────────────────────────────────────────
#  CANAIS  →  logs gerais
# ──────────────────────────────────────────────
@bot.event
async def on_guild_channel_create(channel):
    embed = embed_log("📢 Canal Criado", f"**Nome:** {channel.mention}\n**Tipo:** {str(channel.type).capitalize()}", discord.Color.green())
    await send_to(channel.guild, LOG_CHANNEL_ID, embed)


@bot.event
async def on_guild_channel_delete(channel):
    embed = embed_log("🗑️ Canal Apagado", f"**Nome:** #{channel.name}\n**Tipo:** {str(channel.type).capitalize()}", discord.Color.red())
    await send_to(channel.guild, LOG_CHANNEL_ID, embed)


@bot.event
async def on_guild_channel_update(before, after):
    changes = []
    if before.name != after.name:
        changes.append(f"**Nome:** `{before.name}` → `{after.name}`")
    if hasattr(before, "topic") and before.topic != after.topic:
        changes.append(f"**Tópico:** `{before.topic}` → `{after.topic}`")
    if changes:
        embed = embed_log("🔧 Canal Atualizado", "\n".join(changes), discord.Color.blue())
        await send_to(after.guild, LOG_CHANNEL_ID, embed)


# ──────────────────────────────────────────────
#  CARGOS  →  logs gerais
# ──────────────────────────────────────────────
@bot.event
async def on_guild_role_create(role):
    embed = embed_log("🏷️ Cargo Criado", f"**Nome:** {role.mention}\n**Cor:** `{role.color}`", discord.Color.green())
    await send_to(role.guild, LOG_CHANNEL_ID, embed)


@bot.event
async def on_guild_role_delete(role):
    embed = embed_log("🗑️ Cargo Apagado", f"**Nome:** `{role.name}`", discord.Color.red())
    await send_to(role.guild, LOG_CHANNEL_ID, embed)


@bot.event
async def on_guild_role_update(before, after):
    changes = []
    if before.name != after.name:
        changes.append(f"**Nome:** `{before.name}` → `{after.name}`")
    if before.color != after.color:
        changes.append(f"**Cor:** `{before.color}` → `{after.color}`")
    if before.permissions != after.permissions:
        changes.append("**Permissões foram alteradas**")
    if changes:
        embed = embed_log("🔧 Cargo Atualizado", "\n".join(changes), discord.Color.blue())
        await send_to(after.guild, LOG_CHANNEL_ID, embed)


# ──────────────────────────────────────────────
#  SERVIDOR  →  logs gerais
# ──────────────────────────────────────────────
@bot.event
async def on_guild_update(before, after):
    changes = []
    if before.name != after.name:
        changes.append(f"**Nome:** `{before.name}` → `{after.name}`")
    if before.icon != after.icon:
        changes.append("**Ícone do servidor foi alterado**")
    if changes:
        embed = embed_log("🏠 Servidor Atualizado", "\n".join(changes), discord.Color.blue())
        await send_to(after, LOG_CHANNEL_ID, embed)


# ──────────────────────────────────────────────
#  EMOJIS  →  logs gerais
# ──────────────────────────────────────────────
@bot.event
async def on_guild_emojis_update(guild, before, after):
    added   = [e for e in after  if e not in before]
    removed = [e for e in before if e not in after]
    if added:
        embed = embed_log("😀 Emoji Adicionado", " ".join(str(e) for e in added), discord.Color.green())
        await send_to(guild, LOG_CHANNEL_ID, embed)
    if removed:
        embed = embed_log("😶 Emoji Removido", ", ".join(f"`:{e.name}:`" for e in removed), discord.Color.red())
        await send_to(guild, LOG_CHANNEL_ID, embed)


bot.run(TOKEN)
