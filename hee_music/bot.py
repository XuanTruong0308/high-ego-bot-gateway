"""
bot.py — HEe • Beat (Music Bot độc quyền cho Role HE chạy trên nền tảng Lavalink v4)
- Kết nối Lavalink v4 hỗ trợ giải mã E2EE DAVE mới nhất của Discord
- Hỗ trợ Prefix: he!p <link_ytb>, he!skip, he!pause, he!resume, he!stop, he!queue, he!repeat, he!leave, he!i
- Hỗ trợ Slash: /play, /he-play, /skip, /pause, /resume, /stop, /queue, /repeat, /leave, /info, /guide
- Phân quyền: Độc quyền Role HE / Founder / Admin
- Khóa phòng voice độc quyền: Đang phát tại phòng nào thì phòng khác KHÔNG ĐƯỢC PHÉP can thiệp
- Auto-leave: Tự động rời phòng và dọn dẹp sau 1 phút nếu phòng không còn ai
- Auto-delete: Thông báo thêm vào hàng đợi tự động biến mất sau 10s
"""

import os
import re
import sys
import asyncio
import logging
from datetime import datetime, timezone
from typing import Optional, List, Dict

import discord
from discord import app_commands
from discord.ext import commands
from dotenv import load_dotenv
import wavelink

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

BOT_TOKEN     = os.getenv('BOT_TOKEN', '')
GUILD_ID      = int(os.getenv('GUILD_ID', '0'))
HE_ROLE_NAME  = os.getenv('HE_ROLE_NAME', 'HE')
OWNER_USER_ID = os.getenv('OWNER_USER_ID', '1147375213634388008')
LAVALINK_URI  = os.getenv('LAVALINK_URI', 'http://lavalink:2333')
LAVALINK_PASS = os.getenv('LAVALINK_PASS', 'hee_secret_password_2026')

COLOR_RED  = 0xE11D48
COLOR_DARK = 0x881337

YOUTUBE_URL_REGEX = re.compile(
    r'^(https?://)?(www\.|m\.)?(youtube\.com/watch\?v=|youtu\.be/|youtube\.com/shorts/)[a-zA-Z0-9_-]+'
)

def is_authorized(member: discord.Member) -> bool:
    """Kiểm tra quyền Role HE / Founder / Admin"""
    if str(member.id) == OWNER_USER_ID or member.id == 1147375213634388008:
        return True
    if member.guild_permissions.administrator:
        return True
    return any(r.name == HE_ROLE_NAME or str(r.id) == HE_ROLE_NAME for r in member.roles)

def is_youtube_url(url: str) -> bool:
    return bool(YOUTUBE_URL_REGEX.match(url.strip()))

def format_duration(milliseconds: Optional[int]) -> str:
    if not milliseconds or milliseconds == 0:
        return "Livestream"
    seconds = milliseconds // 1000
    m, s = divmod(seconds, 60)
    h, m = divmod(m, 60)
    if h > 0:
        return f"{h:02d}:{m:02d}:{s:02d}"
    return f"{m:02d}:{s:02d}"

