"""
bot.py — HEe • Sentinel (AutoMod & Quick Delete & Error Debugger)
1. Lọc từ ngữ tục tĩu cực đoan và tự động xóa ngay lập tức.
2. Khi thành viên có role 'HE' thả icon tick xanh (✅) -> Tự động xóa tin nhắn đó sau 5 giây.
3. Bắt toàn bộ lỗi command, ghi log chi tiết và cung cấp lệnh /debug-logs cho Admin/HE role.
"""

import os
import sys
import asyncio
import logging
from datetime import datetime

import discord
from discord import app_commands
from discord.ext import commands
from dotenv import load_dotenv

from filter_engine import ProfanityFilter
import error_logger

# Import module kinh tế dùng chung để trừ điểm vi phạm
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "shared_data")))
try:
    import economy_db
except ImportError:
    economy_db = None

load_dotenv()

# ─────────────────────────── Windows UTF-8 fix ───────────────────────────
try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')
except AttributeError:
    pass

# ─────────────────────────── Logging Console ─────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger('HEe.Sentinel')

# ─────────────────────────── Config từ .env ──────────────────────────────
BOT_TOKEN        = os.getenv('BOT_TOKEN', '')
GUILD_ID         = int(os.getenv('GUILD_ID', '0'))
HE_ROLE_NAME     = os.getenv('HE_ROLE_NAME', 'HE')            # Tên role có quyền tick xanh xóa
LOG_CHANNEL_ID   = int(os.getenv('MOD_LOG_CHANNEL_ID', '0'))  # Kênh gửi thông báo vi phạm

# Brand Colors
COLOR_RED   = 0xE11D48
COLOR_DARK  = 0x881337

# Khởi tạo bộ lọc
profanity_filter = ProfanityFilter()

# ─────────────────────────── Bot Setup & Intents ──────────────────────────
intents = discord.Intents.default()
intents.messages = True
intents.message_content = True
intents.reactions = True
intents.members = True

class SentinelBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix='!', intents=intents)

    async def setup_hook(self):
        guild = discord.Object(id=GUILD_ID)
        self.tree.copy_global_to(guild=guild)
        try:
            synced_guild = await self.tree.sync(guild=guild)
            logger.info(f'Synced {len(synced_guild)} slash command(s) vào guild {GUILD_ID}.')
            synced_global = await self.tree.sync()
            logger.info(f'Synced {len(synced_global)} global slash command(s).')
        except discord.Forbidden:
            logger.warning(f'Không thể sync guild {GUILD_ID} (403). Chuyển sang global sync...')
            synced = await self.tree.sync()
            logger.info(f'Synced {len(synced)} global slash command(s).')

    async def on_ready(self):
        logger.info(f'Logged in as {self.user} (ID: {self.user.id})')
        guild_found = any(g.id == GUILD_ID for g in self.guilds)
        if guild_found:
            logger.info(f'Đã kết nối an toàn với máy chủ HEe ({GUILD_ID}).')
        else:
            logger.warning(f'Bot hiện KHÔNG có mặt trong GUILD_ID={GUILD_ID} trong .env!')

bot = SentinelBot()

# Helper kiểm tra role HE
def has_he_role(member: discord.Member) -> bool:
    if member.guild.owner_id == member.id:
        return True
    if member.guild_permissions.administrator or member.guild_permissions.manage_messages:
        return True
    return any(
        r.name == HE_ROLE_NAME
        or str(r.id) == HE_ROLE_NAME
        or r.name.lower() in ('he', 'role he', 'admin', 'mod', 'quản trị viên')
        for r in member.roles
    )

