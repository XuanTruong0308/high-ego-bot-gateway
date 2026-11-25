"""
bot.py — HEe • Bounty (P6 - Giveaway Bot chống clone & tích hợp Vault)
1. Tổ chức Giveaway chuyên nghiệp bằng Slash Command.
2. Bộ lọc Anti-Clone nghiêm ngặt: Tuổi tài khoản, thời gian trong server, Level rank (Chronicle).
3. Tùy chọn trao giải bằng Điểm Vault: Tự động cộng tiền vào ví economy.db cho người thắng.
4. Nút bấm tương tác cập nhật lượt tham gia realtime, chống nick ảo bấm nhận quà.
"""

import os
import re
import sys
import random
import logging
import sqlite3
import asyncio
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional, List

import discord
from discord import app_commands
from discord.ext import commands, tasks
from dotenv import load_dotenv

BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"

# Tích hợp database shared economy và giveaway
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "shared_data")))
try:
    import economy_db
except ImportError:
    economy_db = None

import giveaway_db

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
logger = logging.getLogger('HEe.Bounty')

BOT_TOKEN        = os.getenv('BOT_TOKEN', '')
GUILD_ID         = int(os.getenv('GUILD_ID', '0'))
HE_ROLE_NAME     = os.getenv('HE_ROLE_NAME', 'HE')
OWNER_USER_ID    = os.getenv('OWNER_USER_ID', '1147375213634388008')
GIVEAWAY_CHANNEL_ID = int(os.getenv('GIVEAWAY_CHANNEL_ID', '0'))
AUDIT_LOG_ID     = int(os.getenv('AUDIT_LOG_CHANNEL_ID', '0'))

COLOR_RED   = 0xE11D48
COLOR_DARK  = 0x881337
COLOR_ENDED = 0x4B5563

intents = discord.Intents.default()

def check_channel_allowed(interaction: discord.Interaction) -> tuple[bool, str]:
    """Chỉ định bot giveaway chỉ được nhắn / gọi tại đúng 1 kênh duy nhất."""
    if GIVEAWAY_CHANNEL_ID and interaction.channel_id != GIVEAWAY_CHANNEL_ID:
        return False, f"❌ Bot Giveaway chỉ được phép hoạt động tại kênh <#{GIVEAWAY_CHANNEL_ID}>!"
    return True, ""

def is_authorized(member: discord.Member) -> bool:
    """Quyền Admin / Role HE / Founder"""
    if str(member.id) == OWNER_USER_ID or member.id == 1147375213634388008:
        return True
    if member.guild_permissions.administrator:
        return True
    return any(r.name == HE_ROLE_NAME or str(r.id) == HE_ROLE_NAME for r in member.roles)

def parse_duration(duration_str: str) -> Optional[int]:
    """Chuyển đổi chuỗi 10m, 2h, 1d thành số giây"""
    match = re.match(r"^(\d+)([smhd])$", duration_str.strip().lower())
    if not match:
        return None
    val, unit = int(match.group(1)), match.group(2)
    multipliers = {'s': 1, 'm': 60, 'h': 3600, 'd': 86400}
    return val * multipliers[unit]

