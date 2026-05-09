import discord
from discord.ext import commands
from discord import app_commands
import os
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
JOIN_CHANNEL_ID = int(os.getenv('JOIN_CHANNEL_ID'))
LEAVE_CHANNEL_ID = int(os.getenv('LEAVE_CHANNEL_ID'))
LOG_CHANNEL_ID = int(os.getenv('LOG_CHANNEL_ID'))
LIBERAR_CHANNEL_ID = int(os.getenv('LIBERAR_CHANNEL_ID'))

intents = discord.Intents.all()
bot = commands.Bot(command_prefix='!', intents=intents)

# ───────────────────────────────────────────────
# HELPER: send embed to channel
# ───────────────────────────────────────────────
async def send_to(guild, channel_id, embed):
    channel = guild.get_channel(channel_id)
    if channel:
        await channel.send(embed=embed)

# ───────────────────────────────────────────────
# MODAL: Formulário de Liberação
# ───────────────────────────────────────────────
class LiberacaoModal(discord.ui.Modal, title='Sistema de Liberação'):
    identificador = discord.ui.TextInput(
        label='Identificador',
        placeholder='Ex: 12345',
        required=True,
        max_length=20
    )
    nome = discord.ui.TextInput(
        label='Nome e Sobrenome',
        placeholder='Ex: João Silva',
        required=True,
        max_length=50
    )
    cargo = discord.ui.TextInput(
        label='Cargo pretendido',
        placeholder='Suporte / Moderador / Admin / Diretor',
        required=True,
        max_length=20
    )

    async def on_submit(self, interaction: discord.Interaction):
        cargos_validos = ['suporte', 'moderador', 'admin', 'diretor']
        cargo_input = self.cargo.value.strip().lower()

        if cargo_input not in cargos_validos:
            await interaction.response.send_message(
                '❌ Cargo inválido! Escolhe entre: Suporte, Moderador, Admin ou Diretor.',
                ephemeral=True
            )
            return

        guild = interaction.guild

        # Encontrar cargos Diretor e Admin para permissões do ticket
        cargo_diretor = discord.utils.get(guild.roles, name='Diretor')
        cargo_admin = discord.utils.get(guild.roles, name='¦ Admin')

        # Encontrar ou criar categoria Tickets
        categoria = discord.utils.get(guild.categories, name='Tickets')
        if not categoria:
            categoria = await guild.create_category('Tickets')

        # Permissões do canal ticket
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            interaction.user: discord.PermissionOverwrite(view_channel=True, send_messages=False),
            guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True),
        }
        if cargo_diretor:
            overwrites[cargo_diretor] = discord.PermissionOverwrite(view_channel=True, send_messages=True)
        if cargo_admin:
            overwrites[cargo_admin] = discord.PermissionOverwrite(view_channel=True, send_messages=True)

        # Criar canal do ticket
        nome_canal = f'lib-{interaction.user.name}'.lower().replace(' ', '-')[:30]
        ticket_channel = await categoria.create_text_channel(nome_canal, overwrites=overwrites)

        # Embed do ticket
        embed = discord.Embed(
            title='📋 Pedido de Liberação',
            color=0x2ecc71,
            timestamp=datetime.utcnow()
        )
        embed.add_field(name='👤 Utilizador', value=interaction.user.mention, inline=True)
        embed.add_field(name='🆔 Identificador', value=self.identificador.value, inline=True)
        embed.add_field(name='📛 Nome', value=self.nome.value, inline=True)
        embed.add_field(name='🎖️ Cargo Pretendido', value=self.cargo.value.capitalize(), inline=True)
        embed.set_footer(text=f'ID: {interaction.user.id}')

        mencoes = ''
        if cargo_diretor:
            mencoes += cargo_diretor.mention + ' '
        if cargo_admin:
            mencoes += cargo_admin.mention

        view = TicketView(
            requerente=interaction.user,
            nome_personagem=self.nome.value,
            cargo_pretendido=self.cargo.value.capitalize()
        )

        await ticket_channel.send(content=mencoes, embed=embed, view=view)

        await interaction.response.send_message(
            f'✅ O teu pedido foi enviado! Aguarda resposta em {ticket_channel.mention}',
            ephemeral=True
        )