# ─────────────────────────── SỰ KIỆN 1: LỌC TỪ TỤC TĨU ───────────────────
@bot.event
async def on_message(message: discord.Message):
    if message.author.bot or not message.guild or message.guild.id != GUILD_ID:
        return

    # Quét nội dung bằng ProfanityFilter
    violated, word = profanity_filter.check(message.content)
    if violated:
        author = message.author
        channel = message.channel
        raw_content = message.content

        # 1. Xóa ngay tin nhắn
        try:
            await message.delete()
            logger.info(f'[AutoMod] Đã xóa tin nhắn chứa từ cấm "{word}" của {author} ({author.id}) tại #{channel}')
        except discord.Forbidden:
            logger.warning(f'[AutoMod] Thiếu quyền Manage Messages để xóa tin nhắn vi phạm của {author}')
            return
        except discord.NotFound:
            return

        # 2. Xử lý phạt theo Phương Án 1 (Bậc thang trừ điểm Daily)
        strike_num = 1
        penalty_pts = 0.0
        remaining_pts = 0.0
        penalty_msg = ""

        if economy_db:
            try:
                strike_num, penalty_pts, remaining_pts = economy_db.apply_profanity_penalty(
                    user_id=author.id,
                    guild_id=message.guild.id,
                    word=word
                )
                if strike_num == 1:
                    penalty_msg = "\n⚠️ **Cảnh cáo lần 1:** Hãy giữ gìn văn hóa trò chuyện (Chưa trừ điểm)."
                else:
                    penalty_msg = f"\n💸 **Vi phạm lần {strike_num}:** Bị phạt trừ **-{penalty_pts:.0f} Điểm** (-{int(penalty_pts * 1000):,} VNĐ)!\n💰 Số dư còn lại: `{remaining_pts:.1f} Điểm`."
            except Exception as e:
                logger.error(f"Lỗi khi trừ điểm vi phạm: {e}")

        # Gửi cảnh báo tạm thời cho người vi phạm (tự biến mất sau 7 giây)
        try:
            warning = await channel.send(
                f'🛑 {author.mention}, tin nhắn của bạn đã bị gỡ bỏ do vi phạm quy tắc ngôn từ của **High Ego eSport**.{penalty_msg}'
            )
            await asyncio.sleep(7)
            await warning.delete()
        except Exception:
            pass

        # 3. Ghi log vào kênh mod nếu có cấu hình
        if LOG_CHANNEL_ID:
            log_chan = message.guild.get_channel(LOG_CHANNEL_ID)
            if log_chan:
                embed = discord.Embed(
                    title=f'🚨 Cảnh Báo Ngôn Từ (Lần {strike_num})',
                    color=COLOR_RED,
                    timestamp=datetime.now()
                )
                embed.add_field(name='Người gửi', value=f'{author.mention} (`{author.id}`)', inline=True)
                embed.add_field(name='Kênh', value=channel.mention, inline=True)
                embed.add_field(name='Từ phát hiện', value=f'`{word}`', inline=True)
                embed.add_field(name='Hình phạt', value=f'Trừ `{penalty_pts:.0f} Điểm` (Còn `{remaining_pts:.1f}` Điểm)', inline=True)
                embed.add_field(name='Nội dung gốc', value=f'```{raw_content[:900]}```', inline=False)
                embed.set_footer(text='HEe • Sentinel AutoMod & Economy')
                try:
                    await log_chan.send(embed=embed)
                except Exception:
                    pass

    await bot.process_commands(message)