async def delete_after_delay(msg, delay: int = 10):
    """Xóa tin nhắn sau một khoảng thời gian nhất định (mặc định 10s)"""
    try:
        await asyncio.sleep(delay)
        if hasattr(msg, 'delete'):
            await msg.delete()
    except Exception:
        pass

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
    player: Optional[wavelink.Player] = guild.voice_client

    if player and player.connected and player.channel:
        if player.channel.id != user_channel.id:
            return False, (
                f"🔒 **PHÒNG ĐỘC QUYỀN ĐANG HOẠT ĐỘNG:**\n"
                f"Bot đang phát nhạc phục vụ riêng tại phòng **{player.channel.name}**!\n"
                f"👉 Thành viên tại các phòng voice khác (kể cả Role HE) không được can thiệp cho đến khi phòng hiện tại rời đi."
            ), player.channel

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
        player: Optional[wavelink.Player] = interaction.guild.voice_client
        if not player or not player.connected:
            await interaction.response.send_message("⚠️ Bot không có trong phòng voice.", ephemeral=True)
            return
        if player.playing and not player.paused:
            await player.pause(True)
            await interaction.response.send_message(f"⏸️ {interaction.user.mention} đã tạm dừng phát nhạc.")
        elif player.paused:
            await player.pause(False)
            await interaction.response.send_message(f"▶️ {interaction.user.mention} đã tiếp tục phát nhạc.")
        else:
            await interaction.response.send_message("⚠️ Hiện không có bài hát nào đang phát.", ephemeral=True)

    @discord.ui.button(label="Bỏ qua", style=discord.ButtonStyle.primary, emoji="⏭️", custom_id="hee_music:skip")
    async def skip_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        player: Optional[wavelink.Player] = interaction.guild.voice_client
        if player and player.playing:
            await player.skip(force=True)
            await interaction.response.send_message(f"⏭️ {interaction.user.mention} đã bỏ qua bài hát hiện tại!")
        else:
            await interaction.response.send_message("⚠️ Không có bài hát nào đang phát.", ephemeral=True)

    @discord.ui.button(label="Lặp lại", style=discord.ButtonStyle.secondary, emoji="🔁", custom_id="hee_music:repeat")
    async def repeat_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        player: Optional[wavelink.Player] = interaction.guild.voice_client
        if not player:
            await interaction.response.send_message("⚠️ Bot không có trong phòng voice.", ephemeral=True)
            return
        if player.queue.mode == wavelink.QueueMode.loop:
            player.queue.mode = wavelink.QueueMode.normal
            status = "TẮT"
        else:
            player.queue.mode = wavelink.QueueMode.loop
            status = "BẬT"
        await interaction.response.send_message(f"🔁 Chế độ lặp lại bài hát hiện tại: **{status}**")

    @discord.ui.button(label="Hàng đợi", style=discord.ButtonStyle.secondary, emoji="📋", custom_id="hee_music:queue")
    async def queue_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        player: Optional[wavelink.Player] = interaction.guild.voice_client
        if not player or (not player.current and player.queue.is_empty):
            await interaction.response.send_message("📭 Hàng đợi hiện đang trống.", ephemeral=True)
            return

        lines = []
        if player.current:
            lines.append(f"▶️ **Đang phát:** [{player.current.title}]({player.current.uri}) (`{format_duration(player.current.length)}`)")

        if not player.queue.is_empty:
            lines.append("\n**Danh sách kế tiếp:**")
            queue_list = list(player.queue)
            for i, s in enumerate(queue_list[:10], 1):
                req_mention = getattr(s, 'requester_mention', 'Thành viên')
                lines.append(f"`{i}.` [{s.title}]({s.uri}) (`{format_duration(s.length)}`) | {req_mention}")
            if len(queue_list) > 10:
                lines.append(f"*... và còn {len(queue_list) - 10} bài hát khác.*")

        embed = discord.Embed(
            title="📋 Danh Sách Nhạc Hàng Đợi",
            description="\n".join(lines),
            color=COLOR_RED
        )
        is_loop = player.queue.mode == wavelink.QueueMode.loop
        embed.set_footer(text=f"Tổng số bài: {len(player.queue) + (1 if player.current else 0)} • Lặp lại: {'Bật' if is_loop else 'Tắt'}")
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @discord.ui.button(label="Dừng & Rời", style=discord.ButtonStyle.danger, emoji="⏹️", custom_id="hee_music:stop")
    async def stop_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        player: Optional[wavelink.Player] = interaction.guild.voice_client
        if player:
            player.queue.clear()
            await player.disconnect()
            await interaction.response.send_message(f"⏹️ {interaction.user.mention} đã dừng nhạc, dọn dẹp hàng đợi và đưa bot rời phòng voice.")
        else:
            await interaction.response.send_message("⚠️ Bot không có trong phòng voice.", ephemeral=True)

