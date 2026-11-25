"""
bot.py — HEe • Tribunal (P4 - Ticket Bot Chuyên Nghiệp)
1. Giao diện bảng điều khiển (Panel) với Select Menu phân loại (Tố giác, thắc mắc, đổi tiền...).
2. Tạo kênh riêng biệt per-ticket với quyền riêng tư chỉ cho người tạo và Role HE.
3. Chỉ Role HE hoặc người tạo ticket mới có quyền Claim hoặc Đóng Ticket.
4. Auto-close sau 3 giờ nếu không có phản hồi mới.
5. Lưu transcript HTML vào data/transcripts/ và gửi bản sao vào kênh log.
"""

import os
import sys
import asyncio
import logging
from datetime import datetime

import discord
from discord import app_commands
from discord.ext import commands, tasks
from dotenv import load_dotenv

import db
import transcript

load_dotenv()

# Windows console UTF-8 fix
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
logger = logging.getLogger('HEe.Tribunal')

# Config từ .env
BOT_TOKEN           = os.getenv('BOT_TOKEN', '')
GUILD_ID            = int(os.getenv('GUILD_ID', '0'))
HE_ROLE_NAME        = os.getenv('HE_ROLE_NAME', 'HE')
TICKET_CATEGORY_ID  = int(os.getenv('TICKET_CATEGORY_ID', '0'))
TRANSCRIPT_LOG_ID   = int(os.getenv('TRANSCRIPT_LOG_CHANNEL_ID', '0'))
AUTO_CLOSE_SECONDS  = int(os.getenv('AUTO_CLOSE_SECONDS', '10800'))  # Mặc định 3 tiếng

COLOR_RED   = 0xE11D48
COLOR_DARK  = 0x881337

intents = discord.Intents.default()
intents.guilds = True
intents.members = True
intents.messages = True
intents.message_content = True

def has_he_role(member: discord.Member) -> bool:
    if member.guild_permissions.administrator:
        return True
    return any(r.name == HE_ROLE_NAME or str(r.id) == HE_ROLE_NAME for r in member.roles)

# ─────────────────── BUTTONS TRONG PHÒNG TICKET ───────────────────
class TicketControlView(discord.ui.View):
    def __init__(self, ticket_row=None):
        super().__init__(timeout=None)

    @discord.ui.button(label='Tiếp nhận (Claim)', style=discord.ButtonStyle.success, emoji='🙋‍♂️', custom_id='ticket_claim_btn')
    async def btn_claim(self, interaction: discord.Interaction, button: discord.ui.Button):
        member = interaction.user
        if not isinstance(member, discord.Member) or not has_he_role(member):
            await interaction.response.send_message('❌ Chỉ có thành viên có Role **HE** mới được tiếp nhận ticket này!', ephemeral=True)
            return

        success = db.claim_ticket(interaction.channel_id, member.id)
        if success:
            button.disabled = True
            button.label = f'Đã tiếp nhận: {member.display_name}'
            await interaction.response.edit_message(view=self)
            await interaction.followup.send(f'🛡️ **{member.mention} (Role HE)** đã tiếp nhận hỗ trợ ticket này.')
        else:
            await interaction.response.send_message('⚠️ Ticket này đã được tiếp nhận trước đó hoặc đã đóng.', ephemeral=True)

    @discord.ui.button(label='Đóng Ticket', style=discord.ButtonStyle.danger, emoji='🔒', custom_id='ticket_close_btn')
    async def btn_close(self, interaction: discord.Interaction, button: discord.ui.Button):
        row = db.get_ticket_by_channel(interaction.channel_id)
        if not row:
            await interaction.response.send_message('❌ Không tìm thấy thông tin ticket trong database.', ephemeral=True)
            return

        member = interaction.user
        is_creator = str(member.id) == str(row['creator_id'])
        is_he = isinstance(member, discord.Member) and has_he_role(member)

        # Kiểm tra điều kiện: chỉ Role HE hoặc người tạo ticket mới được đóng
        if not (is_creator or is_he):
            await interaction.response.send_message('❌ Chỉ có **Người tạo ticket** hoặc thành viên mang **Role HE** mới có quyền đóng ticket này!', ephemeral=True)
            return

        await interaction.response.send_message('⏳ Đang kết xuất transcript và tiến hành đóng ticket...')
        await close_and_delete_ticket(interaction.channel, closed_by=member.display_name)

