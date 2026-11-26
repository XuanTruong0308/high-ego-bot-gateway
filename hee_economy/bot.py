"""
bot.py — HEe • Vault (P5 - Economy & Daily Bot)
1. Lệnh /daily nhận 1 điểm / ngày (= 1k VNĐ).
2. Lệnh /balance xem số dư điểm và số lần cảnh cáo vi phạm.
3. Lệnh /point-add dành riêng cho Role HE / Admin để cộng/trừ điểm (bắt buộc nhập reason).
4. Giới hạn quy đổi: Min 50 điểm (50k) - Max 100 điểm (100k).
"""

import os
import sys
import logging
import sqlite3
from datetime import datetime, timezone

import discord
from discord import app_commands
from discord.ext import commands
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).parent
ASSETS_DIR = BASE_DIR / "assets"
EVENT_BANNER_GIF = ASSETS_DIR / "event_banner.gif"

# Thêm đường dẫn shared_data
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "shared_data")))
import economy_db

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
logger = logging.getLogger('HEe.Vault')

BOT_TOKEN        = os.getenv('BOT_TOKEN', '')
GUILD_ID         = int(os.getenv('GUILD_ID', '0'))
HE_ROLE_NAME     = os.getenv('HE_ROLE_NAME', 'HE')
OWNER_USER_ID    = os.getenv('OWNER_USER_ID', '1147375213634388008')
DAILY_CHANNEL_ID = int(os.getenv('DAILY_CHANNEL_ID', '0'))
AUDIT_LOG_ID     = int(os.getenv('AUDIT_LOG_CHANNEL_ID', '0'))

COLOR_RED  = 0xE11D48
COLOR_DARK = 0x881337

intents = discord.Intents.default()

def is_founder(member: discord.Member) -> bool:
    """Chỉ duy nhất Founder (ID bạn hoặc Server Owner) mới được phép thực thi."""
    if str(member.id) == OWNER_USER_ID or member.id == 1147375213634388008:
        return True
    if member.guild and member.guild.owner_id == member.id:
        return True
    return False

def has_he_role(member: discord.Member) -> bool:
    if member.guild_permissions.administrator:
        return True
    return any(r.name == HE_ROLE_NAME or str(r.id) == HE_ROLE_NAME for r in member.roles)

