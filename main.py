import discord
import os
from discord.ext import commands
from discord import app_commands

intents = discord.Intents.default()
intents.guilds = True
intents.voice_states = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

# Тут будемо зберігати ID каналів (налаштувань і створення)
guild_config = {}

# Словник власників каналів
channel_owners = {}


# ====== VIEW з кнопками ======
class ChannelSettingsView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)  # persistent view

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        """Перевірка – чи користувач власник каналу, в якому він знаходиться"""
        voice = interaction.user.voice
        if not voice or not voice.channel:
            await interaction.response.send_message("❌ Ви повинні бути у вашому голосовому каналі!", ephemeral=True)
            return False

        owner_id = channel_owners.get(voice.channel.id)
        if owner_id != interaction.user.id:
            await interaction.response.send_message("❌ Ви не є власником цього каналу!", ephemeral=True)
            return False

        return True

    # 🔴 Закрити канал
    @discord.ui.button(label="Закрити", style=discord.ButtonStyle.danger, custom_id="lock_btn")
    async def lock(self, interaction: discord.Interaction, button: discord.ui.Button):
        channel = interaction.user.voice.channel
        await channel.set_permissions(interaction.guild.default_role, connect=False, view_channel=True)
        await interaction.response.send_message("🔒 Канал закрито!", ephemeral=True)

    # 🟢 Відкрити канал
    @discord.ui.button(label="Відкрити", style=discord.ButtonStyle.success, custom_id="unlock_btn")
    async def unlock(self, interaction: discord.Interaction, button: discord.ui.Button):
        channel = interaction.user.voice.channel
        await channel.set_permissions(interaction.guild.default_role, connect=True, view_channel=True)
        await interaction.response.send_message("🔓 Канал відкрито!", ephemeral=True)

    # 👁 Приховати
    @discord.ui.button(label="Приховати", style=discord.ButtonStyle.secondary, custom_id="hide_btn")
    async def hide(self, interaction: discord.Interaction, button: discord.ui.Button):
        channel = interaction.user.voice.channel
        await channel.set_permissions(interaction.guild.default_role, view_channel=False)
        await interaction.response.send_message("🙈 Канал приховано!", ephemeral=True)

    # 👁‍🗨 Показати
    @discord.ui.button(label="Показати", style=discord.ButtonStyle.secondary, custom_id="unhide_btn")
    async def unhide(self, interaction: discord.Interaction, button: discord.ui.Button):
        channel = interaction.user.voice.channel
        await channel.set_permissions(interaction.guild.default_role, view_channel=True)
        await interaction.response.send_message("👀 Канал показано!", ephemeral=True)

    # ✏ Перейменувати
    @discord.ui.button(label="Перейменувати", style=discord.ButtonStyle.primary, custom_id="rename_btn")
    async def rename(self, interaction: discord.Interaction, button: discord.ui.Button):
        modal = RenameModal()
        await interaction.response.send_modal(modal)


# ====== MODAL для перейменування ======
class RenameModal(discord.ui.Modal, title="Перейменування каналу"):
    new_name = discord.ui.TextInput(label="Нова назва", placeholder="Введіть назву")

    async def on_submit(self, interaction: discord.Interaction):
        voice = interaction.user.voice
        if not voice or not voice.channel:
            await interaction.response.send_message("❌ Ви повинні бути у вашому голосовому каналі!", ephemeral=True)
            return

        owner_id = channel_owners.get(voice.channel.id)
        if owner_id != interaction.user.id:
            await interaction.response.send_message("❌ Ви не є власником цього каналу!", ephemeral=True)
            return

        await voice.channel.edit(name=f"{self.new_name.value}")
        await interaction.response.send_message(f"✏ Назву каналу змінено на **{self.new_name.value}**", ephemeral=True)


# ====== Slash-команда SETUP ======
@bot.tree.command(name="setup", description="Налаштувати канали для створення і керування")
@app_commands.checks.has_permissions(administrator=True)
async def setup(interaction: discord.Interaction,
                settings_channel: discord.TextChannel,
                create_channel: discord.VoiceChannel):

    guild_config[interaction.guild.id] = {
        "settings_channel": settings_channel.id,
        "create_channel": create_channel.id
    }

    # Embed
    embed = discord.Embed(
        title="📢 Тимчасові канали",
        description=(
            "Ви можете налаштувати свій тимчасовий канал за допомогою кнопок нижче "
            "або за допомогою команд (виконуються у будь-якому доступному каналі):\n\n"
            "— **Доступність каналу**\n"
            "   🔒 Закрити канал\n"
            "   🔓 Відкрити канал\n\n"
            "— **Видимість каналу**\n"
            "   👁️‍🗨️ Приховати канал\n"
            "   👁️ Показати канал\n\n"
            "— **Назва каналу**\n"
            "   ✏️ Перейменувати канал (якщо не вказати назву — буде стандартна назва).\n\n"
            "ℹ️ Ви можете налаштувати все за допомогою кнопок нижче."
        ),
        color=discord.Color.blue()
    )

    await settings_channel.send(embed=embed, view=ChannelSettingsView())
    await interaction.response.send_message("✅ Налаштування завершено!", ephemeral=True)


# ====== Авто-створення каналів ======
@bot.event
async def on_voice_state_update(member, before, after):
    if not member.guild.id in guild_config:
        return

    config = guild_config[member.guild.id]
    create_channel_id = config["create_channel"]

    # Якщо користувач зайшов у "створити-гс"
    if after.channel and after.channel.id == create_channel_id:
        category = after.channel.category
        new_channel = await member.guild.create_voice_channel(
            name=f"Канал - {member.display_name}",
            category=category
        )

        # Переносимо користувача
        await member.move_to(new_channel)

        # Запам'ятовуємо власника
        channel_owners[new_channel.id] = member.id

    # Якщо вийшов і канал спорожнів
    if before.channel and before.channel.id in channel_owners:
        if len(before.channel.members) == 0:
            await before.channel.delete()
            del channel_owners[before.channel.id]


# ====== Старт ======
@bot.event
async def on_ready():
    bot.add_view(ChannelSettingsView())  # робимо кнопки persistent
    await bot.tree.sync()
    print(f"✅ Бот запущений як {bot.user}")



bot.run(os.getenv("TOKEN"))
