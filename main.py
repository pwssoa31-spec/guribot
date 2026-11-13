import os
import discord
from discord import app_commands
from discord.ext import commands

# ==========================================================
#  BOT DE ORGANIZAÇÃO DE SERVIDOR (slash commands)
#  pip install -U discord.py
#  Defina o token: export DISCORD_TOKEN="seu_token"
# ==========================================================

TOKEN = os.getenv("DISCORD_TOKEN", "Dd4")

intents = discord.Intents.default()
intents.members = True  # ative "Server Members Intent" no Developer Portal

bot = commands.Bot(command_prefix="!", intents=intents)


# ---------------------- Utilidades ------------------------
class Confirmar(discord.ui.View):
    """Botões de confirmação para ações destrutivas."""

    def __init__(self, autor: discord.User):
        super().__init__(timeout=30)
        self.autor = autor
        self.resultado = None

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.autor.id:
            await interaction.response.send_message("Só quem usou o comando pode confirmar.", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="Confirmar", style=discord.ButtonStyle.danger)
    async def sim(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.resultado = True
        await interaction.response.defer()
        self.stop()

    @discord.ui.button(label="Cancelar", style=discord.ButtonStyle.secondary)
    async def nao(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.resultado = False
        await interaction.response.defer()
        self.stop()


async def pedir_confirmacao(interaction: discord.Interaction, texto: str) -> bool:
    view = Confirmar(interaction.user)
    await interaction.response.send_message(texto, view=view, ephemeral=True)
    await view.wait()
    if view.resultado:
        return True
    await interaction.edit_original_response(content="❌ Cancelado.", view=None)
    return False


def hierarquia_ok(interaction: discord.Interaction, alvo: discord.Member) -> bool:
    """Impede agir em quem tem cargo igual/maior que o do autor."""
    if interaction.user.id == interaction.guild.owner_id:
        return True
    return interaction.user.top_role > alvo.top_role


@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f"✅ Online como {bot.user} | comandos sincronizados")


@bot.tree.error
async def on_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    if isinstance(error, app_commands.MissingPermissions):
        msg = "❌ Você não tem permissão para isso."
    elif isinstance(error, app_commands.BotMissingPermissions):
        msg = "❌ Eu não tenho permissão para isso. Ajuste meu cargo/permissões."
    else:
        msg = f"⚠️ Erro: {error}"
    if interaction.response.is_done():
        await interaction.followup.send(msg, ephemeral=True)
    else:
        await interaction.response.send_message(msg, ephemeral=True)


# ======================== CANAIS ==========================
TIPOS = [
    app_commands.Choice(name="Texto", value="texto"),
    app_commands.Choice(name="Voz", value="voz"),
]


@bot.tree.command(name="criar_canal", description="Cria um canal")
@app_commands.describe(nome="Nome do canal", tipo="Texto ou voz", categoria="Categoria (opcional)")
@app_commands.choices(tipo=TIPOS)
@app_commands.checks.has_permissions(manage_channels=True)
@app_commands.checks.bot_has_permissions(manage_channels=True)
@app_commands.guild_only()
async def canal_criar(interaction: discord.Interaction, nome: str, tipo: app_commands.Choice[str],
                      categoria: discord.CategoryChannel = None):
    if tipo.value == "texto":
        canal = await interaction.guild.create_text_channel(nome, category=categoria)
    else:
        canal = await interaction.guild.create_voice_channel(nome, category=categoria)
    await interaction.response.send_message(f"✅ Canal {canal.mention} criado.")


@bot.tree.command(name="apagar_canal", description="Apaga um canal (pede confirmação)")
@app_commands.describe(canal="Canal que será apagado")
@app_commands.checks.has_permissions(manage_channels=True)
@app_commands.checks.bot_has_permissions(manage_channels=True)
@app_commands.guild_only()
async def canal_apagar(interaction: discord.Interaction, canal: discord.abc.GuildChannel):
    if not await pedir_confirmacao(interaction, f"⚠️ Apagar **{canal.name}**? Isso não tem volta."):
        return
    nome = canal.name
    await canal.delete(reason=f"Apagado por {interaction.user}")
    await interaction.edit_original_response(content=f"🗑️ Canal **{nome}** apagado.", view=None)


@bot.tree.command(name="renomear_canal", description="Renomeia um canal")
@app_commands.checks.has_permissions(manage_channels=True)
@app_commands.checks.bot_has_permissions(manage_channels=True)
@app_commands.guild_only()
async def canal_renomear(interaction: discord.Interaction, canal: discord.abc.GuildChannel, novo_nome: str):
    await canal.edit(name=novo_nome)
    await interaction.response.send_message(f"✏️ Canal renomeado para **{novo_nome}**.")


@bot.tree.command(name="criar_categoria", description="Cria uma categoria")
@app_commands.checks.has_permissions(manage_channels=True)
@app_commands.checks.bot_has_permissions(manage_channels=True)
@app_commands.guild_only()
async def categoria_criar(interaction: discord.Interaction, nome: str):
    cat = await interaction.guild.create_category(nome)
    await interaction.response.send_message(f"📁 Categoria **{cat.name}** criada.")


@bot.tree.command(name="lock", description="Impede todos de falarem no canal")
@app_commands.checks.has_permissions(manage_channels=True)
@app_commands.checks.bot_has_permissions(manage_roles=True)
@app_commands.guild_only()
async def trancar(interaction: discord.Interaction, canal: discord.TextChannel = None):
    canal = canal or interaction.channel
    await canal.set_permissions(interaction.guild.default_role, send_messages=False)
    await interaction.response.send_message(f"🔒 {canal.mention} trancado.")


@bot.tree.command(name="unlock", description="Libera o canal para todos")
@app_commands.checks.has_permissions(manage_channels=True)
@app_commands.checks.bot_has_permissions(manage_roles=True)
@app_commands.guild_only()
async def destrancar(interaction: discord.Interaction, canal: discord.TextChannel = None):
    canal = canal or interaction.channel
    await canal.set_permissions(interaction.guild.default_role, send_messages=None)
    await interaction.response.send_message(f"🔓 {canal.mention} liberado.")


@bot.tree.command(name="slowmode", description="Define o modo lento (segundos, 0 desativa)")
@app_commands.checks.has_permissions(manage_channels=True)
@app_commands.checks.bot_has_permissions(manage_channels=True)
@app_commands.guild_only()
async def slowmode(interaction: discord.Interaction, segundos: app_commands.Range[int, 0, 21600]):
    await interaction.channel.edit(slowmode_delay=segundos)
    await interaction.response.send_message(f"🐢 Slowmode: {segundos}s")


@bot.tree.command(name="limpar", description="Apaga mensagens recentes do canal")
@app_commands.checks.has_permissions(manage_messages=True)
@app_commands.checks.bot_has_permissions(manage_messages=True)
@app_commands.guild_only()
async def limpar(interaction: discord.Interaction, quantidade: app_commands.Range[int, 1, 100]):
    await interaction.response.defer(ephemeral=True)
    apagadas = await interaction.channel.purge(limit=quantidade)
    await interaction.followup.send(f"🧹 {len(apagadas)} mensagens apagadas.", ephemeral=True)


# ======================== CARGOS ==========================
@bot.tree.command(name="criar_cargo", description="Cria um cargo")
@app_commands.describe(nome="Nome do cargo", cor="Cor em hex, ex: #ff00aa", mencionavel="Pode ser mencionado?")
@app_commands.checks.has_permissions(manage_roles=True)
@app_commands.checks.bot_has_permissions(manage_roles=True)
@app_commands.guild_only()
async def cargo_criar(interaction: discord.Interaction, nome: str, cor: str = "#99aab5", mencionavel: bool = False):
    try:
        cor_obj = discord.Colour.from_str(cor)
    except ValueError:
        return await interaction.response.send_message("❌ Cor inválida. Use algo como #ff00aa", ephemeral=True)
    cargo = await interaction.guild.create_role(name=nome, colour=cor_obj, mentionable=mencionavel)
    await interaction.response.send_message(f"🎭 Cargo {cargo.mention} criado.")


@bot.tree.command(name="apagar_cargo", description="Apaga um cargo (pede confirmação)")
@app_commands.checks.has_permissions(manage_roles=True)
@app_commands.checks.bot_has_permissions(manage_roles=True)
@app_commands.guild_only()
async def cargo_apagar(interaction: discord.Interaction, cargo: discord.Role):
    if cargo >= interaction.guild.me.top_role or cargo.is_default():
        return await interaction.response.send_message("❌ Não posso apagar esse cargo.", ephemeral=True)
    if not await pedir_confirmacao(interaction, f"⚠️ Apagar o cargo **{cargo.name}**?"):
        return
    nome = cargo.name
    await cargo.delete(reason=f"Apagado por {interaction.user}")
    await interaction.edit_original_response(content=f"🗑️ Cargo **{nome}** apagado.", view=None)


@bot.tree.command(name="add_cargo", description="Dá um cargo a um membro")
@app_commands.checks.has_permissions(manage_roles=True)
@app_commands.checks.bot_has_permissions(manage_roles=True)
@app_commands.guild_only()
async def cargo_dar(interaction: discord.Interaction, membro: discord.Member, cargo: discord.Role):
    if cargo >= interaction.guild.me.top_role or (cargo >= interaction.user.top_role
                                                  and interaction.user.id != interaction.guild.owner_id):
        return await interaction.response.send_message("❌ Esse cargo está acima do seu/meu nível.", ephemeral=True)
    await membro.add_roles(cargo)
    await interaction.response.send_message(f"✅ {cargo.mention} dado a {membro.mention}.",
                                            allowed_mentions=discord.AllowedMentions.none())


@bot.tree.command(name="rm_cargo", description="Remove um cargo de um membro")
@app_commands.checks.has_permissions(manage_roles=True)
@app_commands.checks.bot_has_permissions(manage_roles=True)
@app_commands.guild_only()
async def cargo_tirar(interaction: discord.Interaction, membro: discord.Member, cargo: discord.Role):
    if cargo >= interaction.guild.me.top_role or (cargo >= interaction.user.top_role
                                                  and interaction.user.id != interaction.guild.owner_id):
        return await interaction.response.send_message("❌ Esse cargo está acima do seu/meu nível.", ephemeral=True)
    await membro.remove_roles(cargo)
    await interaction.response.send_message(f"✅ {cargo.mention} removido de {membro.mention}.",
                                            allowed_mentions=discord.AllowedMentions.none())


# ======================== MEMBROS =========================
@bot.tree.command(name="apelido", description="Muda o apelido de um membro (vazio = resetar)")
@app_commands.checks.has_permissions(manage_nicknames=True)
@app_commands.checks.bot_has_permissions(manage_nicknames=True)
@app_commands.guild_only()
async def apelido(interaction: discord.Interaction, membro: discord.Member, novo_apelido: str = None):
    if not hierarquia_ok(interaction, membro):
        return await interaction.response.send_message("❌ Cargo dele é igual/maior que o seu.", ephemeral=True)
    await membro.edit(nick=novo_apelido)
    await interaction.response.send_message(f"✏️ Apelido de {membro.mention} atualizado.",
                                            allowed_mentions=discord.AllowedMentions.none())


@bot.tree.command(name="ban", description="Expulsa um membro")
@app_commands.checks.has_permissions(kick_members=True)
@app_commands.checks.bot_has_permissions(kick_members=True)
@app_commands.guild_only()
async def expulsar(interaction: discord.Interaction, membro: discord.Member, motivo: str = "Sem motivo"):
    if not hierarquia_ok(interaction, membro):
        return await interaction.response.send_message("❌ Cargo dele é igual/maior que o seu.", ephemeral=True)
    await membro.kick(reason=f"{interaction.user}: {motivo}")
    await interaction.response.send_message(f"👢 {membro} expulso. Motivo: {motivo}")


@bot.tree.command(name="banir", description="Bane um membro")
@app_commands.checks.has_permissions(ban_members=True)
@app_commands.checks.bot_has_permissions(ban_members=True)
@app_commands.guild_only()
async def banir(interaction: discord.Interaction, membro: discord.Member, motivo: str = "Sem motivo"):
    if not hierarquia_ok(interaction, membro):
        return await interaction.response.send_message("❌ Cargo dele é igual/maior que o seu.", ephemeral=True)
    await membro.ban(reason=f"{interaction.user}: {motivo}")
    await interaction.response.send_message(f"🔨 {membro} banido. Motivo: {motivo}")


@bot.tree.command(name="unban", description="Desbane pelo ID do usuário")
@app_commands.checks.has_permissions(ban_members=True)
@app_commands.checks.bot_has_permissions(ban_members=True)
@app_commands.guild_only()
async def desbanir(interaction: discord.Interaction, user_id: str):
    try:
        await interaction.guild.unban(discord.Object(id=int(user_id)))
    except (ValueError, discord.NotFound):
        return await interaction.response.send_message("❌ ID inválido ou usuário não está banido.", ephemeral=True)
    await interaction.response.send_message(f"✅ <@{user_id}> desbanido.")


@bot.tree.command(name="mute", description="Silencia um membro (timeout) por X minutos")
@app_commands.checks.has_permissions(moderate_members=True)
@app_commands.checks.bot_has_permissions(moderate_members=True)
@app_commands.guild_only()
async def mutar(interaction: discord.Interaction, membro: discord.Member,
                minutos: app_commands.Range[int, 1, 40320], motivo: str = "Sem motivo"):
    if not hierarquia_ok(interaction, membro):
        return await interaction.response.send_message("❌ Cargo dele é igual/maior que o seu.", ephemeral=True)
    from datetime import timedelta
    await membro.timeout(timedelta(minutes=minutos), reason=f"{interaction.user}: {motivo}")
    await interaction.response.send_message(f"🔇 {membro.mention} mutado por {minutos} min.",
                                            allowed_mentions=discord.AllowedMentions.none())


@bot.tree.command(name="desmutar", description="Remove o timeout de um membro")
@app_commands.checks.has_permissions(moderate_members=True)
@app_commands.checks.bot_has_permissions(moderate_members=True)
@app_commands.guild_only()
async def desmutar(interaction: discord.Interaction, membro: discord.Member):
    await membro.timeout(None)
    await interaction.response.send_message(f"🔊 {membro.mention} desmutado.",
                                            allowed_mentions=discord.AllowedMentions.none())


# ======================== INFO ============================
@bot.tree.command(name="servidor", description="Informações do servidor")
@app_commands.guild_only()
async def servidor(interaction: discord.Interaction):
    g = interaction.guild
    emb = discord.Embed(title=g.name, color=discord.Color.blurple())
    emb.add_field(name="Membros", value=g.member_count)
    emb.add_field(name="Canais", value=len(g.channels))
    emb.add_field(name="Cargos", value=len(g.roles))
    emb.add_field(name="Dono", value=f"<@{g.owner_id}>")
    if g.icon:
        emb.set_thumbnail(url=g.icon.url)
    await interaction.response.send_message(embed=emb)


# ----------------------------------------------------------
# 👇 Adicione novos comandos aqui embaixo
# ----------------------------------------------------------

if __name__ == "__main__":
    bot.run(TOKEN)
