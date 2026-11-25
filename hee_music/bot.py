"""
bot.py — HEe • Beat (Music Bot độc quyền cho Role HE với YouTube stream)
- Hỗ trợ Prefix: he!p <link_ytb>, he!skip, he!pause, he!resume, he!stop, he!queue, he!repeat, he!leave, he!i
- Hỗ trợ Slash: /play, /he-play, /skip, /pause, /resume, /stop, /queue, /repeat, /leave, /info, /guide
- Phân quyền: Độc quyền Role HE / Founder / Admin
- Khóa phòng voice độc quyền: Đang phát tại phòng nào thì phòng khác KHÔNG ĐƯỢC PHÉP gọi bot hay can thiệp
- Auto-leave: Tự động rời phòng và dọn dẹp sau 1 phút nếu phòng không còn ai
"""

import os
import re
import sys
import asyncio
import logging
from datetime import datetime, timezone
from typing import Optional, List, Dict
from collections import deque

import discord
from discord import app_commands
from discord.ext import commands
from dotenv import load_dotenv
import yt_dlp

load_dotenv()

try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')
except AttributeError:
    pass

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger('HEe.Beat')

BOT_TOKEN        = os.getenv('BOT_TOKEN', '')
GUILD_ID         = int(os.getenv('GUILD_ID', '0'))
HE_ROLE_NAME     = os.getenv('HE_ROLE_NAME', 'HE')
OWNER_USER_ID    = os.getenv('OWNER_USER_ID', '1147375213634388008')

COLOR_RED  = 0xE11D48
COLOR_DARK = 0x881337

YOUTUBE_URL_REGEX = re.compile(
    r'^(https?://)?(www\.|m\.)?(youtube\.com/watch\?v=|youtu\.be/|youtube\.com/shorts/)[a-zA-Z0-9_-]+'
)

YTDL_OPTIONS = {
    'format': 'bestaudio/best',
    'noplaylist': True,
    'nocheckcertificate': True,
    'ignoreerrors': False,
    'logtostderr': False,
    'quiet': True,
    'no_warnings': True,
    'default_search': 'auto',
    'source_address': '0.0.0.0',
}

FFMPEG_OPTIONS = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
    'options': '-vn'
}

ytdl = yt_dlp.YoutubeDL(YTDL_OPTIONS)

# ─────────────────── NẠP THƯ VIỆN OPUS CHO DISCORD VOICE ───────────────────
if not discord.opus.is_loaded():
    try:
        import ctypes.util
        opus_lib = ctypes.util.find_library('opus') or 'libopus.so.0'
        discord.opus.load_opus(opus_lib)
        logger.info(f"Đã nạp thành công thư viện Opus ({opus_lib}) cho âm thanh Voice.")
    except Exception as e:
        logger.warning(f"Không thể nạp tự động libopus: {e}")

async def delete_after_delay(msg, delay: int = 10):
    """Xóa tin nhắn sau một khoảng thời gian nhất định (mặc định 10s)"""
    try:
        await asyncio.sleep(delay)
        if hasattr(msg, 'delete'):
            await msg.delete()
    except Exception:
        pass

def is_authorized(member: discord.Member) -> bool:
    """Kiểm tra quyền Role HE / Founder / Admin"""
    if str(member.id) == OWNER_USER_ID or member.id == 1147375213634388008:
        return True
    if member.guild_permissions.administrator:
        return True
    return any(r.name == HE_ROLE_NAME or str(r.id) == HE_ROLE_NAME for r in member.roles)

def is_youtube_url(url: str) -> bool:
    return bool(YOUTUBE_URL_REGEX.match(url.strip()))

def format_duration(seconds: Optional[int]) -> str:
    if not seconds:
        return "Livestream"
    m, s = divmod(seconds, 60)
    h, m = divmod(m, 60)
    if h > 0:
        return f"{h:02d}:{m:02d}:{s:02d}"
    return f"{m:02d}:{s:02d}"

class Song:
    def __init__(self, title: str, webpage_url: str, stream_url: str, duration: Optional[int], thumbnail: str, requester: discord.Member):
        self.title = title
        self.webpage_url = webpage_url
        self.stream_url = stream_url
        self.duration = duration
        self.thumbnail = thumbnail
        self.requester = requester

class GuildMusicManager:
    def __init__(self, guild_id: int):
        self.guild_id = guild_id
        self.queue: deque[Song] = deque()
        self.current: Optional[Song] = None
        self.repeat: bool = False
        self.voice_client: Optional[discord.VoiceClient] = None
        self.text_channel: Optional[discord.abc.Messageable] = None
        self.afk_task: Optional[asyncio.Task] = None

    def clear(self):
        self.queue.clear()
        self.current = None
        self.repeat = False

managers: Dict[int, GuildMusicManager] = {}

def get_manager(guild_id: int) -> GuildMusicManager:
    if guild_id not in managers:
        managers[guild_id] = GuildMusicManager(guild_id)
    return managers[guild_id]

