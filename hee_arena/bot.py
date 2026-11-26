"""
bot.py — HEe • Arena (Tournament & Scrims Manager)
Chuyên trách tổ chức scrims và giải đấu eSport (Liên Minh Huyền Thoại):
1. Khởi tạo giải đấu (Mì ăn liền knockout hoặc Vòng bảng -> Chung kết).
2. Đăng ký & quản lý các đội tuyển (tag thành viên từng team).
3. Bốc thăm /random chia bảng, ghép cặp đấu tự động.
4. Tự động tạo và quản lý phòng Voice bảo mật riêng per-team, tự move thành viên vào voice.
5. Cập nhật kết quả trận đấu, tự dọn dẹp phòng voice sau khi xong trận và vinh danh Quán quân.
"""

import os
import sys
import json
import random
import logging
from datetime import datetime
from pathlib import Path

import discord
from discord import app_commands
from discord.ext import commands
from dotenv import load_dotenv

import arena_db as db

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
logger = logging.getLogger('HEe.Arena')

BASE_DIR                = Path(__file__).parent
ASSETS_DIR              = BASE_DIR / "assets"
TOURNAMENT_BANNER_GIF   = ASSETS_DIR / "tournament_banner.gif"

BOT_TOKEN               = os.getenv('BOT_TOKEN', '')
GUILD_ID                = int(os.getenv('GUILD_ID', '0'))
HE_ROLE_NAME            = os.getenv('HE_ROLE_NAME', 'HE')
CATEGORY_DEFAULT_NAME   = os.getenv('TOURNAMENT_CATEGORY_NAME', '🏆 HEe Scrims & Tournaments')

COLOR_RED   = 0xE11D48
COLOR_DARK  = 0x881337
COLOR_GOLD  = 0xFBBF24
COLOR_BLUE  = 0x3B82F6

intents = discord.Intents.default()
intents.guilds = True
intents.members = True
intents.voice_states = True
intents.message_content = True


def has_he_role(member: discord.Member) -> bool:
    if member.guild_permissions.administrator:
        return True
    return any(r.name == HE_ROLE_NAME or str(r.id) == HE_ROLE_NAME for r in member.roles)


class ArenaBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix='!', intents=intents)

    async def setup_hook(self):
        db.init_db()
        logger.info('SQLite Arena DB khởi tạo thành công.')

        guild = discord.Object(id=GUILD_ID)
        self.tree.copy_global_to(guild=guild)
        try:
            synced = await self.tree.sync(guild=guild)
            logger.info(f'Synced {len(synced)} slash command(s) vào guild {GUILD_ID}.')
        except discord.Forbidden:
            logger.warning(f'Không thể sync guild {GUILD_ID} (403). Fallback sang global sync...')
            synced = await self.tree.sync()
            logger.info(f'Synced {len(synced)} global slash command(s).')

    async def on_ready(self):
        logger.info(f'Logged in as {self.user} (ID: {self.user.id})')
        await self.change_presence(
            activity=discord.Activity(
                type=discord.ActivityType.competing,
                name='HEe Scrims & Tournament'
            )
        )


bot = ArenaBot()
scrim_group = app_commands.Group(name='scrim', description='Hệ thống quản lý Scrims & Giải đấu High Ego eSport')


# ─────────────────────────── LỆNH: ANNOUNCE TOURNAMENT ───────────────────────────