def get_user_rank_level(user_id: int, guild_id: int) -> int:
    """Đọc rank level từ rank.db của bot Chronicle"""
    rank_paths = [
        Path('/rank_data/rank.db'),
        Path(__file__).parent.parent / 'hee_rank' / 'data' / 'rank.db',
    ]
    db_file = next((p for p in rank_paths if p.exists()), None)
    if not db_file:
        return 0
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
                # Quy đổi 100 XP = 1 Level (Đồng bộ với Vault)
                lvl = max(0, int(xp // 100))
                return lvl
    except Exception as e:
        logger.warning(f"Lỗi đọc level rank: {e}")
    return 0

def check_anti_clone(
    member: discord.Member,
    min_level: int,
    min_acc_days: int,
    min_server_hours: int,
    required_role_id: Optional[str]
) -> tuple[bool, str]:
    now_utc = datetime.now(timezone.utc)

    # 1. Tuổi tài khoản Discord
    if member.created_at and min_acc_days > 0:
        age_days = (now_utc - member.created_at).days
        if age_days < min_acc_days:
            return False, f"Tài khoản Discord của bạn mới lập được **{age_days} ngày** (Yêu cầu: tối thiểu **{min_acc_days} ngày** để chống clone)."

    # 2. Thời gian tham gia Server
    if member.joined_at and min_server_hours > 0:
        join_hours = (now_utc - member.joined_at).total_seconds() / 3600
        if join_hours < min_server_hours:
            remain = max(1, int(min_server_hours - join_hours))
            return False, f"Bạn cần tham gia server tối thiểu **{min_server_hours} giờ** (Còn thiếu khoảng {remain} giờ)."

    # 3. Yêu cầu Level từ Chronicle
    if min_level > 0:
        user_lvl = get_user_rank_level(member.id, member.guild.id)
        if user_lvl < min_level:
            return False, f"Yêu cầu đạt tối thiểu **Level {min_level}** trong server (Cấp hiện tại của bạn: **Level {user_lvl}**). Hãy chat/voice để tăng cấp!"

    # 4. Yêu cầu Role cụ thể
    if required_role_id:
        has_role = any(str(r.id) == str(required_role_id) for r in member.roles)
        if not has_role:
            return False, f"Bạn cần sở hữu Role <@&{required_role_id}> mới được tham gia Giveaway này."

    return True, ""

# ─────────────────── GIAO DIỆN NÚT BẤM GIVEAWAY ───────────────────
class GiveawayButtonView(discord.ui.View):
    def __init__(self, giveaway_id: int):
        super().__init__(timeout=None)
        self.giveaway_id = giveaway_id

        # Khởi tạo label với số lượng entries hiện tại
        count = giveaway_db.get_entry_count(giveaway_id)
        self.join_btn.label = f"🎉 Tham Gia ({count})"
        self.join_btn.custom_id = f"giveaway_btn_{giveaway_id}"

    @discord.ui.button(style=discord.ButtonStyle.primary, emoji="🎉")
    async def join_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        gw = giveaway_db.get_giveaway_by_message(interaction.message.id)
        if not gw or gw['status'] != 'running':
            await interaction.response.send_message("❌ Giveaway này đã kết thúc hoặc không còn khả dụng!", ephemeral=True)
            return

        member = interaction.user
        if not isinstance(member, discord.Member):
            return

        # Kiểm tra điều kiện Anti-Clone
        passed, reason = check_anti_clone(
            member=member,
            min_level=gw['min_level'],
            min_acc_days=gw['min_account_age_days'],
            min_server_hours=gw['min_server_stay_hours'],
            required_role_id=gw['required_role_id']
        )
        if not passed:
            await interaction.response.send_message(
                f"🛡️ **Không đủ điều kiện tham gia:**\n{reason}",
                ephemeral=True
            )
            return

        # Thêm hoặc Hủy tham gia
        is_joined, total_count = giveaway_db.toggle_entry(gw['id'], member.id)
        button.label = f"🎉 Tham Gia ({total_count})"
        await interaction.message.edit(view=self)

        if is_joined:
            await interaction.response.send_message(
                f"✅ **Tham gia thành công!** Bạn đã ghi danh vào Giveaway **{gw['prize']}**.\nChúc bạn may mắn trúng thưởng! 🍀",
                ephemeral=True
            )
        else:
            await interaction.response.send_message(
                f"ℹ️ Bạn đã **hủy tham gia** Giveaway **{gw['prize']}**.",
                ephemeral=True
            )

# ─────────────────── LỚP BOT BOUNTY ───────────────────
class BountyBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix='!', intents=intents)

    async def setup_hook(self):
        giveaway_db.init_db()
        logger.info('Database Giveaway khởi tạo thành công.')

        # Khôi phục persistent views cho các giveaway đang chạy
        active_gws = giveaway_db.get_active_giveaways()
        for gw in active_gws:
            self.add_view(GiveawayButtonView(gw['id']))
        logger.info(f'Đã nạp lại {len(active_gws)} giveaway đang diễn ra.')

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
        if not self.check_giveaways.is_running():
            self.check_giveaways.start()

    @tasks.loop(seconds=15)
    async def check_giveaways(self):
        now = datetime.now(timezone.utc).timestamp()
        active_gws = giveaway_db.get_active_giveaways()

        for gw in active_gws:
            if gw['end_time'] <= now:
                await self.resolve_giveaway(gw)

    async def resolve_giveaway(self, gw: dict):
        channel = self.get_channel(int(gw['channel_id']))
        if not channel:
            return

        try:
            msg = await channel.fetch_message(int(gw['message_id']))
        except Exception:
            msg = None

        entries = giveaway_db.get_entries(gw['id'])
        winner_count = min(gw['winner_count'], len(entries)) if entries else 0
        winners = random.sample(entries, winner_count) if winner_count > 0 else []

        giveaway_db.end_giveaway(gw['id'], winners)

        if winners:
            winners_mentions = ", ".join(f"<@{w}>" for w in winners)
            embed_desc = (
                f"🏆 **Giải thưởng:** **{gw['prize']}**\n"
                f"👤 **Người tổ chức:** <@{gw['host_id']}>\n"
                f"👥 **Tổng người tham gia hợp lệ:** `{len(entries)} người`\n\n"
                f"🎉 **Chúc mừng người chiến thắng:**\n{winners_mentions}"
            )

            # Tự động cộng điểm vào ví Vault nếu có cấu hình
            if gw['is_vault_points'] and gw['vault_points_amount'] > 0 and economy_db:
                pts = gw['vault_points_amount']
                for w_id in winners:
                    try:
                        economy_db.add_points_admin(
                            user_id=w_id,
                            guild_id=int(gw['guild_id']),
                            amount=pts,
                            reason=f"Thắng Giveaway: {gw['prize']}",
                            operator_id=self.user.id
                        )
                    except Exception as e:
                        logger.error(f"Lỗi tự động cộng điểm Vault cho {w_id}: {e}")
                embed_desc += f"\n\n💰 *Đã tự động cộng `{pts:.1f} Điểm` ({int(pts * 1000):,} VNĐ) vào ví Vault cho mỗi người thắng!*"
        else:
            embed_desc = (
                f"🏆 **Giải thưởng:** **{gw['prize']}**\n"
                f"👤 **Người tổ chức:** <@{gw['host_id']}>\n\n"
                f"❌ **Không có người chiến thắng hợp lệ** (Không có thành viên tham gia hoặc không đủ điều kiện anti-clone)."
            )

        embed = discord.Embed(
            title="🎁 KẾT QUẢ GIVEAWAY — HEe BOUNTY",
            description=embed_desc,
            color=COLOR_ENDED,
            timestamp=datetime.now()
        )
        embed.set_footer(text="Giveaway đã kết thúc • High Ego eSport")

        if msg:
            # Disable button
            disabled_view = discord.ui.View()
            btn = discord.ui.Button(style=discord.ButtonStyle.secondary, label=f"Đã Kết Thúc ({len(entries)})", disabled=True, emoji="🔒")
            disabled_view.add_item(btn)
            await msg.edit(embed=embed, view=disabled_view)

        # Thông báo ping người thắng trong kênh
        if winners:
            await channel.send(f"🎊 Chúc mừng {winners_mentions} đã trúng **{gw['prize']}**! Hãy kiểm tra quà hoặc liên hệ ban quản trị.")
        else:
            await channel.send(f"⚠️ Giveaway **{gw['prize']}** đã kết thúc mà không có ai trúng thưởng.")

bot = BountyBot()

# ─────────────────── SLASH COMMANDS ───────────────────
@bot.tree.command(name='giveaway-start', description='[Role HE / Admin] Khởi tạo Giveaway với hệ thống chống Clone')
@app_commands.describe(
    giai_thuong='Tên phần quà (VD: 50k VNĐ, Thẻ Garena 100k, Nitro)',
    thoi_gian='Thời gian đếm ngược (VD: 10m, 2h, 24h, 3d)',
    so_nguoi_trung='Số lượng người trúng giải (mặc định: 1)',
    level_yeu_cau='Level Rank tối thiểu từ bot Chronicle (mặc định: 0)',
    tuoi_acc_ngay='Tuổi tài khoản Discord tối thiểu (mặc định: 90 ngày / 3 tháng)',
    gio_vao_server='Thời gian tối thiểu ở trong server (mặc định: 0 - không bắt buộc)',
    role_yeu_cau='Role bắt buộc phải có để tham gia',
    thuong_diem_vault='Số Điểm Vault tự động cộng thẳng vào ví người thắng (0 nếu là quà ngoài)'
)
async def cmd_giveaway_start(
    interaction: discord.Interaction,
    giai_thuong: str,
    thoi_gian: str,
    so_nguoi_trung: int = 1,
    level_yeu_cau: int = 0,
    tuoi_acc_ngay: int = 90,
    gio_vao_server: int = 0,
    role_yeu_cau: Optional[discord.Role] = None,
    thuong_diem_vault: float = 0.0
):
    allowed, ch_msg = check_channel_allowed(interaction)
    if not allowed:
        await interaction.response.send_message(ch_msg, ephemeral=True)
        return

    member = interaction.user
    if not isinstance(member, discord.Member) or not is_authorized(member):
        await interaction.response.send_message('❌ Chỉ có **Role HE** hoặc là **Administrator** mới được tạo Giveaway!', ephemeral=True)
        return

    seconds = parse_duration(thoi_gian)
    if not seconds or seconds < 30:
        await interaction.response.send_message('❌ Định dạng thời gian không hợp lệ! Hãy nhập dạng `10m`, `2h`, `24h` hoặc `3d` (Tối thiểu 30 giây).', ephemeral=True)
        return

    if GIVEAWAY_CHANNEL_ID:
        target_channel = interaction.guild.get_channel(GIVEAWAY_CHANNEL_ID) or interaction.channel
    else:
        target_channel = interaction.channel
    end_dt = datetime.now(timezone.utc) + timedelta(seconds=seconds)
    end_timestamp = int(end_dt.timestamp())

    # Soạn điều kiện chống clone
    req_list = []
    if tuoi_acc_ngay > 0:
        req_list.append(f"- 🛡️ Nick Discord tạo tối thiểu: **{tuoi_acc_ngay} ngày**")
    if gio_vao_server > 0:
        req_list.append(f"- ⏳ Tham gia server ít nhất: **{gio_vao_server} giờ**")
    if level_yeu_cau > 0:
        req_list.append(f"- 💬 Đạt tối thiểu: **Level {level_yeu_cau}** (Bot Chronicle)")
    if role_yeu_cau:
        req_list.append(f"- 🏷️ Yêu cầu Role: {role_yeu_cau.mention}")
    if thuong_diem_vault > 0:
        req_list.append(f"- 💰 Phần thưởng liên kết ví Vault: **+{thuong_diem_vault:.1f} Điểm** ({int(thuong_diem_vault * 1000):,} VNĐ)")

    req_str = "\n".join(req_list) if req_list else "- *Mọi thành viên đều có thể tham gia.*"

    embed = discord.Embed(
        title=f"🎉 GIVEAWAY: {giai_thuong.upper()}",
        description=(
            f"Bấm vào nút **Tham Gia** bên dưới để có cơ hội nhận quà!\n\n"
            f"🎁 **Phần thưởng:** **{giai_thuong}**\n"
            f"🏆 **Số người thắng:** `{so_nguoi_trung} người`\n"
            f"👤 **Tổ chức bởi:** {member.mention}\n"
            f"⏰ **Kết thúc vào:** <t:{end_timestamp}:R> (<t:{end_timestamp}:f>)\n\n"
            f"🔒 **Điều Kiện Tham Gia (Anti-Clone):**\n{req_str}"
        ),
        color=COLOR_RED,
        timestamp=end_dt
    )
    embed.set_thumbnail(url=interaction.guild.icon.url if interaction.guild.icon else None)
    embed.set_footer(text="High Ego eSport • Hệ Thống Giveaway Chống Nick Ảo")

    await interaction.response.send_message(f"✅ Đang đăng tải Giveaway tại {target_channel.mention}...", ephemeral=True)

    # Gửi tin nhắn vào kênh và tạo record
    giveaway_msg = await target_channel.send(embed=embed)

    gw_id = giveaway_db.create_giveaway(
        message_id=giveaway_msg.id,
        channel_id=target_channel.id,
        guild_id=interaction.guild_id,
        prize=giai_thuong,
        winner_count=so_nguoi_trung,
        end_time=end_dt.timestamp(),
        host_id=member.id,
        min_level=level_yeu_cau,
        min_account_age_days=tuoi_acc_ngay,
        min_server_stay_hours=gio_vao_server,
        required_role_id=role_yeu_cau.id if role_yeu_cau else None,
        is_vault_points=1 if thuong_diem_vault > 0 else 0,
        vault_points_amount=thuong_diem_vault
    )

    view = GiveawayButtonView(gw_id)
    await giveaway_msg.edit(view=view)

@bot.tree.command(name='giveaway-reroll', description='[Role HE / Admin] Bốc thăm lại người chiến thắng mới cho Giveaway')
@app_commands.describe(tin_nhan_id='ID tin nhắn của Giveaway đã kết thúc')
async def cmd_giveaway_reroll(interaction: discord.Interaction, tin_nhan_id: str):
    allowed, ch_msg = check_channel_allowed(interaction)
    if not allowed:
        await interaction.response.send_message(ch_msg, ephemeral=True)
        return

    member = interaction.user
    if not isinstance(member, discord.Member) or not is_authorized(member):
        await interaction.response.send_message('❌ Bạn phải có **Role HE** hoặc là **Administrator** mới được reroll!', ephemeral=True)
        return

    try:
        msg_id = int(tin_nhan_id.strip())
    except ValueError:
        await interaction.response.send_message('❌ ID tin nhắn không hợp lệ! Vui lòng nhập số ID tin nhắn Discord.', ephemeral=True)
        return

    gw = giveaway_db.get_giveaway_by_message(msg_id)
    if not gw:
        await interaction.response.send_message('❌ Không tìm thấy Giveaway tương ứng trong cơ sở dữ liệu!', ephemeral=True)
        return

    if gw['status'] != 'ended':
        await interaction.response.send_message('❌ Giveaway này chưa kết thúc! Hãy dùng `/giveaway-end` nếu muốn dừng sớm.', ephemeral=True)
        return

    entries = giveaway_db.get_entries(gw['id'])
    if not entries:
        await interaction.response.send_message('❌ Giveaway này không có thành viên nào đăng ký tham gia!', ephemeral=True)
        return

    new_winner = random.choice(entries)
    await interaction.response.send_message(
        f"🎲 **Reroll Thành Công!**\nNgười chiến thắng mới của Giveaway **{gw['prize']}** là: <@{new_winner}>! 🎊"
    )

@bot.tree.command(name='giveaway-end', description='[Role HE / Admin] Kết thúc và quay số Giveaway ngay lập tức')
@app_commands.describe(tin_nhan_id='ID tin nhắn của Giveaway cần dừng sớm')
async def cmd_giveaway_end(interaction: discord.Interaction, tin_nhan_id: str):
    allowed, ch_msg = check_channel_allowed(interaction)
    if not allowed:
        await interaction.response.send_message(ch_msg, ephemeral=True)
        return

    member = interaction.user
    if not isinstance(member, discord.Member) or not is_authorized(member):
        await interaction.response.send_message('❌ Bạn phải có **Role HE** hoặc là **Administrator** mới được dừng Giveaway!', ephemeral=True)
        return

    try:
        msg_id = int(tin_nhan_id.strip())
    except ValueError:
        await interaction.response.send_message('❌ ID tin nhắn không hợp lệ!', ephemeral=True)
        return

    gw = giveaway_db.get_giveaway_by_message(msg_id)
    if not gw or gw['status'] != 'running':
        await interaction.response.send_message('❌ Giveaway này không tồn tại hoặc đã kết thúc từ trước!', ephemeral=True)
        return

    await interaction.response.send_message('⏳ Đang tiến hành kết thúc và quay thưởng sớm...', ephemeral=True)
    await bot.resolve_giveaway(gw)

if __name__ == '__main__':
    if not BOT_TOKEN:
        logger.error('BOT_TOKEN chưa cài đặt!')
        sys.exit(1)
    if not GUILD_ID:
        logger.error('GUILD_ID chưa cài đặt!')
        sys.exit(1)
    bot.run(BOT_TOKEN, log_handler=None)