async def extract_youtube_info(url: str, requester: discord.Member) -> Optional[Song]:
    loop = asyncio.get_event_loop()
    try:
        data = await loop.run_in_executor(None, lambda: ytdl.extract_info(url, download=False))
        if 'entries' in data:
            data = data['entries'][0]

        title = data.get('title', 'Unknown Title')
        webpage_url = data.get('webpage_url', url)
        stream_url = data.get('url', '')
        duration = data.get('duration')
        thumbnail = data.get('thumbnail', '')

        return Song(
            title=title,
            webpage_url=webpage_url,
            stream_url=stream_url,
            duration=duration,
            thumbnail=thumbnail,
            requester=requester
        )
    except Exception as e:
        logger.error(f"Lỗi extract YouTube: {e}")
        return None

# ─────────────────── VOICE HELPERS ───────────────────
def check_voice_exclusivity(member: discord.Member, guild: discord.Guild) -> tuple[bool, str, Optional[discord.VoiceChannel]]:
    """
    Kiểm tra tính độc quyền phòng voice:
    - Nếu bot chưa kết nối: cho phép gọi nếu người gọi đang ở trong một voice channel.
    - Nếu bot đang kết nối: Bắt buộc người gọi phải ở CÙNG PHÒNG VOICE với bot.
      Các phòng voice khác dù là Chủ server hay Role HE cũng BỊ CHẶN TUYỆT ĐỐI.
    """
    if not member.voice or not member.voice.channel:
        return False, "❌ Bạn phải tham gia vào một kênh Voice trước khi gọi bot phát nhạc!", None

    user_channel = member.voice.channel
    vc = guild.voice_client

    if vc and vc.is_connected() and vc.channel:
        if vc.channel.id != user_channel.id:
            return False, (
                f"🔒 **PHÒNG ĐỘC QUYỀN ĐANG HOẠT ĐỘNG:**\n"
                f"Bot đang phát nhạc phục vụ riêng tại phòng **{vc.channel.name}**!\n"
                f"👉 Thành viên tại các phòng voice khác (kể cả Role HE) không được can thiệp cho đến khi phòng hiện tại rời đi."
            ), vc.channel

    return True, "", user_channel

# ─────────────────── INTERACTIVE CONTROLS VIEW ───────────────────
class MusicControlsView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if not is_authorized(interaction.user):
            await interaction.response.send_message("❌ Thao tác này chỉ dành riêng cho thành viên có **Role HE**!", ephemeral=True)
            return False
        ok, err_msg, _ = check_voice_exclusivity(interaction.user, interaction.guild)
        if not ok:
            await interaction.response.send_message(err_msg, ephemeral=True)
            return False
        return True

    @discord.ui.button(label="Tạm dừng / Tiếp tục", style=discord.ButtonStyle.secondary, emoji="⏯️", custom_id="hee_music:pause_resume")
    async def pause_resume_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        vc = interaction.guild.voice_client
        if not vc:
            await interaction.response.send_message("⚠️ Bot không có trong phòng voice.", ephemeral=True)
            return
        if vc.is_playing():
            vc.pause()
            await interaction.response.send_message(f"⏸️ {interaction.user.mention} đã tạm dừng phát nhạc.")
        elif vc.is_paused():
            vc.resume()
            await interaction.response.send_message(f"▶️ {interaction.user.mention} đã tiếp tục phát nhạc.")
        else:
            await interaction.response.send_message("⚠️ Hiện không có bài hát nào đang phát.", ephemeral=True)

    @discord.ui.button(label="Bỏ qua", style=discord.ButtonStyle.primary, emoji="⏭️", custom_id="hee_music:skip")
    async def skip_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        vc = interaction.guild.voice_client
        if vc and (vc.is_playing() or vc.is_paused()):
            vc.stop()
            await interaction.response.send_message(f"⏭️ {interaction.user.mention} đã bỏ qua bài hát hiện tại!")
        else:
            await interaction.response.send_message("⚠️ Không có bài hát nào đang phát.", ephemeral=True)

    @discord.ui.button(label="Lặp lại", style=discord.ButtonStyle.secondary, emoji="🔁", custom_id="hee_music:repeat")
    async def repeat_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        manager = get_manager(interaction.guild.id)
        manager.repeat = not manager.repeat
        status = "BẬT" if manager.repeat else "TẮT"
        await interaction.response.send_message(f"🔁 Chế độ lặp lại bài hát hiện tại: **{status}**")

    @discord.ui.button(label="Hàng đợi", style=discord.ButtonStyle.secondary, emoji="📋", custom_id="hee_music:queue")
    async def queue_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        manager = get_manager(interaction.guild.id)
        if not manager.current and not manager.queue:
            await interaction.response.send_message("📭 Hàng đợi hiện đang trống.", ephemeral=True)
            return
        lines = []
        if manager.current:
            lines.append(f"▶️ **Đang phát:** [{manager.current.title}]({manager.current.webpage_url}) (`{format_duration(manager.current.duration)}`)")
        if manager.queue:
            lines.append("\n**Danh sách kế tiếp:**")
            for i, s in enumerate(list(manager.queue)[:10], 1):
                lines.append(f"`{i}.` [{s.title}]({s.webpage_url}) (`{format_duration(s.duration)}`) | {s.requester.mention}")
            if len(manager.queue) > 10:
                lines.append(f"*... và còn {len(manager.queue) - 10} bài hát khác.*")
        embed = discord.Embed(
            title="📋 Danh Sách Nhạc Hàng Đợi",
            description="\n".join(lines),
            color=COLOR_RED
        )
        embed.set_footer(text=f"Tổng số bài: {len(manager.queue) + (1 if manager.current else 0)} • Lặp lại: {'Bật' if manager.repeat else 'Tắt'}")
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @discord.ui.button(label="Dừng & Rời", style=discord.ButtonStyle.danger, emoji="⏹️", custom_id="hee_music:stop")
    async def stop_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        manager = get_manager(interaction.guild.id)
        manager.clear()
        vc = interaction.guild.voice_client
        if vc and (vc.is_playing() or vc.is_paused()):
            vc.stop()
        if vc and vc.is_connected():
            await vc.disconnect()
            await interaction.response.send_message(f"⏹️ {interaction.user.mention} đã dừng nhạc, dọn dẹp hàng đợi và rời khỏi voice.")
        else:
            await interaction.response.send_message(f"⏹️ {interaction.user.mention} đã dọn dẹp toàn bộ hàng đợi.")