# ───────────────────────────────────────────────
# VIEW: Botões Aceitar / Recusar no ticket
# ───────────────────────────────────────────────
class TicketView(discord.ui.View):
    def __init__(self, requerente: discord.Member, nome_personagem: str, cargo_pretendido: str):
        super().__init__(timeout=None)
        self.requerente = requerente
        self.nome_personagem = nome_personagem
        self.cargo_pretendido = cargo_pretendido

    @discord.ui.button(label='✅ Aceitar', style=discord.ButtonStyle.success)
    async def aceitar(self, interaction: discord.Interaction, button: discord.ui.Button):
        guild = interaction.guild
        membro = guild.get_member(self.requerente.id)

        if not membro:
            await interaction.response.send_message('❌ Utilizador não encontrado no servidor.', ephemeral=True)
            return

        # Mudar apelido para Ac | Nome
        try:
            await membro.edit(nick=f'Ac | {self.nome_personagem}')
        except discord.Forbidden:
            pass

        # Dar cargo
        cargo_obj = discord.utils.find(
            lambda r: r.name.lower().strip('¦ ').strip() == self.cargo_pretendido.lower(),
            guild.roles
        )
        if cargo_obj:
            try:
                await membro.add_roles(cargo_obj)
            except discord.Forbidden:
                pass

        # Mensagem privada ao utilizador
        try:
            await membro.send(
                f'✅ O teu pedido de liberação foi **aceite**!\n'
                f'O teu apelido foi alterado para **Ac | {self.nome_personagem}** e recebeste o cargo **{self.cargo_pretendido}**.'
            )
        except discord.Forbidden:
            pass

        await interaction.response.send_message(f'✅ Pedido aceite por {interaction.user.mention}!')
        await interaction.channel.delete()

    @discord.ui.button(label='❌ Recusar', style=discord.ButtonStyle.danger)
    async def recusar(self, interaction: discord.Interaction, button: discord.ui.Button):
        guild = interaction.guild
        membro = guild.get_member(self.requerente.id)

        # Mensagem privada ao utilizador
        if membro:
            try:
                await membro.send(
                    f'❌ O teu pedido de liberação foi **recusado**.\n'
                    f'Podes tentar novamente mais tarde.'
                )
            except discord.Forbidden:
                pass

        await interaction.response.send_message(f'❌ Pedido recusado por {interaction.user.mention}.')
        await interaction.channel.delete()