def get_user_rank_level(user_id: int, guild_id: int) -> tuple[float, int]:
    """Trả về (xp, level) từ rank.db của bot Chronicle. Level = int(xp // 100)"""
    rank_paths = [
        Path('/rank_data/rank.db'),
        Path(__file__).parent.parent / 'hee_rank' / 'data' / 'rank.db',
    ]
    db_file = next((p for p in rank_paths if p.exists()), None)
    if not db_file:
        return 0.0, 0
    try:
        with sqlite3.connect(db_file) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT xp FROM members WHERE user_id = ? AND guild_id = ?",
                (str(user_id), str(guild_id))
            )
            row = cursor.fetchone()
            if row:
                xp = float(row[0])
                level = max(0, int(xp // 100))
                return xp, level
    except Exception as e:
        logger.warning(f"Lỗi đọc level rank: {e}")
    return 0.0, 0

class VaultBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix='!', intents=intents)

    async def setup_hook(self):
        economy_db.init_db()
        logger.info('Database Economy dùng chung khởi tạo thành công.')

        guild = discord.Object(id=GUILD_ID)
        self.tree.copy_global_to(guild=guild)
        try:
            synced = await self.tree.sync(guild=guild)
            logger.info(f'Synced {len(synced)} slash command(s) vào guild {GUILD_ID}.')
        except discord.Forbidden:
            synced = await self.tree.sync()
            logger.info(f'Synced {len(synced)} global slash command(s).')

    async def on_ready(self):
        logger.info(f'Logged in as {self.user} (ID: {self.user.id})')

bot = VaultBot()

@bot.tree.command(name='daily', description='Điểm danh nhận 1 Điểm thưởng (= 1,000 VNĐ) mỗi ngày')
async def cmd_daily(interaction: discord.Interaction):
    # Kiểm tra kênh chỉ định nếu có cấu hình
    if DAILY_CHANNEL_ID and interaction.channel_id != DAILY_CHANNEL_ID:
        await interaction.response.send_message(
            f'❌ Bạn chỉ có thể điểm danh tại kênh <#{DAILY_CHANNEL_ID}>!', ephemeral=True
        )
        return

    success, msg, new_balance = economy_db.claim_daily(interaction.user.id, interaction.guild_id)
    if not success:
        await interaction.response.send_message(f'⏳ {interaction.user.mention}, {msg}', ephemeral=True)
        return

    embed = discord.Embed(
        title='🎁 Điểm Danh Hằng Ngày — HEe Vault',
        description=(
            f'Chúc mừng {interaction.user.mention}!\n'
            f'{msg}\n\n'
            f'💰 **Số dư hiện tại:** `{new_balance:.1f} Điểm` ({int(new_balance * 1000):,} VNĐ)\n'
            f'📌 *Điều kiện rút tiền: Tích lũy tối thiểu 50 Điểm (50k) và đạt tối thiểu **Rank Level 5** trong server.*'
        ),
        color=COLOR_RED,
        timestamp=datetime.now()
    )
    embed.set_thumbnail(url=interaction.user.display_avatar.url)
    embed.set_footer(text='High Ego eSport • Quỹ Thưởng Thành Viên')
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name='balance', description='Xem số dư điểm thưởng, cấp độ Rank và trạng thái rút tiền của bạn')
@app_commands.describe(thanh_vien='Thành viên muốn tra cứu (mặc định: chính bạn)')
async def cmd_balance(interaction: discord.Interaction, thanh_vien: discord.Member = None):
    target = thanh_vien or interaction.user
    user = economy_db.get_user(target.id, interaction.guild_id)
    points = user['points']
    strikes = user['strike_count']

    # Lấy Rank Level từ bot Chronicle
    xp, level = get_user_rank_level(target.id, interaction.guild_id)

    embed = discord.Embed(
        title=f'💳 Tài Khoản Thưởng — {target.display_name}',
        color=COLOR_RED,
        timestamp=datetime.now()
    )
    embed.set_thumbnail(url=target.display_avatar.url)
    embed.add_field(name='💰 Số Dư Điểm', value=f'**{points:.1f} Điểm**', inline=True)
    embed.add_field(name='💵 Quy Đổi VNĐ', value=f'**{int(points * 1000):,} VNĐ**', inline=True)
    embed.add_field(name='🎖️ Cấp Độ Rank', value=f'**Level {level}** (`{xp:,.0f} XP`)', inline=True)
    embed.add_field(name='⚠️ Cảnh Cáo Vi Phạm', value=f'{strikes} lần', inline=True)

    # Điều kiện rút tiền: Điểm >= 50 VÀ Level >= 5
    if points >= 50.0:
        if level >= 5:
            status_str = f"✅ **ĐỦ ĐIỀU KIỆN RÚT TIỀN!**\nBạn đã đạt `{points:.1f} Điểm` và Rank **Level {level}** (≥ Level 5). Hãy mở ticket hỗ trợ để nhận tiền mặt!"
        else:
            status_str = (
                f"🔒 **CHƯA ĐƯỢC PHÉP RÚT TIỀN:**\n"
                f"Bạn đã có đủ `{points:.1f} Điểm` nhưng Rank hiện tại mới đạt **Level {level}/5**.\n"
                f"👉 *Yêu cầu: Phải đạt tối thiểu **Rank Level 5** (tích cực chat & voice) mới được rút tiền!*"
            )
    else:
        remain_pts = 50.0 - points
        status_str = (
            f"⏳ **Chưa đủ điều kiện rút:**\n"
            f"- Cần thêm: `{remain_pts:.1f} Điểm` (Đạt tối thiểu 50k VNĐ)\n"
            f"- Yêu cầu Rank: **Level 5** (Hiện tại: `Level {level}/5`)"
        )

    embed.add_field(name='Trạng Thái Quy Đổi Tiền Mặt', value=status_str, inline=False)
    embed.set_footer(text='HEe Vault • 1 Điểm = 1,000 VNĐ • Điều kiện rút: Min 50 Điểm & Rank Level 5')
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name='point-add', description='[Founder Only] Cộng hoặc trừ điểm thành viên kèm lý do bắt buộc')
@app_commands.describe(
    thanh_vien='Thành viên cần điều chỉnh điểm',
    so_diem='Số điểm cần thay đổi (dương để cộng, âm để trừ)',
    ly_do='Lý do bắt buộc thực hiện giao dịch này'
)
async def cmd_point_add(interaction: discord.Interaction, thanh_vien: discord.Member, so_diem: float, ly_do: str):
    member = interaction.user
    if not isinstance(member, discord.Member) or not is_founder(member):
        await interaction.response.send_message('❌ Lệnh này được khóa độc quyền! Chỉ có **Chủ sở hữu server (Founder)** mới có quyền cấp/trừ điểm thưởng.', ephemeral=True)
        return

    if not ly_do or len(ly_do.strip()) < 3:
        await interaction.response.send_message('❌ Bạn **bắt buộc phải nhập lý do** rõ ràng khi cộng/trừ điểm!', ephemeral=True)
        return

    new_balance = economy_db.add_points_admin(
        user_id=thanh_vien.id,
        guild_id=interaction.guild_id,
        amount=so_diem,
        reason=ly_do.strip(),
        operator_id=member.id
    )

    sign = '+' if so_diem >= 0 else ''
    embed = discord.Embed(
        title='📝 Điều Chỉnh Điểm Thành Công',
        description=(
            f'**Người nhận:** {thanh_vien.mention}\n'
            f'**Thay đổi:** `{sign}{so_diem:.1f} Điểm` ({int(so_diem * 1000):,} VNĐ)\n'
            f'**Số dư mới:** `{new_balance:.1f} Điểm`\n'
            f'**Lý do:** {ly_do}\n'
            f'**Người thực hiện:** {member.mention} (Role HE)'
        ),
        color=COLOR_RED,
        timestamp=datetime.now()
    )
    await interaction.response.send_message(embed=embed)

    # Gửi log kiểm toán
    if AUDIT_LOG_ID:
        log_chan = interaction.guild.get_channel(AUDIT_LOG_ID)
        if log_chan:
            await log_chan.send(embed=embed)