# ─────────────────── GUIDE EMBED BUILDER ───────────────────
def build_guide_embed(guild: Optional[discord.Guild] = None) -> discord.Embed:
    embed = discord.Embed(
        title="🎵 HEe • Beat — Hướng Dẫn Sử Dụng & Bảng Lệnh",
        description=(
            "**HEe • Beat** là hệ thống phát nhạc YouTube chất lượng cao độc quyền dành riêng cho thành viên mang **Role HE**, Ban Quản Trị và Founder tại **High Ego eSport**.\n\n"
            "✨ *Chỉ chấp nhận link YouTube trực tiếp (Watch, Shorts, youtu.be).*"
        ),
        color=COLOR_RED,
        timestamp=datetime.now(timezone.utc)
    )
    if guild and guild.icon:
        embed.set_author(name=f"High Ego eSport • {guild.name}", icon_url=guild.icon.url)
    else:
        embed.set_author(name="High Ego eSport • HEe Beat")

    embed.add_field(
        name="🎶 1. Lệnh Phát Nhạc (Chỉ link YouTube)",
        value=(
            "• `he!p <link_ytb>` hoặc `/play <link_ytb>`: Kết nối vào phòng voice và phát bài hát.\n"
            "• *Định dạng hỗ trợ: `youtube.com/watch?v=...`, `youtu.be/...`, `youtube.com/shorts/...`.*"
        ),
        inline=False
    )

    embed.add_field(
        name="🎛️ 2. Lệnh Điều Khiển Trình Phát",
        value=(
            "• `he!pause` hoặc `/pause`: Tạm dừng bài hát đang phát.\n"
            "• `he!resume` hoặc `/resume`: Tiếp tục phát nhạc.\n"
            "• `he!skip` hoặc `/skip`: Bỏ qua bài hát hiện tại sang bài kế tiếp.\n"
            "• `he!repeat` hoặc `/repeat`: Bật/Tắt chế độ lặp lại bài hát hiện tại.\n"
            "• `he!stop` hoặc `/stop`: Dừng phát và xóa sạch toàn bộ hàng đợi.\n"
            "• `he!leave` hoặc `/leave`: Yêu cầu bot rời khỏi phòng voice."
        ),
        inline=False
    )

    embed.add_field(
        name="📋 3. Tra Cứu & Trợ Giúp",
        value=(
            "• `he!queue` hoặc `/queue`: Xem danh sách bài hát đang chờ phát.\n"
            "• `he!i` (hoặc `he!info`, `/info`, `/guide`): Mở bảng hướng dẫn này kèm dàn nút bấm thao tác nhanh!"
        ),
        inline=False
    )

    embed.add_field(
        name="🛡️ 4. Cơ Chế Độc Quyền & Tối Ưu Băng Thông",
        value=(
            "🔒 **Khóa phòng độc quyền:** Khi bot đang phục vụ phòng Voice A, người dùng ở phòng Voice B (kể cả Role HE hay Admin) **không thể** gọi hoặc can thiệp vào bot.\n"
            "⏱️ **Tự động ngắt tiết kiệm tài nguyên (AFK 60s):** Khi tất cả thành viên rời phòng voice, bot sẽ tự động đếm ngược **1 phút** rồi rời phòng để tiết kiệm băng thông.\n"
            "👑 **Quyền hạn:** Dành riêng cho thành viên có **Role HE**, Admin hoặc Founder."
        ),
        inline=False
    )

    if guild and guild.icon:
        embed.set_footer(text="HEe • Beat | Bấm các nút bên dưới để điều khiển nhanh", icon_url=guild.icon.url)
    else:
        embed.set_footer(text="HEe • Beat | Bấm các nút bên dưới để điều khiển nhanh")
    return embed