# ─────────────────── DROPDOWN CHỌN LOẠI TICKET ───────────────────
class TicketCategorySelect(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(
                label='Tố Giác Gian Lận / Toxic',
                description='Báo cáo hành vi phá hoại, dùng phần mềm cấm hoặc xúc phạm',
                emoji='🚨',
                value='to_giac'
            ),
            discord.SelectOption(
                label='Khiếu Nại & Đổi Thưởng',
                description='Hỗ trợ cộng điểm thưởng Daily, Event hoặc quy đổi',
                emoji='💵',
                value='doi_thuong'
            ),
            discord.SelectOption(
                label='Hỏi Đáp & Hỗ Trợ Chung',
                description='Giải đáp thắc mắc về máy chủ, quyền lợi và sự kiện',
                emoji='❓',
                value='thac_mac'
            ),
            discord.SelectOption(
                label='Đăng Ký / Hỗ Trợ Giải Đấu',
                description='Các vấn đề về team, check-in và bảng đấu eSport',
                emoji='🏆',
                value='giai_dau'
            ),
        ]
        super().__init__(placeholder='Chọn loại hỗ trợ bạn cần...', min_values=1, max_values=1, custom_id='ticket_category_select', options=options)

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        guild = interaction.guild
        member = interaction.user
        selected_type = self.values[0]

        type_names = {
            'to_giac': '🚨 Tố Giác',
            'doi_thuong': '💵 Đổi Thưởng',
            'thac_mac': '❓ Thắc Mắc',
            'giai_dau': '🏆 Giải Đấu'
        }
        category_name = type_names.get(selected_type, 'Hỗ Trợ')

        # Tìm category ticket
        cat = None
        if TICKET_CATEGORY_ID:
            cat = guild.get_channel(TICKET_CATEGORY_ID)

        # Cài đặt quyền riêng tư: @everyone ẩn, chỉ member và Role HE thấy
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            member: discord.PermissionOverwrite(view_channel=True, send_messages=True, attach_files=True, embed_links=True),
            guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True, manage_channels=True, manage_messages=True)
        }

        # Thêm quyền cho role HE và lấy đối tượng role để mention
        he_role_mention = "@here"
        for role in guild.roles:
            if role.name == HE_ROLE_NAME or str(role.id) == HE_ROLE_NAME:
                overwrites[role] = discord.PermissionOverwrite(view_channel=True, send_messages=True, attach_files=True, embed_links=True)
                he_role_mention = role.mention

        clean_name = f"ticket-{selected_type}-{member.name.lower()[:10]}"
        try:
            ticket_chan = await guild.create_text_channel(
                name=clean_name,
                category=cat,
                overwrites=overwrites,
                topic=f"Ticket hỗ trợ của {member.display_name} ({member.id}) | Loại: {category_name}"
            )
        except discord.Forbidden:
            await interaction.followup.send('❌ Bot thiếu quyền `Manage Channels` để tạo kênh ticket!', ephemeral=True)
            return

        # Lưu vào Database
        t_id = db.create_ticket(ticket_chan.id, guild.id, member.id, category_name)

        # Gửi Embed mở đầu trong kênh ticket kèm buttons
        embed = discord.Embed(
            title=f'🎮 HEe Tribunal — {category_name} #{t_id:04d}',
            description=(
                f'Xin chào {member.mention}!\n'
                f'Yêu cầu hỗ trợ của bạn đã được ghi nhận vào hệ thống.\n\n'
                f'📌 **Vui lòng cung cấp chi tiết vấn đề kèm hình ảnh/bằng chứng (nếu có).**\n'
                f'🛡️ Đội ngũ quản trị viên mang **Role HE** sẽ phản hồi bạn trong thời gian sớm nhất.\n\n'
                f'⏰ *Lưu ý: Ticket sẽ tự động đóng nếu không có phản hồi nào sau 3 tiếng.*'
            ),
            color=COLOR_RED,
            timestamp=datetime.now()
        )
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.set_footer(text='High Ego eSport • Ban Quản Trị')

        control_view = TicketControlView()
        await ticket_chan.send(content=f'📢 {he_role_mention} | Có yêu cầu hỗ trợ mới từ {member.mention}!', embed=embed, view=control_view)

        await interaction.followup.send(f'✅ Ticket của bạn đã được tạo thành công tại {ticket_chan.mention}!', ephemeral=True)

