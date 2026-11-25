"""
bot.py — HEe • Chronicle (P6)
Xếp hạng tương tác: message XP, reaction XP, voice time XP.
Slash commands: /rank, /leaderboard, /rank-info, /xp-add (admin)
"""

import os
import sys
import logging
import asyncio
import time

import discord
from discord import app_commands
from discord.ext import commands, tasks
from dotenv import load_dotenv

import db

load_dotenv()

# ─────────────────────────── Windows UTF-8 fix ───────────────────────────
try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')
except AttributeError:
    pass

# ─────────────────────────── Logging ─────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger('HEe.Chronicle')

# ─────────────────────────── Config từ .env ──────────────────────────────
BOT_TOKEN      = os.getenv('BOT_TOKEN', '')
GUILD_ID       = int(os.getenv('GUILD_ID', '0'))
XP_MSG         = float(os.getenv('XP_MSG', '1'))
XP_REACTION    = float(os.getenv('XP_REACTION', '0.5'))
XP_VOICE_MIN   = float(os.getenv('XP_VOICE_PER_MIN', '2'))
MSG_COOLDOWN   = int(os.getenv('MSG_COOLDOWN', '60'))      # giây
ADMIN_ROLE_NAME = os.getenv('ADMIN_ROLE_NAME', 'Admin')

# ─────────────────────────── Colors & Tiers ──────────────────────────────
COLOR_RED  = 0xE11D48
COLOR_DARK = 0x881337

TIERS = [
    {'name': '🔥 Legend',  'min': 50_000, 'max': float('inf'), 'color': 0xE11D48, 'short': 'Legend'},
    {'name': '💎 Diamond', 'min': 15_000, 'max': 49_999,       'color': 0x67E8F9, 'short': 'Diamond'},
    {'name': '👑 Gold',    'min': 5_000,  'max': 14_999,       'color': 0xFBBF24, 'short': 'Gold'},
    {'name': '🥈 Silver',  'min': 2_000,  'max': 4_999,        'color': 0xD1D5DB, 'short': 'Silver'},
    {'name': '🥉 Bronze',  'min': 500,    'max': 1_999,        'color': 0xB45309, 'short': 'Bronze'},
    {'name': '⚔️ Iron',   'min': 0,      'max': 499,          'color': 0x6B7280, 'short': 'Iron'},
]


def get_tier(xp: float) -> dict:
    for t in TIERS:
        if xp >= t['min']:
            return t
    return TIERS[-1]


def xp_bar(xp: float, tier: dict, length: int = 12) -> str:
    """Thanh tiến trình XP trong tier hiện tại."""
    t_min = tier['min']
    t_max = tier['max']
    if t_max == float('inf'):
        return '▓' * length  # Legend = max
    progress = max(0.0, min(1.0, (xp - t_min) / (t_max - t_min + 1)))
    filled = int(progress * length)
    return '▓' * filled + '░' * (length - filled)


def xp_to_next(xp: float, tier: dict) -> str:
    if tier['max'] == float('inf'):
        return '∞ (MAX)'
    remaining = tier['max'] + 1 - xp
    return f"{remaining:,.0f} XP"


# ─────────────────────────── Bot setup ───────────────────────────────────
intents = discord.Intents.default()
intents.members  = True
intents.messages = True
intents.message_content = True
intents.reactions = True
intents.voice_states = True
intents.presences = False