# ─────────────────── BOT SETUP ───────────────────
intents = discord.Intents.default()
intents.guilds = True
intents.messages = True
intents.message_content = True
intents.voice_states = True

class BeatBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix=['he!', 'HE!', 'he! '], intents=intents, help_command=None)

    async def setup_hook(self):
        guild = discord.Object(id=GUILD_ID)
        self.add_view(MusicControlsView())
        self.tree.copy_global_to(guild=guild)
        try:
            synced = await self.tree.sync(guild=guild)
            logger.info(f"Synced {len(synced)} slash command(s) vào guild {GUILD_ID}.")
        except discord.Forbidden:
            synced = await self.tree.sync()
            logger.info(f"Synced {len(synced)} global slash command(s).")

    async def on_ready(self):
        logger.info(f"Logged in as {self.user} (ID: {self.user.id})")
        await self.change_presence(
            activity=discord.Activity(type=discord.ActivityType.listening, name="he!p <link_ytb> | he!i | Role HE")
        )

bot = BeatBot()

async def play_next_song(guild: discord.Guild):
    manager = get_manager(guild.id)
    vc = guild.voice_client

    if not vc or not vc.is_connected():
        manager.clear()
        return

    # Nếu đang bật repeat bài hiện tại
    if manager.repeat and manager.current:
        next_song = manager.current
    elif manager.queue:
        next_song = manager.queue.popleft()
        manager.current = next_song
    else:
        manager.current = None
        if manager.text_channel and hasattr(manager.text_channel, 'send'):
            embed = discord.Embed(
                title="🎵 Hết Hàng Đợi",
                description="Đã phát hết danh sách nhạc trong hàng đợi. Đang chờ thêm bài hát mới...",
                color=COLOR_RED
            )
            await manager.text_channel.send(embed=embed)
        return

    try:
        audio_source = discord.PCMVolumeTransformer(
            discord.FFmpegPCMAudio(next_song.stream_url, **FFMPEG_OPTIONS),
            volume=0.8
        )

        def after_callback(error):
            if error:
                logger.error(f"Lỗi playback: {error}")
            coro = play_next_song(guild)
            fut = asyncio.run_coroutine_threadsafe(coro, bot.loop)
            try:
                fut.result()
            except Exception as e:
                logger.error(f"Lỗi callback sau phát nhạc: {e}")

        vc.play(audio_source, after=after_callback)

        if manager.text_channel and hasattr(manager.text_channel, 'send'):
            embed = discord.Embed(
                title="🎶 Đang Phát — HEe Beat",
                description=(
                    f"**[{next_song.title}]({next_song.webpage_url})**\n\n"
                    f"⏱️ **Thời lượng:** `{format_duration(next_song.duration)}`\n"
                    f"👤 **Yêu cầu bởi:** {next_song.requester.mention}\n"
                    f"🔁 **Lặp lại:** `{'Bật' if manager.repeat else 'Tắt'}`\n"
                    f"📋 **Còn lại trong hàng đợi:** `{len(manager.queue)} bài`"
                ),
                color=COLOR_RED,
                timestamp=datetime.now(timezone.utc)
            )
            if next_song.thumbnail:
                embed.set_thumbnail(url=next_song.thumbnail)
            embed.set_footer(text="High Ego eSport • Exclusive Music Suite")
            await manager.text_channel.send(embed=embed, view=MusicControlsView())

    except Exception as e:
        logger.error(f"Lỗi khởi tạo âm thanh: {e}")
        if manager.text_channel and hasattr(manager.text_channel, 'send'):
            await manager.text_channel.send(f"⚠️ Không thể phát bài hát: `{next_song.title}` ({e})")
        await play_next_song(guild)