@scrim_group.command(name='announce', description='[Role HE / Admin] Phát thông báo giải đấu / Scrims @everyone')
@app_commands.describe(
    tieu_de='Tiêu đề thông báo giải đấu (VD: ĐẠI CHIẾN SCRIMS HEe #01)',
    noi_dung='Nội dung, thể lệ, thời gian và cơ cấu giải thưởng',
    kenh_thong_bao='Kênh muốn đăng thông báo (mặc định: kênh hiện tại)'
)
async def cmd_scrim_announce(
    interaction: discord.Interaction,
    tieu_de: str,
    noi_dung: str,
    kenh_thong_bao: discord.TextChannel = None
):
    if not isinstance(interaction.user, discord.Member) or not has_he_role(interaction.user):
        await interaction.response.send_message('❌ Chỉ có thành viên mang **Role HE** mới được phát thông báo giải đấu!', ephemeral=True)
        return

    target_channel = kenh_thong_bao or interaction.channel

    embed = discord.Embed(
        title=f'🏆 {tieu_de.strip().upper()}',
        description=noi_dung.strip(),
        color=COLOR_RED,
        timestamp=datetime.now()
    )
    embed.set_author(
        name=f'High Ego eSport — Arena Tournament',
        icon_url=interaction.guild.icon.url if interaction.guild.icon else None
    )
    embed.set_footer(
        text=f'Tổ chức bởi {interaction.user.display_name} • High Ego eSport',
        icon_url=interaction.user.display_avatar.url
    )

    if TOURNAMENT_BANNER_GIF.exists():
        file = discord.File(str(TOURNAMENT_BANNER_GIF), filename="tournament_banner.gif")
        embed.set_image(url="attachment://tournament_banner.gif")
        await target_channel.send(content='@everyone', embed=embed, file=file)
    else:
        await target_channel.send(content='@everyone', embed=embed)

    await interaction.response.send_message(
        f'✅ Đã phát thông báo giải đấu thành công tại {target_channel.mention}!',
        ephemeral=True
    )


# ─────────────────────────── LỆNH: CREATE TOURNAMENT ───────────────────────────

@scrim_group.command(name='create', description='Khởi tạo giải đấu / buổi Scrims mới')
@app_commands.describe(
    ten_giai='Tên của giải đấu hoặc buổi Scrims',
    the_thuc='Thể thức thi đấu: Mì ăn liền (Knockout) hoặc Vòng bảng -> Chung kết'
)
@app_commands.choices(the_thuc=[
    app_commands.Choice(name='⚡ Mì Ăn Liền (Loại trực tiếp / Knockout)', value='fast'),
    app_commands.Choice(name='🏆 Vòng Bảng ➔ Chung Kết (Group Stage + Playoffs)', value='groups'),
])
async def cmd_scrim_create(
    interaction: discord.Interaction,
    ten_giai: str,
    the_thuc: app_commands.Choice[str]
):
    if not isinstance(interaction.user, discord.Member) or not has_he_role(interaction.user):
        await interaction.response.send_message('❌ Chỉ có thành viên mang **Role HE** hoặc Quản trị viên mới được tạo giải!', ephemeral=True)
        return

    active = db.get_active_tournament(interaction.guild_id)
    if active:
        await interaction.response.send_message(
            f'⚠️ Hiện đang có giải đấu **"{active["name"]}"** (ID: `#{active["id"]}`) đang diễn ra!\n'
            f'Vui lòng hoàn thành giải hiện tại hoặc dùng `/scrim cancel` để hủy trước khi tạo mới.',
            ephemeral=True
        )
        return

    t_id = db.create_tournament(
        guild_id=interaction.guild_id,
        name=ten_giai,
        format_type=the_thuc.value,
        created_by=interaction.user.id
    )

    format_desc = "⚡ Loại Trực Tiếp (Knockout / Mì Ăn Liền)" if the_thuc.value == 'fast' else "🏆 Vòng Bảng ➔ Chung Kết"

    embed = discord.Embed(
        title=f'🎮 KHỞI TẠO GIẢI ĐẤU THÀNH CÔNG: {ten_giai}',
        description=(
            f'Giải đấu **#{t_id:03d}** đã chính thức mở cổng đăng ký!\n\n'
            f'📋 **Thể thức:** `{format_desc}`\n'
            f'👑 **Người khởi tạo:** {interaction.user.mention}\n'
            f'📌 **Bước tiếp theo:** Dùng lệnh `/scrim add-team` để thêm các đội tuyển tham dự.'
        ),
        color=COLOR_RED,
        timestamp=datetime.now()
    )
    embed.set_footer(text='High Ego eSport • Arena System')

    if TOURNAMENT_BANNER_GIF.exists():
        file = discord.File(str(TOURNAMENT_BANNER_GIF), filename="tournament_banner.gif")
        embed.set_image(url="attachment://tournament_banner.gif")
        await interaction.response.send_message(embed=embed, file=file)
    else:
        await interaction.response.send_message(embed=embed)


# ─────────────────────────── LỆNH: ADD TEAM ───────────────────────────