# ─────────────────── SỰ KIỆN 2: ROLE HE / ADMIN THẢ TICK XANH XÓA TIN NHẮN ──
@bot.event
async def on_raw_reaction_add(payload: discord.RawReactionActionEvent):
    if not payload.guild_id or payload.guild_id != GUILD_ID:
        return

    # Chấp nhận mọi biến thể của tick: ✅, ✔️, ☑️, custom tick emoji
    emoji_name = str(payload.emoji.name).lower()
    is_tick = (
        payload.emoji.name in ('✅', '✔️', '☑️')
        or emoji_name in ('white_check_mark', 'heavy_check_mark', 'ballot_box_with_check', 'tick', 'check')
        or 'check' in emoji_name
        or 'tick' in emoji_name
    )
    if not is_tick:
        return

    guild = bot.get_guild(payload.guild_id)
    if not guild:
        return

    # Lấy thông tin member (tự fallback nếu payload.member bị None trên Discord Gateway)
    member = payload.member
    if not member:
        member = guild.get_member(payload.user_id)
    if not member:
        try:
            member = await guild.fetch_member(payload.user_id)
        except Exception:
            return

    if member.bot:
        return

    # Kiểm tra xem người thả có Role HE, Admin, Manage Messages hoặc là Owner không
    if not has_he_role(member):
        logger.info(f'[QuickDelete] Bỏ qua vì {member} không có quyền xóa tin nhắn.')
        return

    # Lấy channel an toàn (hỗ trợ cả thread, voice text...)
    channel = bot.get_channel(payload.channel_id)
    if not channel:
        try:
            channel = await bot.fetch_channel(payload.channel_id)
        except Exception:
            return

    try:
        target_message = await channel.fetch_message(payload.message_id)
    except (discord.NotFound, discord.Forbidden):
        return

    logger.info(f'[QuickDelete] {member} đã thả tick ({payload.emoji.name}) vào tin nhắn của {target_message.author}. Xóa sau 1s...')

    # Báo phản hồi bằng reaction đồng hồ cát ⏳
    try:
        await target_message.add_reaction('⏳')
    except Exception:
        pass

    # Đợi 1 giây để người dùng thấy phản hồi
    await asyncio.sleep(1)

    # Thực hiện xóa tin nhắn
    try:
        await target_message.delete()
        logger.info(f'[QuickDelete] Đã xóa thành công tin nhắn {payload.message_id}.')
    except (discord.NotFound, discord.Forbidden) as e:
        logger.warning(f'[QuickDelete] Không thể xóa tin nhắn: {e}')

# ─────────────────── SỰ KIỆN 3: BẮT TOÀN BỘ LỖI COMMAND & LOGS ────────────
@bot.tree.error
async def on_app_command_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    # Unwrap exception gốc nếu có
    actual_error = getattr(error, 'original', error)
    cmd_name = interaction.command.name if interaction.command else "unknown"
    
    # Ghi nhận log vào file
    err_id = error_logger.record_error(
        command_name=cmd_name,
        user_name=str(interaction.user),
        user_id=interaction.user.id,
        guild_id=interaction.guild_id,
        channel_id=interaction.channel_id,
        error=actual_error
    )
    
    logger.error(f'[CommandError] Lệnh /{cmd_name} bị lỗi (ID: {err_id}): {actual_error}')

    # Trả lời người dùng lịch sự kèm mã lỗi
    msg = f'❌ Đã xảy ra sự cố khi thực thi lệnh `/{cmd_name}`. Mã lỗi: `{err_id}`. Đã được ghi nhận vào hệ thống logs.'
    if interaction.response.is_done():
        await interaction.followup.send(msg, ephemeral=True)
    else:
        await interaction.response.send_message(msg, ephemeral=True)

# ─────────────────────────── SLASH COMMANDS CỦA BOT ───────────────────────