# ─────────────────── AUTO-LEAVE AFK ───────────────────
@bot.event
async def on_voice_state_update(member: discord.Member, before: discord.VoiceState, after: discord.VoiceState):
    """Tự động out phòng sau 1 phút nếu phòng không còn ai để tiết kiệm băng thông"""
    guild = member.guild
    vc = guild.voice_client

    if not vc or not vc.is_connected() or not vc.channel:
        return

    manager = get_manager(guild.id)
    non_bot_members = [m for m in vc.channel.members if not m.bot]

    if len(non_bot_members) == 0:
        if not manager.afk_task or manager.afk_task.done():
            logger.info(f"Phòng {vc.channel.name} trống người, bắt đầu đếm ngược 1 phút tự out...")

            async def countdown_leave():
                try:
                    await asyncio.sleep(60)
                    if vc and vc.is_connected() and vc.channel:
                        current_non_bots = [m for m in vc.channel.members if not m.bot]
                        if len(current_non_bots) == 0:
                            if manager.text_channel and hasattr(manager.text_channel, 'send'):
                                embed = discord.Embed(
                                    title="🔌 Tự Động Rời Phòng",
                                    description=f"Phòng **{vc.channel.name}** không còn ai sau 1 phút. Bot đã tự động ngắt kết nối để tiết kiệm băng thông.",
                                    color=COLOR_RED
                                )
                                await manager.text_channel.send(embed=embed)
                            manager.clear()
                            await vc.disconnect()
                            logger.info(f"Đã ngắt kết nối khỏi phòng trống {vc.channel.name}.")
                except asyncio.CancelledError:
                    logger.info("Đếm ngược auto-leave bị hủy do có người quay lại phòng.")

            manager.afk_task = asyncio.create_task(countdown_leave())

    else:
        # Nếu có người quay lại hoặc tham gia phòng
        if manager.afk_task and not manager.afk_task.done():
            manager.afk_task.cancel()
            manager.afk_task = None
            logger.info(f"Thành viên {member.display_name} tham gia, đã hủy đếm ngược out phòng.")

# ─────────────────── CORE MUSIC LOGIC ───────────────────
async def process_play_request(
    channel_send,
    member: discord.Member,
    guild: discord.Guild,
    url: str,
    text_channel: Optional[discord.abc.Messageable] = None
):
    if not is_authorized(member):
        await channel_send("❌ Lệnh phát nhạc này chỉ dành riêng cho thành viên có **Role HE** hoặc **Administrator**!")
        return

    clean_url = url.strip()
    if not is_youtube_url(clean_url):
        await channel_send("❌ Chỉ chấp nhận **link YouTube cụ thể** (VD: `https://www.youtube.com/watch?v=...` hoặc `https://youtu.be/...`)! Không hỗ trợ từ khóa tìm kiếm hoặc link từ nền tảng khác.")
        return

    ok, err_msg, target_vc = check_voice_exclusivity(member, guild)
    if not ok:
        await channel_send(err_msg)
        return

    manager = get_manager(guild.id)
    if text_channel:
        manager.text_channel = text_channel
    elif isinstance(channel_send, discord.abc.Messageable):
        manager.text_channel = channel_send

    vc = guild.voice_client
    if not vc or not vc.is_connected():
        try:
            vc = await target_vc.connect()
            manager.voice_client = vc
        except Exception as e:
            await channel_send(f"❌ Không thể kết nối vào kênh voice: {e}")
            return
    elif vc.channel.id != target_vc.id:
        await channel_send("🔒 Bot đang phát nhạc tại phòng khác, bạn không thể gọi bot!")
        return

    # Nếu đang đếm ngược out phòng thì hủy
    if manager.afk_task and not manager.afk_task.done():
        manager.afk_task.cancel()
        manager.afk_task = None

    loading_msg = await channel_send("🔍 Đang tải thông tin bài hát từ YouTube...")
    if loading_msg:
        asyncio.create_task(delete_after_delay(loading_msg, 5))

    song = await extract_youtube_info(clean_url, member)
    if not song:
        err_msg = await channel_send("❌ Không thể trích xuất âm thanh từ link YouTube này! (Video có thể bị giới hạn bản quyền, độ tuổi hoặc URL không hợp lệ).")
        if err_msg:
            asyncio.create_task(delete_after_delay(err_msg, 10))
        return

    if vc.is_playing() or vc.is_paused():
        manager.queue.append(song)
        embed = discord.Embed(
            title="📥 Đã Thêm Vào Hàng Đợi",
            description=(
                f"**[{song.title}]({song.webpage_url})**\n\n"
                f"⏱️ **Thời lượng:** `{format_duration(song.duration)}`\n"
                f"🔢 **Vị trí trong hàng đợi:** `#{len(manager.queue)}`\n"
                f"👤 **Yêu cầu:** {member.mention}\n\n"
                f"*(Thông báo này sẽ tự động xóa sau 10 giây để tránh làm loãng chat)*"
            ),
            color=COLOR_RED
        )
        if song.thumbnail:
            embed.set_thumbnail(url=song.thumbnail)
        sent_msg = await channel_send(embed=embed)
        if sent_msg:
            asyncio.create_task(delete_after_delay(sent_msg, 10))
    else:
        manager.queue.append(song)
        await play_next_song(guild)

# ─────────────────── PREFIX COMMANDS (he!p ...) ───────────────────
@bot.command(name='p')
async def prefix_play(ctx: commands.Context, *, url: str = None):
    if not url:
        await ctx.send("❌ Vui lòng nhập link YouTube cần phát! Ví dụ: `he!p https://www.youtube.com/watch?v=...`")
        return
    await process_play_request(ctx.send, ctx.author, ctx.guild, url, ctx.channel)