@scrim_group.command(name='add-team', description='Đăng ký đội tuyển và tag các thành viên tham gia')
@app_commands.describe(
    ten_doi='Tên đội tuyển (VD: HE Red, Dragon Slayer...)',
    doi_truong='Đội trưởng đại diện',
    thanh_vien_1='Thành viên 2',
    thanh_vien_2='Thành viên 3',
    thanh_vien_3='Thành viên 4',
    thanh_vien_4='Thành viên 5'
)
async def cmd_scrim_add_team(
    interaction: discord.Interaction,
    ten_doi: str,
    doi_truong: discord.Member,
    thanh_vien_1: discord.Member = None,
    thanh_vien_2: discord.Member = None,
    thanh_vien_3: discord.Member = None,
    thanh_vien_4: discord.Member = None
):
    if not isinstance(interaction.user, discord.Member) or not has_he_role(interaction.user):
        await interaction.response.send_message('❌ Chỉ có thành viên mang **Role HE** mới được thêm đội!', ephemeral=True)
        return

    tourney = db.get_active_tournament(interaction.guild_id)
    if not tourney:
        await interaction.response.send_message('❌ Hiện không có giải đấu nào đang mở đăng ký. Hãy dùng `/scrim create` trước!', ephemeral=True)
        return

    if tourney['status'] != 'registering':
        await interaction.response.send_message('❌ Giải đấu đã bắt đầu bốc thăm / thi đấu, không thể nhận thêm đội!', ephemeral=True)
        return

    members = [doi_truong.id]
    for m in [thanh_vien_1, thanh_vien_2, thanh_vien_3, thanh_vien_4]:
        if m and m.id not in members:
            members.append(m.id)

    team_id = db.add_team(tourney['id'], ten_doi, doi_truong.id, members)
    all_teams = db.get_teams(tourney['id'])

    members_mentions = " ".join([f"<@{uid}>" for uid in members])

    embed = discord.Embed(
        title=f'⚔️ ĐÃ THÊM ĐỘI TUYỂN: {ten_doi}',
        description=(
            f'• **Mã đội:** `Team #{team_id}`\n'
            f'• **Đội trưởng:** {doi_truong.mention}\n'
            f'• **Danh sách thành viên:** {members_mentions}\n'
            f'• **Tổng số đội hiện tại:** `{len(all_teams)} đội`'
        ),
        color=COLOR_RED,
        timestamp=datetime.now()
    )
    embed.set_footer(text='Dùng /scrim random khi đã đủ đội để tiến hành chia bảng!')
    await interaction.response.send_message(embed=embed)


# ─────────────────────────── LỆNH: RANDOM (BỐC THĂM) ───────────────────────────

