from __future__ import annotations

import logging
import os
from datetime import datetime, timezone
from pathlib import Path

import discord
from discord import app_commands
from discord.ext import commands
from dotenv import load_dotenv

from config_store import get_guild_config, set_guild_channel

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("HEe.Gatekeeper")

BASE_DIR = Path(__file__).parent
ASSETS_DIR = BASE_DIR / "assets"
WELCOME_GIF = ASSETS_DIR / "welcome.gif"
GOODBYE_GIF = ASSETS_DIR / "goodbye.gif"

COLOR_HEE_RED = 0xE11D48
COLOR_HEE_DARK_RED = 0x881337


def _env_int(name: str) -> int | None:
    val = os.getenv(name, "").strip()
    return int(val) if val.isdigit() else None


DEFAULT_GUILD_ID = _env_int("GUILD_ID")
DEFAULT_WELCOME_ID = _env_int("WELCOME_CHANNEL_ID")
DEFAULT_GOODBYE_ID = _env_int("GOODBYE_CHANNEL_ID")


def _resolve_channel(guild: discord.Guild, key: str, env_fallback: int | None) -> discord.TextChannel | None:
    cfg = get_guild_config(guild.id)
    channel_id = cfg.get(key) or env_fallback
    if not channel_id:
        return None
    try:
        parsed_id = int(channel_id)
    except (TypeError, ValueError):
        return None
    channel = guild.get_channel(parsed_id)
    return channel if isinstance(channel, discord.TextChannel) else None


def _build_welcome_embed(member: discord.Member | discord.User, guild: discord.Guild) -> discord.Embed:
    embed = discord.Embed(
        title="WELCOME TO HIGH EGO ESPORT",
        description=(
            f"Chào mừng {member.mention} đã gia nhập **{guild.name}**!\n"
            "Hãy đọc luật server, chọn role game của bạn và sẵn sàng thể hiện bản lĩnh."
        ),
        color=COLOR_HEE_RED,
        timestamp=datetime.now(timezone.utc),
    )
    embed.set_author(name="HEe • High Ego eSport", icon_url=guild.icon.url if guild.icon else None)
    embed.set_thumbnail(url=member.display_avatar.url)
    embed.add_field(name="Thành viên thứ", value=f"**#{guild.member_count}**", inline=True)
    embed.add_field(name="Tài khoản tạo lúc", value=discord.utils.format_dt(member.created_at, style="R"), inline=True)
    embed.set_footer(text="High Ego eSport • Prove Your Ego")
    if WELCOME_GIF.exists():
        embed.set_image(url="attachment://welcome.gif")
    return embed


def _build_goodbye_embed(member: discord.Member | discord.User, guild: discord.Guild) -> discord.Embed:
    embed = discord.Embed(
        title="GOODBYE • HIGH EGO ESPORT",
        description=f"**{member.display_name}** (`@{member.name}`) đã rời khỏi **{guild.name}**.\nChúc bạn may mắn trên chặng đường tiếp theo — GGWP!",
        color=COLOR_HEE_DARK_RED,
        timestamp=datetime.now(timezone.utc),
    )
    embed.set_author(name="HEe • High Ego eSport", icon_url=guild.icon.url if guild.icon else None)
    embed.set_thumbnail(url=member.display_avatar.url)
    embed.add_field(name="Thành viên còn lại", value=f"**{guild.member_count}**", inline=True)
    embed.set_footer(text="High Ego eSport • GGWP")
    if GOODBYE_GIF.exists():
        embed.set_image(url="attachment://goodbye.gif")
    return embed


async def _send_banner(
    channel: discord.TextChannel,
    embed: discord.Embed,
    gif_path: Path,
    filename: str,
) -> None:
    if gif_path.exists():
        file = discord.File(gif_path, filename=filename)
        await channel.send(embed=embed, file=file)
    else:
        logger.warning("Banner GIF not found at %s; sending embed only.", gif_path)
        await channel.send(embed=embed)


class GatekeeperBot(commands.Bot):
    def __init__(self) -> None:
        intents = discord.Intents.default()
        intents.members = True
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self) -> None:
        if DEFAULT_GUILD_ID:
            guild_obj = discord.Object(id=DEFAULT_GUILD_ID)
            self.tree.copy_global_to(guild=guild_obj)
            synced = await self.tree.sync(guild=guild_obj)
            logger.info("Synced %d slash command(s) to guild %s.", len(synced), DEFAULT_GUILD_ID)
        else:
            synced = await self.tree.sync()
            logger.info("Synced %d global slash command(s).", len(synced))

    async def on_ready(self) -> None:
        logger.info("Logged in as %s (ID: %s)", self.user, self.user.id if self.user else "?")
        await self.change_presence(
            activity=discord.Activity(type=discord.ActivityType.watching, name="High Ego eSport • HEe")
        )