# ─────────────────── GUIDE EMBED BUILDER ───────────────────
def build_guide_embed(guild: Optional[discord.Guild] = None) -> discord.Embed:
    embed = discord.Embed(
        title="🎵 HEe • Beat — Hướng Dẫn Sử Dụng & Bảng Lệnh",
        description=(
            "**HEe • Beat** là hệ thống phát nhạc YouTube chất lượng cao (320kbps Lavalink v4) độc quyền dành riêng cho thành viên mang **Role HE**, Ban Quản Trị và Founder tại **High Ego eSport**.\n\n"
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

afk_tasks: Dict[int, asyncio.Task] = {}

class BeatBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix=['he!', 'HE!', 'he! '], intents=intents, help_command=None)

    async def setup_hook(self):
        # Kết nối Lavalink v4
        node = wavelink.Node(
            uri=LAVALINK_URI,
            password=LAVALINK_PASS
        )
        try:
            await wavelink.Pool.connect(nodes=[node], client=self)
            logger.info(f"Đã đăng ký Lavalink Node: {LAVALINK_URI}")
        except Exception as e:
            logger.error(f"Lỗi kết nối Lavalink Node: {e}")

        # Nạp view các nút bấm điều khiển
        self.add_view(MusicControlsView())

        # Đồng bộ Slash Commands
        guild = discord.Object(id=GUILD_ID)
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

# ─────────────────── WAVELINK EVENTS ───────────────────
@bot.event
async def on_wavelink_node_ready(payload: wavelink.NodeReadyEventPayload):
    logger.info(f"Lavalink Node sẵn sàng: {payload.node!r} (Resumed: {payload.resumed})")

@bot.event
async def on_wavelink_track_start(payload: wavelink.TrackStartEventPayload):
    player: wavelink.Player = payload.player
    track: wavelink.Playable = payload.track
    if not player or not track:
        return

    home_channel = getattr(player, 'home_channel', None)
    if home_channel and hasattr(home_channel, 'send'):
        req_mention = getattr(track, 'requester_mention', 'Role HE')
        embed = discord.Embed(
            title="🎶 Đang Phát — HEe Beat",
            description=(
                f"**[{track.title}]({track.uri})**\n\n"
                f"⏱️ **Thời lượng:** `{format_duration(track.length)}`\n"
                f"👤 **Yêu cầu bởi:** {req_mention}\n"
                f"🔁 **Lặp lại:** `{'Bật' if player.queue.mode == wavelink.QueueMode.loop else 'Tắt'}`\n"
                f"📋 **Còn lại trong hàng đợi:** `{len(player.queue)} bài`"
            ),
            color=COLOR_RED,
            timestamp=datetime.now(timezone.utc)
        )
        if track.artwork:
            embed.set_thumbnail(url=track.artwork)
        embed.set_footer(text="High Ego eSport • Lavalink v4 Audio Engine")
        await home_channel.send(embed=embed, view=MusicControlsView())

@bot.event
async def on_wavelink_track_end(payload: wavelink.TrackEndEventPayload):
    player: wavelink.Player = payload.player
    if not player:
        return
    if player.queue.is_empty and not player.playing:
        home_channel = getattr(player, 'home_channel', None)
        if home_channel and hasattr(home_channel, 'send'):
            embed = discord.Embed(
                title="🎵 Hết Hàng Đợi",
                description="Đã phát hết danh sách nhạc trong hàng đợi. Đang chờ thêm bài hát mới...",
                color=COLOR_RED
            )
            await home_channel.send(embed=embed)

# ─────────────────── AUTO-LEAVE AFK ───────────────────
@bot.event
async def on_voice_state_update(member: discord.Member, before: discord.VoiceState, after: discord.VoiceState):
    """Tự động out phòng sau 1 phút nếu phòng không còn ai để tiết kiệm băng thông"""
    guild = member.guild
    player: Optional[wavelink.Player] = guild.voice_client

    if not player or not player.connected or not player.channel:
        return

    non_bot_members = [m for m in player.channel.members if not m.bot]

    if len(non_bot_members) == 0:
        task = afk_tasks.get(guild.id)
        if not task or task.done():
            logger.info(f"Phòng {player.channel.name} trống người, bắt đầu đếm ngược 1 phút tự out...")

            async def countdown_leave():
                try:
                    await asyncio.sleep(60)
                    if player and player.connected and player.channel:
                        current_non_bots = [m for m in player.channel.members if not m.bot]
                        if len(current_non_bots) == 0:
                            home_channel = getattr(player, 'home_channel', None)
                            if home_channel and hasattr(home_channel, 'send'):
                                embed = discord.Embed(
                                    title="🔌 Tự Động Rời Phòng",
                                    description=f"Phòng **{player.channel.name}** không còn ai sau 1 phút. Bot đã tự động ngắt kết nối để tiết kiệm băng thông.",
                                    color=COLOR_RED
                                )
                                await home_channel.send(embed=embed)
                            player.queue.clear()
                            await player.disconnect()
                            logger.info(f"Đã ngắt kết nối khỏi phòng trống {player.channel.name}.")
                except asyncio.CancelledError:
                    logger.info("Đếm ngược auto-leave bị hủy do có người quay lại phòng.")

            afk_tasks[guild.id] = asyncio.create_task(countdown_leave())

    else:
        task = afk_tasks.get(guild.id)
        if task and not task.done():
            task.cancel()
            afk_tasks[guild.id] = None
            logger.info(f"Thành viên {member.display_name} tham gia, đã hủy đếm ngược out phòng.")

# ─────────────────── CORE PLAY PROCESSOR ───────────────────
async def process_play_request(
    channel_send,
    member: discord.Member,
    guild: discord.Guild,
    url: str,
    text_channel: discord.abc.Messageable
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

    player: Optional[wavelink.Player] = guild.voice_client
    if not player:
        try:
            player = await target_vc.connect(cls=wavelink.Player, self_deaf=True)
        except Exception as e:
            await channel_send(f"❌ Không thể kết nối vào kênh voice: {e}")
            return
    elif player.channel.id != target_vc.id:
        await channel_send("🔒 Bot đang phát nhạc tại phòng khác, bạn không thể gọi bot!")
        return

    player.home_channel = text_channel

    # Hủy tác vụ AFK nếu có
    task = afk_tasks.get(guild.id)
    if task and not task.done():
        task.cancel()
        afk_tasks[guild.id] = None

    loading_msg = await channel_send("🔍 Đang tải dữ liệu từ YouTube qua Lavalink...")
    if loading_msg:
        asyncio.create_task(delete_after_delay(loading_msg, 5))

    try:
        tracks: wavelink.Search = await wavelink.Playable.search(clean_url)
    except Exception as e:
        logger.error(f"Lỗi tìm kiếm track: {e}")
        await channel_send(f"❌ Lỗi tìm kiếm nguồn phát: {e}")
        return

    if not tracks:
        await channel_send("❌ Không tìm thấy bài hát từ link YouTube này!")
        return

    if isinstance(tracks, wavelink.Playlist):
        track = tracks[0]
    else:
        track = tracks[0]

    # Lưu thông tin người yêu cầu
    track.requester_mention = member.mention

    if player.playing or player.paused:
        await player.queue.put_wait(track)
        embed = discord.Embed(
            title="📥 Đã Thêm Vào Hàng Đợi",
            description=(
                f"**[{track.title}]({track.uri})**\n\n"
                f"⏱️ **Thời lượng:** `{format_duration(track.length)}`\n"
                f"🔢 **Vị trí trong hàng đợi:** `#{len(player.queue)}`\n"
                f"👤 **Yêu cầu:** {member.mention}\n\n"
                f"*(Thông báo này sẽ tự động xóa sau 10 giây để tránh làm loãng chat)*"
            ),
            color=COLOR_RED
        )
        if track.artwork:
            embed.set_thumbnail(url=track.artwork)
        sent_msg = await channel_send(embed=embed)
        if sent_msg:
            asyncio.create_task(delete_after_delay(sent_msg, 10))
    else:
        await player.play(track)

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

    player: Optional[wavelink.Player] = ctx.guild.voice_client
    if player and player.playing:
        await player.skip(force=True)
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

    player: Optional[wavelink.Player] = ctx.guild.voice_client
    if player and player.playing and not player.paused:
        await player.pause(True)
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

    player: Optional[wavelink.Player] = ctx.guild.voice_client
    if player and player.paused:
        await player.pause(False)
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

    player: Optional[wavelink.Player] = ctx.guild.voice_client
    if player:
        player.queue.clear()
        await player.stop()
        await ctx.send("⏹️ Đã dừng phát nhạc và xóa toàn bộ hàng đợi.")
    else:
        await ctx.send("⚠️ Bot không có trong kênh voice nào.")

@bot.command(name='repeat')
async def prefix_repeat(ctx: commands.Context):
    if not is_authorized(ctx.author):
        await ctx.send("❌ Quyền này chỉ dành cho **Role HE**!")
        return
    ok, err_msg, _ = check_voice_exclusivity(ctx.author, ctx.guild)
    if not ok:
        await ctx.send(err_msg)
        return

    player: Optional[wavelink.Player] = ctx.guild.voice_client
    if not player:
        await ctx.send("⚠️ Bot không có trong kênh voice nào.")
        return

    if player.queue.mode == wavelink.QueueMode.loop:
        player.queue.mode = wavelink.QueueMode.normal
        status = "TẮT"
    else:
        player.queue.mode = wavelink.QueueMode.loop
        status = "BẬT"
    await ctx.send(f"🔁 Chế độ lặp lại bài hát hiện tại: **{status}**")

@bot.command(name='queue', aliases=['q'])
async def prefix_queue(ctx: commands.Context):
    player: Optional[wavelink.Player] = ctx.guild.voice_client
    if not player or (not player.current and player.queue.is_empty):
        await ctx.send("📭 Hàng đợi hiện đang trống.")
        return

    lines = []
    if player.current:
        lines.append(f"▶️ **Đang phát:** [{player.current.title}]({player.current.uri}) (`{format_duration(player.current.length)}`)")

    if not player.queue.is_empty:
        lines.append("\n**Danh sách kế tiếp:**")
        queue_list = list(player.queue)
        for i, s in enumerate(queue_list[:10], 1):
            req_mention = getattr(s, 'requester_mention', 'Thành viên')
            lines.append(f"`{i}.` [{s.title}]({s.uri}) (`{format_duration(s.length)}`) | Yêu cầu: {req_mention}")
        if len(queue_list) > 10:
            lines.append(f"*... và còn {len(queue_list) - 10} bài hát khác.*")

    embed = discord.Embed(
        title="📋 Danh Sách Nhạc Hàng Đợi",
        description="\n".join(lines),
        color=COLOR_RED
    )
    is_loop = player.queue.mode == wavelink.QueueMode.loop
    embed.set_footer(text=f"Tổng số bài: {len(player.queue) + (1 if player.current else 0)} • Lặp lại: {'Bật' if is_loop else 'Tắt'}")
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

    player: Optional[wavelink.Player] = ctx.guild.voice_client
    if player and player.connected:
        player.queue.clear()
        await player.disconnect()
        await ctx.send("👋 Đã rời khỏi phòng voice và dọn dẹp hàng đợi.")
    else:
        await ctx.send("⚠️ Bot không có trong kênh voice nào.")

@bot.command(name='i', aliases=['info', 'help', 'guide'])
async def prefix_info(ctx: commands.Context):
    """Hiển thị bảng hướng dẫn và cụm nút bấm điều khiển âm nhạc"""
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

    player: Optional[wavelink.Player] = interaction.guild.voice_client
    if player and player.playing:
        await player.skip(force=True)
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

    player: Optional[wavelink.Player] = interaction.guild.voice_client
    if player and player.playing and not player.paused:
        await player.pause(True)
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

    player: Optional[wavelink.Player] = interaction.guild.voice_client
    if player and player.paused:
        await player.pause(False)
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

    player: Optional[wavelink.Player] = interaction.guild.voice_client
    if player:
        player.queue.clear()
        await player.stop()
        await interaction.response.send_message("⏹️ Đã dừng phát nhạc và xóa toàn bộ hàng đợi.")
    else:
        await interaction.response.send_message("⚠️ Bot không có trong kênh voice nào.", ephemeral=True)

@bot.tree.command(name='repeat', description='[Role HE] Bật hoặc tắt lặp lại bài hát hiện tại')
async def slash_repeat(interaction: discord.Interaction):
    if not is_authorized(interaction.user):
        await interaction.response.send_message("❌ Quyền này chỉ dành cho **Role HE**!", ephemeral=True)
        return
    ok, err_msg, _ = check_voice_exclusivity(interaction.user, interaction.guild)
    if not ok:
        await interaction.response.send_message(err_msg, ephemeral=True)
        return

    player: Optional[wavelink.Player] = interaction.guild.voice_client
    if not player:
        await interaction.response.send_message("⚠️ Bot không có trong phòng voice.", ephemeral=True)
        return

    if player.queue.mode == wavelink.QueueMode.loop:
        player.queue.mode = wavelink.QueueMode.normal
        status = "TẮT"
    else:
        player.queue.mode = wavelink.QueueMode.loop
        status = "BẬT"
    await interaction.response.send_message(f"🔁 Chế độ lặp lại bài hát hiện tại: **{status}**")

@bot.tree.command(name='queue', description='Xem danh sách hàng đợi các bài hát kế tiếp')
async def slash_queue(interaction: discord.Interaction):
    player: Optional[wavelink.Player] = interaction.guild.voice_client
    if not player or (not player.current and player.queue.is_empty):
        await interaction.response.send_message("📭 Hàng đợi hiện đang trống.", ephemeral=True)
        return

    lines = []
    if player.current:
        lines.append(f"▶️ **Đang phát:** [{player.current.title}]({player.current.uri}) (`{format_duration(player.current.length)}`)")

    if not player.queue.is_empty:
        lines.append("\n**Danh sách kế tiếp:**")
        queue_list = list(player.queue)
        for i, s in enumerate(queue_list[:10], 1):
            req_mention = getattr(s, 'requester_mention', 'Thành viên')
            lines.append(f"`{i}.` [{s.title}]({s.uri}) (`{format_duration(s.length)}`) | Yêu cầu: {req_mention}")
        if len(queue_list) > 10:
            lines.append(f"*... và còn {len(queue_list) - 10} bài hát khác.*")

    embed = discord.Embed(
        title="📋 Danh Sách Nhạc Hàng Đợi",
        description="\n".join(lines),
        color=COLOR_RED
    )
    is_loop = player.queue.mode == wavelink.QueueMode.loop
    embed.set_footer(text=f"Tổng số bài: {len(player.queue) + (1 if player.current else 0)} • Lặp lại: {'Bật' if is_loop else 'Tắt'}")
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

    player: Optional[wavelink.Player] = interaction.guild.voice_client
    if player and player.connected:
        player.queue.clear()
        await player.disconnect()
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