@scrim_group.command(name='random', description='Bốc thăm ngẫu nhiên chia bảng hoặc ghép nhánh đấu')
async def cmd_scrim_random(interaction: discord.Interaction):
    if not isinstance(interaction.user, discord.Member) or not has_he_role(interaction.user):
        await interaction.response.send_message('❌ Chỉ có thành viên mang **Role HE** mới được thực hiện bốc thăm!', ephemeral=True)
        return

    tourney = db.get_active_tournament(interaction.guild_id)
    if not tourney:
        await interaction.response.send_message('❌ Không có giải đấu nào đang hoạt động!', ephemeral=True)
        return

    teams = db.get_teams(tourney['id'])
    if len(teams) < 2:
        await interaction.response.send_message(f'❌ Cần tối thiểu 2 đội để bốc thăm (hiện có {len(teams)} đội)!', ephemeral=True)
        return

    await interaction.response.defer()

    # 1. Tạo Category riêng cho giải đấu nếu chưa có
    guild = interaction.guild
    category = None
    if tourney['category_id']:
        category = guild.get_channel(int(tourney['category_id']))

    if not category:
        category_name = f"🏆 {tourney['name'][:25]}"
        category = await guild.create_category(name=category_name)
        db.update_tournament_status(tourney['id'], status='in_progress', category_id=category.id)
    else:
        db.update_tournament_status(tourney['id'], status='in_progress')

    # Trộn ngẫu nhiên danh sách đội
    shuffled_teams = list(teams)
    random.shuffle(shuffled_teams)

    # 2. Xử lý theo thể thức
    if tourney['format'] == 'fast':
        # Thể thức Knockout (Mì ăn liền)
        embed = discord.Embed(
            title=f'🎲 KẾT QUẢ BỐC THĂM NHÁNH ĐẤU — {tourney["name"]}',
            description='Các cặp đấu loại trực tiếp đã được hệ thống bắt cặp ngẫu nhiên:',
            color=COLOR_RED,
            timestamp=datetime.now()
        )

        match_count = len(shuffled_teams) // 2
        round_name = "Chung Kết" if match_count == 1 else ("Bán Kết" if match_count == 2 else "Tứ Kết")

        for i in range(match_count):
            t_a = shuffled_teams[i * 2]
            t_b = shuffled_teams[i * 2 + 1]
            m_id = db.create_match(tourney['id'], round_name, i + 1, t_a['id'], t_b['id'])

            embed.add_field(
                name=f'⚔️ Trận #{m_id:02d} ({round_name} {i+1})',
                value=f'🔴 **{t_a["name"]}** vs 🔵 **{t_b["name"]}**',
                inline=False
            )

        if len(shuffled_teams) % 2 != 0:
            lucky_team = shuffled_teams[-1]
            embed.add_field(
                name='🌟 Đội Đặc Cách (Bye)',
                value=f'**{lucky_team["name"]}** được vào thẳng vòng trong do số đội lẻ.',
                inline=False
            )

    else:
        # Thể thức Vòng Bảng (Groups)
        group_a = []
        group_b = []
        for idx, team in enumerate(shuffled_teams):
            if idx % 2 == 0:
                group_a.append(team)
                db.update_team_group(team['id'], 'A', len(group_a))
            else:
                group_b.append(team)
                db.update_team_group(team['id'], 'B', len(group_b))

        embed = discord.Embed(
            title=f'🎲 KẾT QUẢ CHIA BẢNG ĐẤU — {tourney["name"]}',
            description='Hệ thống đã phân bổ ngẫu nhiên các đội vào 2 bảng đấu:',
            color=COLOR_RED,
            timestamp=datetime.now()
        )

        txt_a = "\n".join([f"• **{t['name']}** (<@{t['captain_id']}>)" for t in group_a])
        txt_b = "\n".join([f"• **{t['name']}** (<@{t['captain_id']}>)" for t in group_b])
        embed.add_field(name='🔴 BẢNG A', value=txt_a or 'Chưa có đội', inline=True)
        embed.add_field(name='🔵 BẢNG B', value=txt_b or 'Chưa có đội', inline=True)

        # Tạo các cặp đấu vòng tròn cho từng bảng
        match_num = 1
        for grp_name, grp_teams in [('Bảng A', group_a), ('Bảng B', group_b)]:
            for i in range(len(grp_teams)):
                for j in range(i + 1, len(grp_teams)):
                    db.create_match(tourney['id'], f'Vòng Bảng - {grp_name}', match_num, grp_teams[i]['id'], grp_teams[j]['id'])
                    match_num += 1

    embed.set_footer(text='Dùng /scrim start-match [mã_trận] để mở phòng Voice bảo mật và triệu tập 2 đội thi đấu!')
    if TOURNAMENT_BANNER_GIF.exists():
        file = discord.File(str(TOURNAMENT_BANNER_GIF), filename="tournament_banner.gif")
        embed.set_image(url="attachment://tournament_banner.gif")
        await interaction.followup.send(embed=embed, file=file)
    else:
        await interaction.followup.send(embed=embed)


# ─────────────────────────── LỆNH: START MATCH (TẠO VOICE RIÊNG) ───────────────────────────