bot = GatekeeperBot()


@bot.event
async def on_member_join(member: discord.Member) -> None:
    channel = _resolve_channel(member.guild, "welcome_channel_id", DEFAULT_WELCOME_ID)
    if not channel:
        return
    embed = _build_welcome_embed(member, member.guild)
    await _send_banner(channel, embed, WELCOME_GIF, "welcome.gif")


@bot.event
async def on_member_remove(member: discord.Member) -> None:
    channel = _resolve_channel(member.guild, "goodbye_channel_id", DEFAULT_GOODBYE_ID)
    if not channel:
        return
    embed = _build_goodbye_embed(member, member.guild)
    await _send_banner(channel, embed, GOODBYE_GIF, "goodbye.gif")


@bot.tree.command(name="build", description="Tự động tạo kênh/category mới và gắn chức năng cho server HEe")
@app_commands.default_permissions(manage_channels=True)
@app_commands.describe(
    loai="Loại kênh muốn tạo (Text, Voice, hoặc Category)",
    ten="Tên kênh hoặc Category",
    chuc_nang="Chức năng tự động gắn vào kênh vừa tạo",
    category="Đặt kênh vào bên trong Category nào (tùy chọn)",
    gioi_han_nguoi="Giới hạn số người tối đa cho kênh Voice (0 = không giới hạn)",
)
@app_commands.choices(
    loai=[
        app_commands.Choice(name="Text Channel", value="text"),
        app_commands.Choice(name="Voice Channel", value="voice"),
        app_commands.Choice(name="Category", value="category"),
    ],
    chuc_nang=[
        app_commands.Choice(name="Kênh bình thường", value="normal"),
        app_commands.Choice(name="Kênh Welcome (gửi banner chào mừng)", value="welcome"),
        app_commands.Choice(name="Kênh Goodbye (gửi banner tạm biệt)", value="goodbye"),
        app_commands.Choice(name="Room Ngủ (Voice AFK)", value="sleep_voice"),
    ],
)
async def build_channel(
    interaction: discord.Interaction,
    loai: app_commands.Choice[str],
    ten: str,
    chuc_nang: app_commands.Choice[str] | None = None,
    category: discord.CategoryChannel | None = None,
    gioi_han_nguoi: app_commands.Range[int, 0, 99] = 0,
) -> None:
    if not interaction.guild:
        await interaction.response.send_message("Lệnh này chỉ dùng được trong server.", ephemeral=True)
        return

    clean_name = ten.strip()
    if not clean_name:
        await interaction.response.send_message("Tên kênh hoặc Category không được để trống.", ephemeral=True)
        return

    func_value = chuc_nang.value if chuc_nang else "normal"
    if func_value in {"welcome", "goodbye"} and loai.value != "text":
        await interaction.response.send_message(
            "Chức năng Welcome/Goodbye chỉ áp dụng được cho **Text Channel**.",
            ephemeral=True,
        )
        return
    if func_value == "sleep_voice" and loai.value != "voice":
        await interaction.response.send_message(
            "Chức năng **Room Ngủ (Voice AFK)** chỉ áp dụng được cho **Voice Channel**.",
            ephemeral=True,
        )
        return

    await interaction.response.defer(ephemeral=True)
    guild = interaction.guild

    try:
        if loai.value == "category":
            created = await guild.create_category(name=clean_name)
        elif loai.value == "voice":
            created = await guild.create_voice_channel(
                name=clean_name,
                category=category,
                user_limit=gioi_han_nguoi,
            )
        else:
            created = await guild.create_text_channel(
                name=clean_name,
                category=category,
            )
            if func_value == "welcome":
                set_guild_channel(guild.id, "welcome_channel_id", created.id)
            elif func_value == "goodbye":
                set_guild_channel(guild.id, "goodbye_channel_id", created.id)
    except discord.Forbidden:
        await interaction.followup.send(
            "Bot chưa có quyền **Manage Channels** để tạo kênh. Hãy kiểm tra lại quyền của bot.",
            ephemeral=True,
        )
        return
    except discord.HTTPException as exc:
        await interaction.followup.send(
            f"Không thể tạo kênh do Discord từ chối yêu cầu: `{exc.text}`",
            ephemeral=True,
        )
        return

    extra_note = ""
    if func_value == "welcome":
        extra_note = "\nĐã tự động gắn làm **Kênh Welcome** (gửi banner chào mừng)."
    elif func_value == "goodbye":
        extra_note = "\nĐã tự động gắn làm **Kênh Goodbye** (gửi banner tạm biệt)."
    elif func_value == "sleep_voice" and loai.value == "voice":
        extra_note = f"\nID Room Ngủ để dán vào bot Voice AFK: `{created.id}`"

    await interaction.followup.send(
        f"Đã tạo thành công {created.mention} (`{created.id}`).{extra_note}",
        ephemeral=True,
    )