# ─────────────────── MODAL TẠO THÔNG BÁO SỰ KIỆN ───────────────────
class EventAnnounceModal(discord.ui.Modal, title='Soạn Thông Báo Sự Kiện HEe'):
    event_title = discord.ui.TextInput(
        label='Tiêu đề sự kiện',
        placeholder='Ví dụ: GIẢI ĐẤU CUSTOM SQUAD SCRIM #01',
        max_length=100,
        required=True
    )
    event_content = discord.ui.TextInput(
        label='Nội dung, thể lệ, phần thưởng',
        style=discord.TextStyle.paragraph,
        placeholder='Xuống dòng thoải mái, viết thể lệ, danh sách luật:\n- Thể thức: Squad 4\n- Thời gian: 20h00 tối nay\n- Giải thưởng: 500k VNĐ',
        max_length=2000,
        required=True
    )

    def __init__(self, target_channel: discord.TextChannel):
        super().__init__()
        self.target_channel = target_channel

    async def on_submit(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title=f'🌟 {self.event_title.value.strip().upper()}',
            description=self.event_content.value.strip(),
            color=COLOR_RED,
            timestamp=datetime.now()
        )
        embed.set_author(
            name=f'Sự Kiện — {interaction.guild.name}',
            icon_url=interaction.guild.icon.url if interaction.guild.icon else None
        )
        embed.set_footer(
            text=f'Thông báo bởi {interaction.user.display_name} • High Ego eSport',
            icon_url=interaction.user.display_avatar.url
        )

        if EVENT_BANNER_GIF.exists():
            file = discord.File(str(EVENT_BANNER_GIF), filename="event_banner.gif")
            embed.set_image(url="attachment://event_banner.gif")
            await self.target_channel.send(content='@everyone', embed=embed, file=file)
        else:
            await self.target_channel.send(content='@everyone', embed=embed)

        await interaction.response.send_message(
            f'✅ Đã phát thông báo sự kiện thành công tại {self.target_channel.mention}!',
            ephemeral=True
        )