@scrim_group.command(name='start-match', description='Mở 2 kênh Voice bảo mật riêng và triệu tập 2 đội vào thi đấu')
@app_commands.describe(ma_tran='Mã số trận đấu muốn kích hoạt (VD: 1, 2...)')
async def cmd_scrim_start_match(interaction: discord.Interaction, ma_tran: int):
    if not isinstance(interaction.user, discord.Member) or not has_he_role(interaction.user):
        await interaction.response.send_message('❌ Chỉ có thành viên mang **Role HE** mới được kích hoạt trận đấu!', ephemeral=True)
        return

    match = db.get_match(ma_tran)
    if not match:
        await interaction.response.send_message(f'❌ Không tìm thấy trận đấu có mã #{ma_tran}!', ephemeral=True)
        return

    if match['status'] == 'completed':
        await interaction.response.send_message(f'⚠️ Trận đấu #{ma_tran} đã hoàn thành trước đó!', ephemeral=True)
        return

    await interaction.response.defer()
    guild = interaction.guild

    tourney = db.get_tournament(match['tournament_id'])
    category = guild.get_channel(int(tourney['category_id'])) if tourney and tourney['category_id'] else None

    # Lấy danh sách thành viên Team A và Team B
    members_a_ids = json.loads(match['team_a_members']) if match['team_a_members'] else []
    members_b_ids = json.loads(match['team_b_members']) if match['team_b_members'] else []

    # Tìm role HE
    he_role = next((r for r in guild.roles if r.name == HE_ROLE_NAME or str(r.id) == HE_ROLE_NAME), None)

    # 1. Cấu hình Overwrites cho Team A
    overwrites_a = {
        guild.default_role: discord.PermissionOverwrite(view_channel=True, connect=False),
        guild.me: discord.PermissionOverwrite(view_channel=True, connect=True, speak=True, move_members=True, manage_channels=True)
    }
    if he_role:
        overwrites_a[he_role] = discord.PermissionOverwrite(view_channel=True, connect=True, speak=True, mute_members=True)

    members_a_objs = []
    for uid in members_a_ids:
        m = guild.get_member(int(uid))
        if m:
            members_a_objs.append(m)
            overwrites_a[m] = discord.PermissionOverwrite(view_channel=True, connect=True, speak=True)

    # 2. Cấu hình Overwrites cho Team B
    overwrites_b = {
        guild.default_role: discord.PermissionOverwrite(view_channel=True, connect=False),
        guild.me: discord.PermissionOverwrite(view_channel=True, connect=True, speak=True, move_members=True, manage_channels=True)
    }
    if he_role:
        overwrites_b[he_role] = discord.PermissionOverwrite(view_channel=True, connect=True, speak=True, mute_members=True)

    members_b_objs = []
    for uid in members_b_ids:
        m = guild.get_member(int(uid))
        if m:
            members_b_objs.append(m)
            overwrites_b[m] = discord.PermissionOverwrite(view_channel=True, connect=True, speak=True)

    # Tạo kênh voice riêng biệt
    clean_a = f"🔴・[Trận {ma_tran}] {match['team_a_name'][:12]}"
    clean_b = f"🔵・[Trận {ma_tran}] {match['team_b_name'][:12]}"

    voice_a = await guild.create_voice_channel(name=clean_a, category=category, overwrites=overwrites_a, user_limit=5)
    voice_b = await guild.create_voice_channel(name=clean_b, category=category, overwrites=overwrites_b, user_limit=5)

    db.set_match_ongoing(ma_tran, voice_a.id, voice_b.id)

    # 3. Tự động kéo (Move) những thành viên đang có mặt ở voice khác về đúng phòng
    moved_count = 0
    for m in members_a_objs:
        if m.voice and m.voice.channel and m.voice.channel.id != voice_a.id:
            try:
                await m.move_to(voice_a)
                moved_count += 1
            except Exception:
                pass

    for m in members_b_objs:
        if m.voice and m.voice.channel and m.voice.channel.id != voice_b.id:
            try:
                await m.move_to(voice_b)
                moved_count += 1
            except Exception:
                pass

    # 4. Gửi thông báo triệu tập
    ping_a = " ".join([m.mention for m in members_a_objs])
    ping_b = " ".join([m.mention for m in members_b_objs])

    embed = discord.Embed(
        title=f'🚨 TRIỆU TẬP THI ĐẤU — TRẬN #{ma_tran} ({match["round_name"]})',
        description=(
            f'Trận đấu giữa **{match["team_a_name"]}** và **{match["team_b_name"]}** đã được kích hoạt!\n\n'
            f'🔊 **Phòng Voice Team A:** {voice_a.mention} (Chỉ cấp quyền cho Team A)\n'
            f'🔊 **Phòng Voice Team B:** {voice_b.mention} (Chỉ cấp quyền cho Team B)\n'
            f'🚀 **Tự động Move:** Đã kéo `{moved_count}` thành viên đang online voice vào phòng.\n\n'
            f'⏰ **Yêu cầu:** Tất cả thành viên có mặt ngay lập tức để chuẩn bị cấm/chọn (Ban/Pick)!'
        ),
        color=COLOR_RED,
        timestamp=datetime.now()
    )
    embed.add_field(name=f'🔴 {match["team_a_name"]}', value=ping_a or 'Không có thông tin', inline=False)
    embed.add_field(name=f'🔵 {match["team_b_name"]}', value=ping_b or 'Không có thông tin', inline=False)
    embed.set_footer(text='Ban Quản Trị / Trọng tài dùng /scrim result để nhập kết quả sau trận.')

    await interaction.followup.send(content=f"📢 {ping_a} {ping_b}", embed=embed)