@bot.tree.command(name="set-banner-channel", description="Chọn kênh có sẵn làm kênh Welcome hoặc Goodbye")
@app_commands.default_permissions(manage_channels=True)
@app_commands.describe(loai="Chọn loại banner", kenh="Kênh Text muốn gửi banner vào")
@app_commands.choices(
    loai=[
        app_commands.Choice(name="Welcome", value="welcome"),
        app_commands.Choice(name="Goodbye", value="goodbye"),
    ]
)
async def set_banner_channel(
    interaction: discord.Interaction,
    loai: app_commands.Choice[str],
    kenh: discord.TextChannel,
) -> None:
    if not interaction.guild:
        await interaction.response.send_message("Lệnh này chỉ dùng được trong server.", ephemeral=True)
        return

    key = "welcome_channel_id" if loai.value == "welcome" else "goodbye_channel_id"
    set_guild_channel(interaction.guild.id, key, kenh.id)
    await interaction.response.send_message(
        f"Đã cập nhật kênh **{loai.name}** thành {kenh.mention}.",
        ephemeral=True,
    )


@bot.tree.command(name="test-banner", description="Gửi thử banner Welcome hoặc Goodbye để kiểm tra")
@app_commands.default_permissions(manage_channels=True)
@app_commands.describe(loai="Chọn loại banner muốn test")
@app_commands.choices(
    loai=[
        app_commands.Choice(name="Welcome", value="welcome"),
        app_commands.Choice(name="Goodbye", value="goodbye"),
    ]
)
async def test_banner(
    interaction: discord.Interaction,
    loai: app_commands.Choice[str],
) -> None:
    if not interaction.guild or not isinstance(interaction.channel, discord.TextChannel):
        await interaction.response.send_message("Hãy chạy lệnh này trong một Text Channel của server.", ephemeral=True)
        return

    await interaction.response.defer(ephemeral=True)
    try:
        if loai.value == "welcome":
            embed = _build_welcome_embed(interaction.user, interaction.guild)
            await _send_banner(interaction.channel, embed, WELCOME_GIF, "welcome.gif")
        else:
            embed = _build_goodbye_embed(interaction.user, interaction.guild)
            await _send_banner(interaction.channel, embed, GOODBYE_GIF, "goodbye.gif")
    except discord.Forbidden:
        await interaction.followup.send(
            "Bot thiếu quyền gửi tin nhắn, nhúng liên kết hoặc đính kèm tệp trong kênh này.",
            ephemeral=True,
        )
        return

    await interaction.followup.send(f"Đã gửi thử banner **{loai.name}**!", ephemeral=True)


@bot.tree.error
async def on_app_command_error(interaction: discord.Interaction, error: app_commands.AppCommandError) -> None:
    logger.exception("Slash command error: %s", error)
    message = "Có lỗi xảy ra khi thực hiện lệnh. Vui lòng thử lại hoặc kiểm tra quyền của bot."
    if isinstance(error, app_commands.MissingPermissions):
        message = "Bạn cần quyền **Manage Channels** để sử dụng lệnh này."
    if interaction.response.is_done():
        await interaction.followup.send(message, ephemeral=True)
    else:
        await interaction.response.send_message(message, ephemeral=True)


def main() -> None:
    token = os.getenv("DISCORD_TOKEN", "").strip()
    if not token or token == "YOUR_DISCORD_BOT_TOKEN_HERE":
        raise RuntimeError("Vui lòng cấu hình DISCORD_TOKEN hợp lệ trong file .env")
    bot.run(token)


if __name__ == "__main__":
    main()