class Chronicle(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix='!', intents=intents)

    async def setup_hook(self):
        db.init_db()
        logger.info('SQLite DB khởi tạo thành công.')

        guild = discord.Object(id=GUILD_ID)
        self.tree.copy_global_to(guild=guild)
        try:
            synced = await self.tree.sync(guild=guild)
            logger.info(f'Synced {len(synced)} slash command(s) vào guild {GUILD_ID}.')
        except discord.Forbidden:
            logger.warning(f'Không thể sync guild {GUILD_ID} (403). Fallback sang global sync...')
            synced = await self.tree.sync()
            logger.info(f'Synced {len(synced)} global slash command(s).')

        # Khởi động task voice XP mỗi 1 phút
        self.flush_voice_loop.start()

    async def on_ready(self):
        guilds_str = ', '.join(f'{g.name} ({g.id})' for g in self.guilds)
        logger.info(f'Logged in as {self.user} (ID: {self.user.id})')
        logger.info(f'Connected to {len(self.guilds)} guild(s): {guilds_str}')
        if not any(g.id == GUILD_ID for g in self.guilds):
            logger.warning(f'Bot KHÔNG có mặt trong GUILD_ID={GUILD_ID} đã cấu hình trong .env!')

    # ─────────────────── XP Events ───────────────────────────────────────

    async def on_message(self, message: discord.Message):
        if message.author.bot or not message.guild:
            return
        if message.guild.id != GUILD_ID:
            return
        awarded = db.add_xp_message(
            message.author.id, message.guild.id,
            XP_MSG, MSG_COOLDOWN
        )
        if awarded:
            logger.debug(f'+{XP_MSG} XP (msg) → {message.author} | #{message.channel}')
        await self.process_commands(message)

    async def on_reaction_add(self, reaction: discord.Reaction, user: discord.User):
        if user.bot or not reaction.message.guild:
            return
        if reaction.message.guild.id != GUILD_ID:
            return
        # Chỉ cộng XP cho người thả reaction (không cộng cho tác giả msg)
        db.add_xp_reaction(user.id, reaction.message.guild.id, XP_REACTION)
        logger.debug(f'+{XP_REACTION} XP (reaction) → {user}')

    async def on_voice_state_update(
        self,
        member: discord.Member,
        before: discord.VoiceState,
        after: discord.VoiceState,
    ):
        if member.bot or member.guild.id != GUILD_ID:
            return

        joined = before.channel is None and after.channel is not None
        left   = before.channel is not None and after.channel is None

        if joined:
            db.set_voice_join(member.id, member.guild.id)
            logger.debug(f'{member} vào voice → bắt đầu tính XP')
        elif left:
            minutes = db.flush_voice_xp(member.id, member.guild.id, XP_VOICE_MIN)
            if minutes > 0:
                logger.info(f'+{minutes * XP_VOICE_MIN:.0f} XP (voice {minutes}m) → {member}')

    # ─────────────────── Background: flush voice mỗi 1 phút ─────────────

    @tasks.loop(minutes=1)
    async def flush_voice_loop(self):
        """Mỗi phút: cộng XP voice cho tất cả member đang ở voice."""
        for guild in self.guilds:
            if guild.id != GUILD_ID:
                continue
            for vc in guild.voice_channels:
                for member in vc.members:
                    if member.bot:
                        continue
                    # Thay vì flush hẳn, chỉ cộng XP 1 phút mỗi vòng lặp
                    db.add_xp_manual(member.id, guild.id, XP_VOICE_MIN)

    @flush_voice_loop.before_loop
    async def before_flush(self):
        await self.wait_until_ready()


bot = Chronicle()

# ─────────────────────────── Slash Commands ──────────────────────────────

@bot.tree.command(name='rank', description='Xem rank và XP của bạn hoặc thành viên khác')
@app_commands.describe(thanh_vien='Thành viên muốn xem (mặc định: chính bạn)')
async def cmd_rank(interaction: discord.Interaction, thanh_vien: discord.Member = None):
    await interaction.response.defer(thinking=True)

    target = thanh_vien or interaction.user
    if target.bot:
        await interaction.followup.send('❌ Bot không có rank!', ephemeral=True)
        return

    db.upsert_member(target.id, interaction.guild_id)
    row = db.get_member(target.id, interaction.guild_id)
    xp = row['xp'] if row else 0.0

    tier     = get_tier(xp)
    position = db.get_rank_position(target.id, interaction.guild_id)
    bar      = xp_bar(xp, tier)
    to_next  = xp_to_next(xp, tier)

    embed = discord.Embed(
        title=f'📊 {target.display_name}',
        color=tier['color'],
    )
    embed.set_thumbnail(url=target.display_avatar.url)
    embed.add_field(name='Rank', value=tier['name'], inline=True)
    embed.add_field(name='Vị trí', value=f'#{position}', inline=True)
    embed.add_field(name='Tổng XP', value=f'{xp:,.0f} XP', inline=True)
    embed.add_field(
        name=f'Tiến trình [{bar}]',
        value=f'Còn **{to_next}** để lên tier tiếp theo',
        inline=False,
    )
    embed.add_field(name='💬 Tin nhắn', value=f"{row['total_messages']:,}", inline=True)
    embed.add_field(name='👍 Reactions', value=f"{row['total_reactions']:,}", inline=True)
    embed.add_field(name='🎙️ Voice', value=f"{row['total_voice_min']:,} phút", inline=True)
    embed.set_footer(text='HEe • Chronicle | High Ego eSport')

    await interaction.followup.send(embed=embed)