# ─────────────────────────── LỆNH: REPORT RESULT ───────────────────────────

@scrim_group.command(name='result', description='Báo cáo kết quả trận đấu và tự động dọn dẹp phòng voice')
@app_commands.describe(
    ma_tran='Mã số trận đấu vừa kết thúc',
    doi_thang='Chọn đội tuyển chiến thắng trong trận đấu này'
)
@app_commands.choices(doi_thang=[
    app_commands.Choice(name='🔴 Đội A (Team A)', value='A'),
    app_commands.Choice(name='🔵 Đội B (Team B)', value='B'),
])
async def cmd_scrim_result(
    interaction: discord.Interaction,
    ma_tran: int,
    doi_thang: app_commands.Choice[str]
):
    if not isinstance(interaction.user, discord.Member) or not has_he_role(interaction.user):
        await interaction.response.send_message('❌ Chỉ có thành viên mang **Role HE** mới được báo cáo kết quả!', ephemeral=True)
        return

    match = db.get_match(ma_tran)
    if not match:
        await interaction.response.send_message(f'❌ Không tìm thấy trận đấu #{ma_tran}!', ephemeral=True)
        return

    if match['status'] == 'completed':
        await interaction.response.send_message(f'⚠️ Trận đấu #{ma_tran} đã được nhập kết quả trước đó!', ephemeral=True)
        return

    await interaction.response.defer()
    guild = interaction.guild

    winner_id = match['team_a_id'] if doi_thang.value == 'A' else match['team_b_id']
    winner_name = match['team_a_name'] if doi_thang.value == 'A' else match['team_b_name']
    loser_id = match['team_b_id'] if doi_thang.value == 'A' else match['team_a_id']

    # Lưu kết quả vào DB
    db.set_match_winner(ma_tran, winner_id)
    db.update_team_stats(winner_id, won=True)
    db.update_team_stats(loser_id, won=False)

    # 1. Tự động xóa 2 phòng Voice tạm thời để tránh rác server
    deleted_voices = 0
    for v_id_str in [match['team_a_voice_id'], match['team_b_voice_id']]:
        if v_id_str:
            chan = guild.get_channel(int(v_id_str))
            if chan:
                try:
                    await chan.delete(reason=f"Kết thúc trận #{ma_tran}")
                    deleted_voices += 1
                except Exception as e:
                    logger.error(f"Lỗi khi xóa voice channel: {e}")

    db.clear_match_voices(ma_tran)

    embed = discord.Embed(
        title=f'🏆 KẾT QUẢ TRẬN #{ma_tran} — {match["round_name"]}',
        description=(
            f'🎉 Chúc mừng đội tuyển **{winner_name}** đã giành chiến thắng!\n\n'
            f'🧹 **Dọn dẹp:** Đã tự động giải phóng `{deleted_voices}` phòng voice tạm thời.\n'
            f'📌 Kết quả đã được ghi nhận vào hệ thống giải đấu.'
        ),
        color=COLOR_GOLD,
        timestamp=datetime.now()
    )
    embed.set_footer(text='High Ego eSport • Arena System')

    await interaction.followup.send(embed=embed)


# ─────────────────────────── LỆNH: BRACKET & STATUS ───────────────────────────