# ───────────────────────────────────────────────
# VIEW: Botão principal "Realizar Liberação"
# ───────────────────────────────────────────────
class LiberacaoView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label='✅ Realizar Liberação', style=discord.ButtonStyle.success, custom_id='liberacao_btn')
    async def liberacao(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(LiberacaoModal())


# ───────────────────────────────────────────────
# COMANDO: !liberar — envia a mensagem de liberação
# ───────────────────────────────────────────────
@bot.command(name='liberar')
@commands.has_permissions(administrator=True)
async def liberar(ctx):
    embed = discord.Embed(
        title='🔓 Sistema de Liberação do Servidor',
        description=(
            '**Bem-vindo ao sistema de liberação!**\n\n'
            '• Conecta-te ao servidor primeiro e tem a tua identificação em mãos.\n'
            '• Clica no botão abaixo para preencheres o formulário.\n'
            '• Após o envio, um superior irá aceitar ou recusar o teu pedido.'
        ),
        color=0x2ecc71
    )
    embed.set_footer(text=ctx.guild.name)
    await ctx.send(embed=embed, view=LiberacaoView())
    await ctx.message.delete()


# ───────────────────────────────────────────────
# EVENTOS DE LOG
# ───────────────────────────────────────────────

@bot.event
async def on_ready():
    print(f'✅ Bot online como {bot.user}')
    channel_join = bot.get_channel(JOIN_CHANNEL_ID)
    channel_leave = bot.get_channel(LEAVE_CHANNEL_ID)
    channel_log = bot.get_channel(LOG_CHANNEL_ID)
    if channel_join:
        print(f'📥 Canal de entradas : {channel_join.name}')
    if channel_leave:
        print(f'📤 Canal de saídas   : {channel_leave.name}')
    if channel_log:
        print(f'📋 Canal de logs     : {channel_log.name}')
    # Registar view persistente
    bot.add_view(LiberacaoView())

# Membro entrou
@bot.event
async def on_member_join(member):
    embed = discord.Embed(
        title='📥 Membro Entrou',
        color=0x2ecc71,
        timestamp=datetime.utcnow()
    )
    embed.set_thumbnail(url=member.display_avatar.url)
    embed.add_field(name='Utilizador', value=f'{member.mention} ({member})', inline=False)
    embed.add_field(name='ID', value=member.id, inline=True)
    embed.add_field(name='Conta criada', value=f'há {(datetime.utcnow() - member.created_at.replace(tzinfo=None)).days} dias', inline=True)
    embed.add_field(name='Total de membros', value=member.guild.member_count, inline=True)
    await send_to(member.guild, JOIN_CHANNEL_ID, embed)

# Membro saiu
@bot.event
async def on_member_remove(member):
    embed = discord.Embed(
        title='📤 Membro Saiu',
        color=0xe74c3c,
        timestamp=datetime.utcnow()
    )
    embed.set_thumbnail(url=member.display_avatar.url)
    embed.add_field(name='Utilizador', value=f'{member} ({member.id})', inline=False)
    cargos = [r.mention for r in member.roles if r.name != '@everyone']
    embed.add_field(name='Cargos', value=' '.join(cargos) if cargos else 'Nenhum', inline=False)
    await send_to(member.guild, LEAVE_CHANNEL_ID, embed)

# Mensagem apagada
@bot.event
async def on_message_delete(message):
    if message.author.bot:
        return
    embed = discord.Embed(title='🗑️ Mensagem Apagada', color=0xe74c3c, timestamp=datetime.utcnow())
    embed.add_field(name='Autor', value=f'{message.author.mention} ({message.author})', inline=False)
    embed.add_field(name='Canal', value=message.channel.mention, inline=True)
    embed.add_field(name='Conteúdo', value=message.content[:1000] if message.content else '*sem texto*', inline=False)
    await send_to(message.guild, LOG_CHANNEL_ID, embed)

# Mensagem editada
@bot.event
async def on_message_edit(before, after):
    if before.author.bot or before.content == after.content:
        return
    embed = discord.Embed(title='✏️ Mensagem Editada', color=0xf39c12, timestamp=datetime.utcnow())
    embed.add_field(name='Autor', value=f'{before.author.mention} ({before.author})', inline=False)
    embed.add_field(name='Canal', value=before.channel.mention, inline=True)
    embed.add_field(name='Antes', value=before.content[:500] if before.content else '*vazio*', inline=False)
    embed.add_field(name='Depois', value=after.content[:500] if after.content else '*vazio*', inline=False)
    await send_to(before.guild, LOG_CHANNEL_ID, embed)

# Canal criado
@bot.event
async def on_guild_channel_create(channel):
    embed = discord.Embed(title='📢 Canal Criado', color=0x2ecc71, timestamp=datetime.utcnow())
    embed.add_field(name='Nome', value=channel.name, inline=True)
    embed.add_field(name='Tipo', value=str(channel.type), inline=True)
    await send_to(channel.guild, LOG_CHANNEL_ID, embed)

# Canal apagado
@bot.event
async def on_guild_channel_delete(channel):
    embed = discord.Embed(title='🗑️ Canal Apagado', color=0xe74c3c, timestamp=datetime.utcnow())
    embed.add_field(name='Nome', value=channel.name, inline=True)
    await send_to(channel.guild, LOG_CHANNEL_ID, embed)

# Cargo criado
@bot.event
async def on_guild_role_create(role):
    embed = discord.Embed(title='🏷️ Cargo Criado', color=role.color, timestamp=datetime.utcnow())
    embed.add_field(name='Nome', value=role.name, inline=True)
    await send_to(role.guild, LOG_CHANNEL_ID, embed)

# Cargo apagado
@bot.event
async def on_guild_role_delete(role):
    embed = discord.Embed(title='🗑️ Cargo Apagado', color=0xe74c3c, timestamp=datetime.utcnow())
    embed.add_field(name='Nome', value=role.name, inline=True)
    await send_to(role.guild, LOG_CHANNEL_ID, embed)

# Membro atualizado (nickname/cargos)
@bot.event
async def on_member_update(before, after):
    if before.nick != after.nick:
        embed = discord.Embed(title='📝 Nickname Alterado', color=0x3498db, timestamp=datetime.utcnow())
        embed.add_field(name='Utilizador', value=after.mention, inline=False)
        embed.add_field(name='Antes', value=before.nick or before.name, inline=True)
        embed.add_field(name='Depois', value=after.nick or after.name, inline=True)
        await send_to(after.guild, LOG_CHANNEL_ID, embed)

    if before.roles != after.roles:
        added = [r.mention for r in after.roles if r not in before.roles]
        removed = [r.mention for r in before.roles if r not in after.roles]
        if added or removed:
            embed = discord.Embed(title='🔄 Cargos Atualizados', color=0x9b59b6, timestamp=datetime.utcnow())
            embed.add_field(name='Utilizador', value=after.mention, inline=False)
            if added:
                embed.add_field(name='Adicionados', value=' '.join(added), inline=True)
            if removed:
                embed.add_field(name='Removidos', value=' '.join(removed), inline=True)
            await send_to(after.guild, LOG_CHANNEL_ID, embed)

# Voz
@bot.event
async def on_voice_state_update(member, before, after):
    if before.channel == after.channel:
        return
    if after.channel and not before.channel:
        embed = discord.Embed(title='🎙️ Entrou no Canal de Voz', color=0x2ecc71, timestamp=datetime.utcnow())
        embed.add_field(name='Utilizador', value=member.mention, inline=True)
        embed.add_field(name='Canal', value=after.channel.name, inline=True)
        await send_to(member.guild, LOG_CHANNEL_ID, embed)
    elif before.channel and not after.channel:
        embed = discord.Embed(title='🔇 Saiu do Canal de Voz', color=0xe74c3c, timestamp=datetime.utcnow())
        embed.add_field(name='Utilizador', value=member.mention, inline=True)
        embed.add_field(name='Canal', value=before.channel.name, inline=True)
        await send_to(member.guild, LOG_CHANNEL_ID, embed)
    elif before.channel and after.channel:
        embed = discord.Embed(title='🔀 Mudou de Canal de Voz', color=0xf39c12, timestamp=datetime.utcnow())
        embed.add_field(name='Utilizador', value=member.mention, inline=True)
        embed.add_field(name='Antes', value=before.channel.name, inline=True)
        embed.add_field(name='Depois', value=after.channel.name, inline=True)
        await send_to(member.guild, LOG_CHANNEL_ID, embed)

bot.run(DISCORD_TOKEN)