@bot.command(name='skip')
async def prefix_skip(ctx: commands.Context):
    if not is_authorized(ctx.author):
        await ctx.send("❌ Chỉ thành viên có **Role HE** mới có quyền chuyển bài!")
        return
    ok, err_msg, _ = check_voice_exclusivity(ctx.author, ctx.guild)
    if not ok:
        await ctx.send(err_msg)
        return

    vc = ctx.guild.voice_client
    if vc and (vc.is_playing() or vc.is_paused()):
        vc.stop()
        await ctx.send("⏭️ Đã bỏ qua bài hát hiện tại!")
    else:
        await ctx.send("⚠️ Không có bài hát nào đang phát.")

@bot.command(name='pause')
async def prefix_pause(ctx: commands.Context):
    if not is_authorized(ctx.author):
        await ctx.send("❌ Quyền này chỉ dành cho **Role HE**!")
        return
    ok, err_msg, _ = check_voice_exclusivity(ctx.author, ctx.guild)
    if not ok:
        await ctx.send(err_msg)
        return

    vc = ctx.guild.voice_client
    if vc and vc.is_playing():
        vc.pause()
        await ctx.send("⏸️ Đã tạm dừng phát nhạc.")
    else:
        await ctx.send("⚠️ Bot không phát nhạc hoặc bài hát đã bị tạm dừng.")

@bot.command(name='resume')
async def prefix_resume(ctx: commands.Context):
    if not is_authorized(ctx.author):
        await ctx.send("❌ Quyền này chỉ dành cho **Role HE**!")
        return
    ok, err_msg, _ = check_voice_exclusivity(ctx.author, ctx.guild)
    if not ok:
        await ctx.send(err_msg)
        return

    vc = ctx.guild.voice_client
    if vc and vc.is_paused():
        vc.resume()
        await ctx.send("▶️ Đã tiếp tục phát nhạc.")
    else:
        await ctx.send("⚠️ Nhạc không ở trạng thái tạm dừng.")

@bot.command(name='stop')
async def prefix_stop(ctx: commands.Context):
    if not is_authorized(ctx.author):
        await ctx.send("❌ Quyền này chỉ dành cho **Role HE**!")
        return
    ok, err_msg, _ = check_voice_exclusivity(ctx.author, ctx.guild)
    if not ok:
        await ctx.send(err_msg)
        return

    manager = get_manager(ctx.guild.id)
    manager.clear()
    vc = ctx.guild.voice_client
    if vc and (vc.is_playing() or vc.is_paused()):
        vc.stop()
    await ctx.send("⏹️ Đã dừng phát nhạc và xóa toàn bộ hàng đợi.")

@bot.command(name='repeat')
async def prefix_repeat(ctx: commands.Context):
    if not is_authorized(ctx.author):
        await ctx.send("❌ Quyền này chỉ dành cho **Role HE**!")
        return
    ok, err_msg, _ = check_voice_exclusivity(ctx.author, ctx.guild)
    if not ok:
        await ctx.send(err_msg)
        return

    manager = get_manager(ctx.guild.id)
    manager.repeat = not manager.repeat
    status = "BẬT" if manager.repeat else "TẮT"
    await ctx.send(f"🔁 Chế độ lặp lại bài hát hiện tại: **{status}**")

@bot.command(name='queue', aliases=['q'])
async def prefix_queue(ctx: commands.Context):
    manager = get_manager(ctx.guild.id)
    if not manager.current and not manager.queue:
        await ctx.send("📭 Hàng đợi hiện đang trống.")
        return

    lines = []
    if manager.current:
        lines.append(f"▶️ **Đang phát:** [{manager.current.title}]({manager.current.webpage_url}) (`{format_duration(manager.current.duration)}`)")

    if manager.queue:
        lines.append("\n**Danh sách kế tiếp:**")
        for i, s in enumerate(list(manager.queue)[:10], 1):
            lines.append(f"`{i}.` [{s.title}]({s.webpage_url}) (`{format_duration(s.duration)}`) | Yêu cầu: {s.requester.mention}")
        if len(manager.queue) > 10:
            lines.append(f"*... và còn {len(manager.queue) - 10} bài hát khác.*")

    embed = discord.Embed(
        title="📋 Danh Sách Nhạc Hàng Đợi",
        description="\n".join(lines),
        color=COLOR_RED
    )
    embed.set_footer(text=f"Tổng số bài: {len(manager.queue) + (1 if manager.current else 0)} • Lặp lại: {'Bật' if manager.repeat else 'Tắt'}")
    await ctx.send(embed=embed)