@scrim_group.command(name='bracket', description='Xem sơ đồ nhánh đấu và bảng điểm hiện tại')
async def cmd_scrim_bracket(interaction: discord.Interaction):
    tourney = db.get_active_tournament(interaction.guild_id)
    if not tourney:
        await interaction.response.send_message('❌ Hiện không có giải đấu nào đang diễn ra!', ephemeral=True)
        return

    teams = db.get_teams(tourney['id'])
    matches = db.get_matches(tourney['id'])

    embed = discord.Embed(
        title=f'📊 NHÁNH ĐẤU & TIẾN TRÌNH — {tourney["name"]}',
        description=f'**Trạng thái:** `{tourney["status"].upper()}` | **Thể thức:** `{tourney["format"]}`',
        color=COLOR_RED,
        timestamp=datetime.now()
    )

    if tourney['format'] == 'fast':
        if not matches:
            embed.description += '\n\n*Chưa có lịch thi đấu. Hãy dùng `/scrim random` để bốc thăm.*'
        else:
            for m in matches:
                status_icon = '✅' if m['status'] == 'completed' else ('🔥' if m['status'] == 'ongoing' else '⏳')
                winner_txt = f" ➔ **Thắng: {m['winner_name']}**" if m['winner_name'] else ""
                embed.add_field(
                    name=f'{status_icon} Trận #{m["id"]:02d} ({m["round_name"]})',
                    value=f'🔴 {m["team_a_name"] or "TBD"} vs 🔵 {m["team_b_name"] or "TBD"}{winner_txt}',
                    inline=False
                )
    else:
        # Bảng xếp hạng Vòng bảng
        teams_a = [t for t in teams if t['group_name'] == 'A']
        teams_b = [t for t in teams if t['group_name'] == 'B']

        teams_a.sort(key=lambda x: (x['points'], x['wins']), reverse=True)
        teams_b.sort(key=lambda x: (x['points'], x['wins']), reverse=True)

        txt_a = "\n".join([f"`{idx+1}.` **{t['name']}** — {t['points']}đ ({t['wins']}T/{t['losses']}B)" for idx, t in enumerate(teams_a)])
        txt_b = "\n".join([f"`{idx+1}.` **{t['name']}** — {t['points']}đ ({t['wins']}T/{t['losses']}B)" for idx, t in enumerate(teams_b)])

        embed.add_field(name='🔴 BẢNG A', value=txt_a or 'Trống', inline=True)
        embed.add_field(name='🔵 BẢNG B', value=txt_b or 'Trống', inline=True)

    await interaction.response.send_message(embed=embed)


# ─────────────────────────── LỆNH: CANCEL TOURNAMENT ───────────────────────────

@scrim_group.command(name='cancel', description='Hủy giải đấu hiện tại và dọn dẹp danh mục kênh')
async def cmd_scrim_cancel(interaction: discord.Interaction):
    if not isinstance(interaction.user, discord.Member) or not has_he_role(interaction.user):
        await interaction.response.send_message('❌ Chỉ có thành viên mang **Role HE** mới có quyền hủy giải đấu!', ephemeral=True)
        return

    tourney = db.get_active_tournament(interaction.guild_id)
    if not tourney:
        await interaction.response.send_message('❌ Hiện không có giải đấu nào đang hoạt động!', ephemeral=True)
        return

    await interaction.response.defer()
    guild = interaction.guild

    # Xóa Category và toàn bộ kênh con nếu có
    if tourney['category_id']:
        cat = guild.get_channel(int(tourney['category_id']))
        if cat and isinstance(cat, discord.CategoryChannel):
            for ch in cat.channels:
                try:
                    await ch.delete(reason="Hủy giải đấu")
                except Exception:
                    pass
            try:
                await cat.delete(reason="Hủy giải đấu")
            except Exception:
                pass

    db.update_tournament_status(tourney['id'], status='cancelled')
    await interaction.followup.send(f'🗑️ Đã hủy giải đấu **"{tourney["name"]}"** (ID: `#{tourney["id"]}`) và dọn dẹp sạch sẽ danh mục kênh trên server!')


bot.tree.add_command(scrim_group)

if __name__ == '__main__':
    if not BOT_TOKEN or BOT_TOKEN == 'YOUR_BOT_TOKEN_HERE':
        logger.error('BOT_TOKEN chưa được cung cấp trong .env!')
        sys.exit(1)
    bot.run(BOT_TOKEN)