@bot.tree.command(name='debug-logs', description='[Role HE / Admin] Đọc các dòng log lỗi command mới nhất')
@app_commands.describe(so_dong='Số dòng log muốn xem (mặc định: 30, tối đa: 80)')
async def cmd_debug_logs(interaction: discord.Interaction, so_dong: int = 30):
    member = interaction.user
    if not isinstance(member, discord.Member) or not has_he_role(member):
        await interaction.response.send_message('❌ Bạn phải có role **HE** hoặc **Admin** mới được dùng lệnh này!', ephemeral=True)
        return

    limit = max(10, min(so_dong, 80))
    logs_content = error_logger.get_recent_logs(limit)

    # Chia đoạn nếu log dài quá 1900 ký tự (giới hạn Discord)
    if len(logs_content) > 1900:
        logs_content = logs_content[-1900:]

    embed = discord.Embed(
        title=f'📋 Command Error Logs (Gần nhất)',
        description=f'```{logs_content}```',
        color=COLOR_RED,
        timestamp=datetime.now()
    )
    embed.set_footer(text='HEe • Sentinel Debugger')
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name='clear-logs', description='[Admin] Xóa sạch toàn bộ file logs lỗi hiện tại')
async def cmd_clear_logs(interaction: discord.Interaction):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message('❌ Chỉ **Administrator** mới được xóa file logs!', ephemeral=True)
        return

    success = error_logger.clear_logs()
    if success:
        await interaction.response.send_message('🧹 Đã dọn dẹp sạch toàn bộ file logs lỗi!', ephemeral=True)
    else:
        await interaction.response.send_message('❌ Không thể dọn dẹp file logs.', ephemeral=True)

@bot.tree.command(name='strike-reset', description='[Role HE / Admin] Reset số lần vi phạm ngôn từ của thành viên về 0')
@app_commands.describe(
    thanh_vien='Thành viên muốn xóa số lần vi phạm',
    ly_do='Lý do xóa vi phạm (mặc định: Đã kiểm điểm / BQT Ân xá)'
)
async def cmd_strike_reset(
    interaction: discord.Interaction,
    thanh_vien: discord.Member,
    ly_do: str = "Đã kiểm điểm / BQT Ân xá"
):
    member = interaction.user
    if not isinstance(member, discord.Member) or not has_he_role(member):
        await interaction.response.send_message('❌ Bạn phải có role **HE** hoặc **Admin** mới được dùng lệnh này!', ephemeral=True)
        return

    if not economy_db:
        await interaction.response.send_message('❌ Không tìm thấy database kinh tế `economy_db`!', ephemeral=True)
        return

    try:
        economy_db.reset_user_account(
            user_id=thanh_vien.id,
            guild_id=interaction.guild_id,
            reset_points=False,
            reset_strikes=True,
            reason=ly_do,
            operator_id=member.id
        )

        embed = discord.Embed(
            title='🕊️ ÂN XÁ / RESET VI PHẠM THÀNH CÔNG',
            description=(
                f'Toàn bộ số lần cảnh cáo & vi phạm của {thanh_vien.mention} đã được đưa về **0 lần**!\n\n'
                f'👤 **Thành viên:** {thanh_vien.mention} (`{thanh_vien.id}`)\n'
                f'👑 **Người thực hiện:** {member.mention}\n'
                f'📝 **Lý do:** {ly_do}\n'
                f'💡 *Thành viên này hiện đã có lịch sử trong sạch để tiếp tục sinh hoạt.*'
            ),
            color=0x10B981,
            timestamp=datetime.now()
        )
        embed.set_footer(text='HEe • Sentinel AutoMod & Justice System')
        await interaction.response.send_message(embed=embed)

        # Gửi log mod
        if LOG_CHANNEL_ID:
            log_chan = interaction.guild.get_channel(LOG_CHANNEL_ID)
            if log_chan:
                try:
                    await log_chan.send(embed=embed)
                except Exception:
                    pass

    except Exception as e:
        logger.error(f"Lỗi khi reset strike cho {thanh_vien.id}: {e}")
        await interaction.response.send_message(f'❌ Đã có lỗi xảy ra khi reset vi phạm: {e}', ephemeral=True)

# ─────────────────────────── Khởi động ───────────────────────────────────
if __name__ == '__main__':
    if not BOT_TOKEN:
        logger.error('BOT_TOKEN chưa được cài đặt trong .env! Vui lòng kiểm tra lại.')
        sys.exit(1)
    if not GUILD_ID:
        logger.error('GUILD_ID chưa được cài đặt trong .env!')
        sys.exit(1)
    bot.run(BOT_TOKEN, log_handler=None)