@bot.tree.command(name='leaderboard', description='Top thành viên tương tác nhiều nhất')
@app_commands.describe(so_luong='Số lượng hiển thị (mặc định 10, tối đa 25)')
async def cmd_leaderboard(interaction: discord.Interaction, so_luong: int = 10):
    await interaction.response.defer(thinking=True)

    limit = max(1, min(so_luong, 25))
    rows  = db.get_leaderboard(interaction.guild_id, limit)

    if not rows:
        await interaction.followup.send('❌ Chưa có dữ liệu tương tác nào!', ephemeral=True)
        return

    embed = discord.Embed(
        title='🏆 Bảng xếp hạng tương tác — HEe',
        color=COLOR_RED,
    )

    medals = {1: '🥇', 2: '🥈', 3: '🥉'}
    lines = []
    for idx, row in enumerate(rows, start=1):
        member = interaction.guild.get_member(int(row['user_id']))
        name   = member.display_name if member else f'<@{row["user_id"]}>'
        tier   = get_tier(row['xp'])
        medal  = medals.get(idx, f'`{idx:>2}.`')
        lines.append(
            f"{medal} **{name}** — {tier['name']}  `{row['xp']:,.0f} XP`"
        )

    embed.description = '\n'.join(lines)
    embed.set_footer(text='HEe • Chronicle | High Ego eSport')
    await interaction.followup.send(embed=embed)


@bot.tree.command(name='rank-info', description='Xem thông tin các tier và điều kiện XP')
async def cmd_rank_info(interaction: discord.Interaction):
    embed = discord.Embed(
        title='📋 Hệ thống Rank — HEe Chronicle',
        color=COLOR_RED,
    )
    tier_lines = []
    for t in reversed(TIERS):
        if t['max'] == float('inf'):
            xp_range = f'{t["min"]:,} XP trở lên'
        else:
            xp_range = f'{t["min"]:,} – {t["max"]:,} XP'
        tier_lines.append(f"{t['name']}: **{xp_range}**")

    embed.add_field(name='Các Tier', value='\n'.join(tier_lines), inline=False)
    embed.add_field(
        name='Cách kiếm XP',
        value=(
            f'💬 Gửi tin nhắn: **+{XP_MSG:.0f} XP** (cooldown {MSG_COOLDOWN}s)\n'
            f'👍 Thả reaction: **+{XP_REACTION:.1f} XP** mỗi reaction\n'
            f'🎙️ Thời gian voice: **+{XP_VOICE_MIN:.0f} XP** / phút'
        ),
        inline=False,
    )
    embed.set_footer(text='HEe • Chronicle | High Ego eSport')
    await interaction.response.send_message(embed=embed)


@bot.tree.command(name='xp-add', description='[Admin] Cộng hoặc trừ XP cho thành viên')
@app_commands.describe(
    thanh_vien='Thành viên cần chỉnh XP',
    so_xp='Số XP cần cộng (âm để trừ)',
)
async def cmd_xp_add(interaction: discord.Interaction, thanh_vien: discord.Member, so_xp: float):
    # Kiểm tra quyền Admin
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message(
            '❌ Chỉ **Admin** mới dùng được lệnh này!', ephemeral=True
        )
        return
    if thanh_vien.bot:
        await interaction.response.send_message('❌ Không thể cộng XP cho bot!', ephemeral=True)
        return

    db.add_xp_manual(thanh_vien.id, interaction.guild_id, so_xp)
    row  = db.get_member(thanh_vien.id, interaction.guild_id)
    new_xp = row['xp'] if row else 0.0
    tier = get_tier(new_xp)

    sign = '+' if so_xp >= 0 else ''
    embed = discord.Embed(
        title='✅ Điều chỉnh XP thành công',
        description=(
            f'**{thanh_vien.display_name}**\n'
            f'Thay đổi: `{sign}{so_xp:.0f} XP`\n'
            f'XP hiện tại: `{new_xp:,.0f} XP`\n'
            f'Rank: {tier["name"]}'
        ),
        color=COLOR_RED,
    )
    embed.set_footer(text=f'Thực hiện bởi {interaction.user.display_name}')
    await interaction.response.send_message(embed=embed)


# ─────────────────────────── Entry point ─────────────────────────────────
if __name__ == '__main__':
    if not BOT_TOKEN:
        logger.error('BOT_TOKEN chưa được set trong .env! Dừng bot.')
        sys.exit(1)
    if not GUILD_ID:
        logger.error('GUILD_ID chưa được set trong .env! Dừng bot.')
        sys.exit(1)
    bot.run(BOT_TOKEN, log_handler=None)