@bot.command(name='leave', aliases=['out'])
async def prefix_leave(ctx: commands.Context):
    if not is_authorized(ctx.author):
        await ctx.send("❌ Quyền này chỉ dành cho **Role HE**!")
        return
    ok, err_msg, _ = check_voice_exclusivity(ctx.author, ctx.guild)
    if not ok:
        await ctx.send(err_msg)
        return

    manager = get_manager(ctx.guild.id)
    manager.clear()
    vc = ctx.guild.voice_client
    if vc and vc.is_connected():
        await vc.disconnect()
        await ctx.send("👋 Đã rời khỏi phòng voice và dọn dẹp hàng đợi.")
    else:
        await ctx.send("⚠️ Bot không có trong kênh voice nào.")

@bot.command(name='i', aliases=['info', 'help', 'guide'])
async def prefix_info(ctx: commands.Context):
    """Hiển thị bảng hướng dẫn và dàn nút điều khiển âm nhạc"""
    embed = build_guide_embed(ctx.guild)
    view = MusicControlsView()
    await ctx.send(embed=embed, view=view)

# ─────────────────── SLASH COMMANDS (/play ...) ───────────────────
@bot.tree.command(name='play', description='[Role HE] Phát nhạc YouTube cụ thể (độc quyền phòng voice)')
@app_commands.describe(link_ytb='Link YouTube video hoặc shorts cụ thể')
async def slash_play(interaction: discord.Interaction, link_ytb: str):
    await interaction.response.defer()
    async def reply_func(*args, **kwargs):
        if 'embed' in kwargs:
            return await interaction.followup.send(embed=kwargs['embed'])
        elif args and isinstance(args[0], discord.Embed):
            return await interaction.followup.send(embed=args[0])
        elif args:
            return await interaction.followup.send(str(args[0]))
        elif 'content' in kwargs:
            return await interaction.followup.send(kwargs['content'])
        return None
    await process_play_request(reply_func, interaction.user, interaction.guild, link_ytb, interaction.channel)

@bot.tree.command(name='he-play', description='[Role HE] Phát nhạc YouTube (tương tự /play hoặc he!p)')
@app_commands.describe(link_ytb='Link YouTube video cụ thể')
async def slash_he_play(interaction: discord.Interaction, link_ytb: str):
    await interaction.response.defer()
    async def reply_func(*args, **kwargs):
        if 'embed' in kwargs:
            return await interaction.followup.send(embed=kwargs['embed'])
        elif args and isinstance(args[0], discord.Embed):
            return await interaction.followup.send(embed=args[0])
        elif args:
            return await interaction.followup.send(str(args[0]))
        elif 'content' in kwargs:
            return await interaction.followup.send(kwargs['content'])
        return None
    await process_play_request(reply_func, interaction.user, interaction.guild, link_ytb, interaction.channel)

@bot.tree.command(name='skip', description='[Role HE] Bỏ qua bài hát hiện tại')
async def slash_skip(interaction: discord.Interaction):
    if not is_authorized(interaction.user):
        await interaction.response.send_message("❌ Chỉ thành viên có **Role HE** mới có quyền chuyển bài!", ephemeral=True)
        return
    ok, err_msg, _ = check_voice_exclusivity(interaction.user, interaction.guild)
    if not ok:
        await interaction.response.send_message(err_msg, ephemeral=True)
        return

    vc = interaction.guild.voice_client
    if vc and (vc.is_playing() or vc.is_paused()):
        vc.stop()
        await interaction.response.send_message("⏭️ Đã bỏ qua bài hát hiện tại!")
    else:
        await interaction.response.send_message("⚠️ Không có bài hát nào đang phát.", ephemeral=True)

@bot.tree.command(name='pause', description='[Role HE] Tạm dừng phát nhạc')
async def slash_pause(interaction: discord.Interaction):
    if not is_authorized(interaction.user):
        await interaction.response.send_message("❌ Quyền này chỉ dành cho **Role HE**!", ephemeral=True)
        return
    ok, err_msg, _ = check_voice_exclusivity(interaction.user, interaction.guild)
    if not ok:
        await interaction.response.send_message(err_msg, ephemeral=True)
        return

    vc = interaction.guild.voice_client
    if vc and vc.is_playing():
        vc.pause()
        await interaction.response.send_message("⏸️ Đã tạm dừng phát nhạc.")
    else:
        await interaction.response.send_message("⚠️ Bot không phát nhạc hoặc đã tạm dừng.", ephemeral=True)

@bot.tree.command(name='resume', description='[Role HE] Tiếp tục phát nhạc')
async def slash_resume(interaction: discord.Interaction):
    if not is_authorized(interaction.user):
        await interaction.response.send_message("❌ Quyền này chỉ dành cho **Role HE**!", ephemeral=True)
        return
    ok, err_msg, _ = check_voice_exclusivity(interaction.user, interaction.guild)
    if not ok:
        await interaction.response.send_message(err_msg, ephemeral=True)
        return

    vc = interaction.guild.voice_client
    if vc and vc.is_paused():
        vc.resume()
        await interaction.response.send_message("▶️ Đã tiếp tục phát nhạc.")
    else:
        await interaction.response.send_message("⚠️ Nhạc không ở trạng thái tạm dừng.", ephemeral=True)