class TicketPanelView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(TicketCategorySelect())

# ─────────────────── HÀM XỬ LÝ ĐÓNG VÀ XUẤT TRANSCRIPT ───────────────────
async def close_and_delete_ticket(channel: discord.TextChannel, closed_by: str = 'Hệ thống'):
    row = db.get_ticket_by_channel(channel.id)
    if not row or row['status'] == 'closed':
        return

    creator = channel.guild.get_member(int(row['creator_id'])) or await channel.guild.fetch_member(int(row['creator_id']))

    # 1. Tạo file transcript HTML
    transcript_path = await transcript.generate_html_transcript(
        channel=channel,
        ticket_id=row['ticket_id'],
        category_type=row['category_type'],
        creator=creator or channel.guild.me,
        closed_by=closed_by
    )

    # 2. Lưu vào DB
    db.close_ticket(channel.id, transcript_path)

    # 3. Gửi bản sao transcript vào kênh log (nếu có)
    if TRANSCRIPT_LOG_ID:
        log_chan = channel.guild.get_channel(TRANSCRIPT_LOG_ID)
        if log_chan:
            log_embed = discord.Embed(
                title=f'📋 Báo Cáo Ticket Đã Đóng #{row["ticket_id"]:04d}',
                color=COLOR_DARK,
                timestamp=datetime.now()
            )
            log_embed.add_field(name='Người mở', value=f'<@{row["creator_id"]}>', inline=True)
            log_embed.add_field(name='Loại', value=row['category_type'], inline=True)
            log_embed.add_field(name='Người đóng', value=closed_by, inline=True)
            try:
                await log_chan.send(embed=log_embed, file=discord.File(transcript_path))
            except Exception as e:
                logger.error(f'Không thể gửi transcript vào kênh log: {e}')

    # 4. Gửi file qua tin nhắn riêng (DM) cho người tạo ticket
    if creator:
        try:
            dm_embed = discord.Embed(
                title=f'🔒 Ticket #{row["ticket_id"]:04d} Đã Được Đóng',
                description=f'Cảm ơn bạn đã liên hệ ban quản trị **High Ego eSport**.\nĐính kèm dưới đây là file lưu trữ lịch sử cuộc trò chuyện (Transcript).',
                color=COLOR_RED
            )
            await creator.send(embed=dm_embed, file=discord.File(transcript_path))
        except Exception:
            pass

    # Đợi 5 giây rồi xóa hẳn kênh ticket
    await channel.send('🛑 Kênh này sẽ được dọn dẹp sau 5 giây...')
    await asyncio.sleep(5)
    try:
        await channel.delete(reason=f"Đóng ticket #{row['ticket_id']} bởi {closed_by}")
    except Exception as e:
        logger.error(f'Không thể xóa kênh ticket: {e}')