@bot.tree.command(name='event-announce', description='[Role HE / Admin] Mở bảng soạn thảo thông báo sự kiện @everyone kèm Banner GIF')
@app_commands.describe(
    kenh_thong_bao='Kênh muốn gửi thông báo (mặc định: kênh hiện tại)'
)
async def cmd_event_announce(
    interaction: discord.Interaction,
    kenh_thong_bao: discord.TextChannel = None
):
    member = interaction.user
    if not isinstance(member, discord.Member) or not has_he_role(member):
        await interaction.response.send_message('❌ Chỉ có **Role HE** hoặc là **Administrator** mới được đăng thông báo sự kiện!', ephemeral=True)
        return

    target_channel = kenh_thong_bao or interaction.channel
    modal = EventAnnounceModal(target_channel=target_channel)
    await interaction.response.send_modal(modal)

@bot.tree.command(name='point-reset', description='[Founder Only] Đưa điểm hoặc số lần vi phạm của thành viên về 0')
@app_commands.describe(
    thanh_vien='Thành viên cần reset',
    loai_reset='Chọn mục muốn reset về 0',
    ly_do='Lý do thực hiện reset'
)
@app_commands.choices(
    loai_reset=[
        app_commands.Choice(name='Reset cả Điểm và Vi Phạm về 0', value='both'),
        app_commands.Choice(name='Chỉ Reset Điểm về 0', value='points'),
        app_commands.Choice(name='Chỉ Xóa Lịch Sử Vi Phạm (0 Strike)', value='strikes'),
    ]
)
async def cmd_point_reset(interaction: discord.Interaction, thanh_vien: discord.Member, loai_reset: str, ly_do: str):
    member = interaction.user
    if not isinstance(member, discord.Member) or not is_founder(member):
        await interaction.response.send_message('❌ Lệnh này được khóa độc quyền! Chỉ có **Chủ sở hữu server (Founder)** mới có quyền reset điểm hoặc xóa lịch sử vi phạm.', ephemeral=True)
        return

    if not ly_do or len(ly_do.strip()) < 3:
        await interaction.response.send_message('❌ Bạn **bắt buộc phải nhập lý do** khi reset dữ liệu thành viên!', ephemeral=True)
        return

    reset_pts = loai_reset in ('both', 'points')
    reset_strk = loai_reset in ('both', 'strikes')

    economy_db.reset_user_account(
        user_id=thanh_vien.id,
        guild_id=interaction.guild_id,
        reset_points=reset_pts,
        reset_strikes=reset_strk,
        reason=ly_do.strip(),
        operator_id=member.id
    )

    desc_map = {
        'both': 'Đã đưa **Điểm thưởng về 0** và **Xóa sạch lịch sử vi phạm**!',
        'points': 'Đã đưa **Điểm thưởng về 0** (Giữ nguyên vi phạm)!',
        'strikes': 'Đã **Xóa sạch lịch sử vi phạm về 0** (Ân xá cảnh cáo)!'
    }

    embed = discord.Embed(
        title='🔄 Reset Dữ Liệu Thành Viên Thành Công',
        description=(
            f'**Thành viên:** {thanh_vien.mention}\n'
            f'**Thao tác:** {desc_map.get(loai_reset)}\n'
            f'**Lý do:** {ly_do}\n'
            f'**Thực hiện bởi:** {member.mention} (Role HE)'
        ),
        color=COLOR_RED,
        timestamp=datetime.now()
    )
    await interaction.response.send_message(embed=embed)

    if AUDIT_LOG_ID:
        log_chan = interaction.guild.get_channel(AUDIT_LOG_ID)
        if log_chan:
            await log_chan.send(embed=embed)

if __name__ == '__main__':
    if not BOT_TOKEN:
        logger.error('BOT_TOKEN chưa cài đặt!')
        sys.exit(1)
    if not GUILD_ID:
        logger.error('GUILD_ID chưa cài đặt!')
        sys.exit(1)
    bot.run(BOT_TOKEN, log_handler=None)