@bot.tree.command(name='stop', description='[Role HE] Dừng phát và dọn sạch hàng đợi')
async def slash_stop(interaction: discord.Interaction):
    if not is_authorized(interaction.user):
        await interaction.response.send_message("❌ Quyền này chỉ dành cho **Role HE**!", ephemeral=True)
        return
    ok, err_msg, _ = check_voice_exclusivity(interaction.user, interaction.guild)
    if not ok:
        await interaction.response.send_message(err_msg, ephemeral=True)
        return

    manager = get_manager(interaction.guild.id)
    manager.clear()
    vc = interaction.guild.voice_client
    if vc and (vc.is_playing() or vc.is_paused()):
        vc.stop()
    await interaction.response.send_message("⏹️ Đã dừng phát nhạc và xóa toàn bộ hàng đợi.")

@bot.tree.command(name='repeat', description='[Role HE] Bật hoặc tắt lặp lại bài hát hiện tại')
async def slash_repeat(interaction: discord.Interaction):
    if not is_authorized(interaction.user):
        await interaction.response.send_message("❌ Quyền này chỉ dành cho **Role HE**!", ephemeral=True)
        return
    ok, err_msg, _ = check_voice_exclusivity(interaction.user, interaction.guild)
    if not ok:
        await interaction.response.send_message(err_msg, ephemeral=True)
        return

    manager = get_manager(interaction.guild.id)
    manager.repeat = not manager.repeat
    status = "BẬT" if manager.repeat else "TẮT"
    await interaction.response.send_message(f"🔁 Chế độ lặp lại bài hát hiện tại: **{status}**")

@bot.tree.command(name='queue', description='Xem danh sách hàng đợi các bài hát kế tiếp')
async def slash_queue(interaction: discord.Interaction):
    manager = get_manager(interaction.guild.id)
    if not manager.current and not manager.queue:
        await interaction.response.send_message("📭 Hàng đợi hiện đang trống.", ephemeral=True)
        return

    lines = []
    if manager.current:
        lines.append(f"▶️ **Đang phát:** [{manager.current.title}]({manager.current.webpage_url}) (`{format_duration(manager.current.duration)}`)")

    if manager.queue:
        lines.append("\n**Danh sách kế tiếp:**")
        for i, s in enumerate(list(manager.queue)[:10], 1):
            lines.append(f"`{i}.` [{s.title}]({s.webpage_url}) (`{format_duration(s.duration)}`) | Yêu cầu: {s.requester.mention}")
        if len(manager.queue) > 10:
            lines.append(f"*... và còn {len(manager.queue) - 10} bài hát khác.*")

    embed = discord.Embed(
        title="📋 Danh Sách Nhạc Hàng Đợi",
        description="\n".join(lines),
        color=COLOR_RED
    )
    embed.set_footer(text=f"Tổng số bài: {len(manager.queue) + (1 if manager.current else 0)} • Lặp lại: {'Bật' if manager.repeat else 'Tắt'}")
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name='leave', description='[Role HE] Rời khỏi phòng voice')
async def slash_leave(interaction: discord.Interaction):
    if not is_authorized(interaction.user):
        await interaction.response.send_message("❌ Quyền này chỉ dành cho **Role HE**!", ephemeral=True)
        return
    ok, err_msg, _ = check_voice_exclusivity(interaction.user, interaction.guild)
    if not ok:
        await interaction.response.send_message(err_msg, ephemeral=True)
        return

    manager = get_manager(interaction.guild.id)
    manager.clear()
    vc = interaction.guild.voice_client
    if vc and vc.is_connected():
        await vc.disconnect()
        await interaction.response.send_message("👋 Đã rời khỏi phòng voice và dọn dẹp hàng đợi.")
    else:
        await interaction.response.send_message("⚠️ Bot không có trong kênh voice nào.", ephemeral=True)

@bot.tree.command(name='info', description='Bảng hướng dẫn lệnh và các nút điều khiển bot nhạc HEe • Beat')
async def slash_info(interaction: discord.Interaction):
    embed = build_guide_embed(interaction.guild)
    view = MusicControlsView()
    await interaction.response.send_message(embed=embed, view=view)

@bot.tree.command(name='guide', description='Hướng dẫn sử dụng và bảng nút thao tác nhanh HEe • Beat')
async def slash_guide(interaction: discord.Interaction):
    embed = build_guide_embed(interaction.guild)
    view = MusicControlsView()
    await interaction.response.send_message(embed=embed, view=view)

if __name__ == '__main__':
    if not BOT_TOKEN:
        logger.error("BOT_TOKEN chưa cài đặt!")
        sys.exit(1)
    if not GUILD_ID:
        logger.error("GUILD_ID chưa cài đặt!")
        sys.exit(1)
    bot.run(BOT_TOKEN, log_handler=None)