# ─────────────────── BOT CLASS & TASK AUTO-CLOSE ───────────────────
class TribunalBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix='!', intents=intents)

    async def setup_hook(self):
        db.init_db()
        logger.info('SQLite Tickets DB khởi tạo thành công.')

        # Khôi phục persistence cho persistent views
        self.add_view(TicketPanelView())
        self.add_view(TicketControlView())

        guild = discord.Object(id=GUILD_ID)
        self.tree.copy_global_to(guild=guild)
        try:
            synced = await self.tree.sync(guild=guild)
            logger.info(f'Synced {len(synced)} slash command(s) vào guild {GUILD_ID}.')
        except discord.Forbidden:
            synced = await self.tree.sync()
            logger.info(f'Synced {len(synced)} global slash command(s).')

        self.auto_close_checker.start()

    async def on_ready(self):
        logger.info(f'Logged in as {self.user} (ID: {self.user.id})')

    async def on_message(self, message: discord.Message):
        if message.author.bot or not message.guild or message.guild.id != GUILD_ID:
            return
        # Cập nhật thời gian hoạt động mới nhất cho ticket
        db.update_last_active(message.channel.id)
        await self.process_commands(message)

    @tasks.loop(minutes=5)
    async def auto_close_checker(self):
        """Kiểm tra các ticket đã quá 3 tiếng không có phản hồi và tự động đóng."""
        inactive_tickets = db.get_inactive_open_tickets(max_idle_seconds=AUTO_CLOSE_SECONDS)
        for t in inactive_tickets:
            channel_id = int(t['channel_id'])
            channel = self.get_channel(channel_id)
            if channel:
                logger.info(f'[AutoClose] Ticket #{t["ticket_id"]} (Kênh {channel.name}) không có phản hồi sau 3h. Đang tự động đóng...')
                await channel.send('⏰ **Ticket này đã không có hoạt động mới trong hơn 3 tiếng. Hệ thống sẽ tự động đóng và kết xuất dữ liệu.**')
                await asyncio.sleep(3)
                await close_and_delete_ticket(channel, closed_by='Tự Động (Auto-Close 3h)')

    @auto_close_checker.before_loop
    async def before_auto_close(self):
        await self.wait_until_ready()

bot = TribunalBot()

# ─────────────────── SLASH COMMANDS ───────────────────

@bot.tree.command(name='setup-ticket-panel', description='[Admin] Tạo bảng điều khiển mở Ticket tại kênh này')
async def cmd_setup_panel(interaction: discord.Interaction):
    if not interaction.user.guild_permissions.administrator and not has_he_role(interaction.user):
        await interaction.response.send_message('❌ Chỉ có **Administrator** hoặc thành viên mang **Role HE** mới được thiết lập bảng ticket!', ephemeral=True)
        return

    embed = discord.Embed(
        title='🛡️ TRUNG TÂM HỖ TRỢ — HIGH EGO ESPORT',
        description=(
            'Chào mừng bạn đến với trung tâm hỗ trợ và giải quyết khiếu nại của **HEe**.\n\n'
            '📌 **Cách tạo ticket hỗ trợ:**\n'
            'Hãy chọn phân loại tương ứng với nhu cầu của bạn ở menu bên dưới.\n'
            'Một kênh chat riêng tư sẽ được tạo ra để bạn trao đổi trực tiếp với ban quản trị.\n\n'
            '⚠️ *Vui lòng không spam ticket hoặc tạo yêu cầu không có nội dung.*'
        ),
        color=COLOR_RED
    )
    embed.set_thumbnail(url=interaction.guild.icon.url if interaction.guild.icon else None)
    embed.set_footer(text='HEe Tribunal • Hệ thống hỗ trợ thành viên')

    panel_view = TicketPanelView()
    await interaction.channel.send(embed=embed, view=panel_view)
    await interaction.response.send_message('✅ Đã tạo thành công Bảng điều khiển Ticket!', ephemeral=True)

@bot.tree.command(name='close-ticket', description='Đóng ticket hiện tại và xuất dữ liệu lưu trữ')
async def cmd_close(interaction: discord.Interaction):
    row = db.get_ticket_by_channel(interaction.channel_id)
    if not row:
        await interaction.response.send_message('❌ Lệnh này chỉ sử dụng được bên trong kênh Ticket đang mở!', ephemeral=True)
        return

    member = interaction.user
    is_creator = str(member.id) == str(row['creator_id'])
    is_he = isinstance(member, discord.Member) and has_he_role(member)

    if not (is_creator or is_he):
        await interaction.response.send_message('❌ Chỉ có **Người tạo ticket** hoặc thành viên mang **Role HE** mới có quyền đóng ticket!', ephemeral=True)
        return

    await interaction.response.send_message('⏳ Đang tiến hành kết xuất transcript và đóng ticket...')
    await close_and_delete_ticket(interaction.channel, closed_by=member.display_name)

if __name__ == '__main__':
    if not BOT_TOKEN:
        logger.error('BOT_TOKEN chưa được cài đặt trong .env!')
        sys.exit(1)
    if not GUILD_ID:
        logger.error('GUILD_ID chưa được cài đặt trong .env!')
        sys.exit(1)
    bot.run(BOT_TOKEN, log_handler=None)
