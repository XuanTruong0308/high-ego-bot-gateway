"""
bot.py — HEe • Oracle (Competitive Strategy & Draft Intelligence Bot for Road To VCS)
Chuyên trách hỗ trợ team High Ego eSport chuẩn bị tham gia giải đấu và Road To VCS:
1. /oracle draft-analyze: Phân tích đội hình 5 tướng (Damage Split, CC chain, Engage, Win condition, Weaknesses, Bans).
2. /oracle counter: Phân tích kèo đấu & Tướng khắc chế, quản lý đợt lính và thời điểm trừng phạt.
3. /oracle build: Giáo án trang bị High-Elo, ngưỡng đột biến sức mạnh và nhánh đồ phản kích tình huống.
4. /oracle comp-save & /oracle comp-list: Lưu trữ và quản lý các bài đánh chiến thuật của team.
5. /oracle scrim-log & /oracle scrim-history: Nhật ký phân tích sau trận Scrims thực chiến.
6. /oracle meta-synergy: Thư viện các cặp đôi 2v2 và combo giao tranh thống trị meta VCS.
"""

import os
import sys
from datetime import datetime
from pathlib import Path
import logging

import discord
from discord import app_commands
from discord.ext import commands
from dotenv import load_dotenv

import oracle_data as odata
import oracle_db as db

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
logger = logging.getLogger('HEe.Oracle')

BOT_TOKEN       = os.getenv('BOT_TOKEN', '')
GUILD_ID        = int(os.getenv('GUILD_ID', '0'))
HE_ROLE_NAME    = os.getenv('HE_ROLE_NAME', 'HE')

COLOR_GOLD      = 0xF59E0B
COLOR_CYAN      = 0x06B6D4
COLOR_RED       = 0xEF4444
COLOR_PURPLE    = 0x8B5CF6
COLOR_EMERALD   = 0x10B981

intents = discord.Intents.default()
intents.guilds = True


def has_he_role(member: discord.Member) -> bool:
    if member.guild_permissions.administrator:
        return True
    return any(r.name == HE_ROLE_NAME or str(r.id) == HE_ROLE_NAME for r in member.roles)


class OracleBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix='!oracle', intents=intents)

    async def setup_hook(self):
        db.init_db()
        logger.info('SQLite Oracle DB khởi tạo thành công.')

        guild = discord.Object(id=GUILD_ID)
        self.tree.copy_global_to(guild=guild)
        try:
            synced_guild = await self.tree.sync(guild=guild)
            logger.info(f'Synced {len(synced_guild)} slash command(s) vào guild {GUILD_ID}.')
            synced_global = await self.tree.sync()
            logger.info(f'Synced {len(synced_global)} global slash command(s).')
        except discord.Forbidden:
            logger.warning(f'Không thể sync guild {GUILD_ID} (403). Fallback sang global sync...')
            synced = await self.tree.sync()
            logger.info(f'Synced {len(synced)} global slash command(s).')

    async def on_ready(self):
        logger.info(f'Logged in as {self.user} (ID: {self.user.id})')
        await self.change_presence(
            activity=discord.Activity(
                type=discord.ActivityType.watching,
                name='Road To VCS • Competitive Meta'
            )
        )


bot = OracleBot()
oracle_group = app_commands.Group(name='oracle', description='Hệ thống phân tích chiến thuật Road To VCS — High Ego eSport')


# ─────────────────────────── LỆNH 1: DRAFT ANALYZE ───────────────────────────

@oracle_group.command(name='draft-analyze', description='[Road to VCS] Phân tích chuyên sâu đội hình 5 tướng (Damage, CC, Wincon, Điểm yếu)')
@app_commands.describe(
    top='Tướng Đường Trên (VD: K\'Sante, Renekton, Rumble, Aatrox...)',
    jungle='Tướng Đi Rừng (VD: Sejuani, Jarvan IV, Vi, Maokai, Nidalee...)',
    mid='Tướng Đường Giữa (VD: Azir, Orianna, Yone, Taliyah, Tristana...)',
    adc='Tướng Xạ Thủ (VD: Kalista, Varus, Ashe, Kai\'Sa...)',
    support='Tướng Hỗ Trợ (VD: Nautilus, Renata Glasc, Rakan, Braum...)'
)
async def cmd_draft_analyze(
    interaction: discord.Interaction,
    top: str,
    jungle: str,
    mid: str,
    adc: str,
    support: str
):
    await interaction.response.defer()

    report = odata.analyze_composition(top, jungle, mid, adc, support)

    embed = discord.Embed(
        title=f'🧠 PHÂN TÍCH ĐỘI HÌNH THI ĐẤU — ROAD TO VCS',
        description=(
            f'**Tổ hợp đội hình:**\n'
            f'🛡️ **TOP:** `{top.strip().title()}` | 🌲 **JGL:** `{jungle.strip().title()}` | ⚡ **MID:** `{mid.strip().title()}`\n'
            f'🏹 **ADC:** `{adc.strip().title()}` | 🛡️ **SUP:** `{support.strip().title()}`\n\n'
            f'🎯 **Lối vận hành chính:** {report["archetype"]}\n'
            f'🔑 **Điều kiện thắng (Win Condition):** {report["win_con"]}'
        ),
        color=COLOR_GOLD,
        timestamp=datetime.now()
    )

    # Thang đo sát thương
    dmg_bar = f'🗡️ Vật lý (AD): **{report["pct_ad"]}%** | 🔮 Phép thuật (AP): **{report["pct_ap"]}%** | ⚪ Chuẩn: **{report["pct_true"]}%**'
    embed.add_field(name='📊 Cân Bằng Sát Thương (Damage Split)', value=dmg_bar, inline=False)

    # Thang đo khống chế & Mở giao tranh
    cc_status = "Rất Cao (Khóa chết)" if report["cc_score"] >= 16 else ("Trung Bình (Đủ dùng)" if report["cc_score"] >= 11 else "Thiếu Hụt (Nguy hiểm)")
    engage_status = "Cực Mạnh (Chủ động)" if report["engage_score"] >= 16 else ("Khá" if report["engage_score"] >= 11 else "Thụ động (Phản giao tranh)")
    
    embed.add_field(
        name='🔒 Chỉ Số Kiểm Soát Giao Tranh',
        value=f'• Khống chế cứng (Hard CC): `{report["cc_score"]}/25` — **{cc_status}**\n• Tầm mở giao tranh (Engage): `{report["engage_score"]}/25` — **{engage_status}**',
        inline=True
    )

    # Điểm rơi sức mạnh
    curve_txt = f'• Đầu trận (1-14p): `{report["early"]}/25`\n• Giữa trận (15-25p): `{report["mid"]}/25`\n• Cuối trận (30p+): `{report["late"]}/25`'
    embed.add_field(name='⏳ Ngưỡng Sức Mạnh (Power Spikes)', value=curve_txt, inline=True)

    # Cảnh báo điểm yếu
    if report["warnings"]:
        embed.add_field(name='⚠️ Cảnh Báo Điểm Yếu Chí Mạng', value="\n".join(report["warnings"]), inline=False)
    else:
        embed.add_field(name='✅ Đánh Giá Cấu Trúc', value='Đội hình có độ cân bằng rất tốt giữa sát thương, khống chế và khả năng giao tranh.', inline=False)

    # Đề xuất Target Ban
    if report["target_bans"]:
        embed.add_field(name='🚫 Mục Tiêu Nên Cấm (Target Bans)', value=", ".join([f"`{b}`" for b in report["target_bans"]]), inline=False)

    embed.set_footer(text='High Ego eSport • Ban Huấn Luyện Road To VCS')
    await interaction.followup.send(embed=embed)


# ─────────────────────────── LỆNH 2: COUNTER & MATCHUP ───────────────────────────

@oracle_group.command(name='counter', description='[Road to VCS] Phân tích khắc chế tướng, kèo đấu kỹ năng và quản lý đợt lính')
@app_commands.describe(tuong='Tên vị tướng đối thủ cần khắc chế (VD: Yone, K\'Sante, Azir, Kalista, Renekton...)')
async def cmd_counter(interaction: discord.Interaction, tuong: str):
    clean_name = tuong.lower().strip()
    data = None
    for key, c_info in odata.CHAMPIONS.items():
        if key == clean_name or clean_name in key:
            data = c_info
            break

    if not data:
        # Fallback general advice
        embed = discord.Embed(
            title=f'⚔️ CHIẾN THUẬT ĐỐI ĐẦU: {tuong.upper()}',
            description=(
                f'Hiện dữ liệu chuyên sâu cho `{tuong}` đang được Ban huấn luyện cập nhật thêm.\n\n'
                f'📌 **Nguyên tắc đối đầu High-Elo chung:**\n'
                f'1. **Quản lý lính:** Không đẩy cao thiếu tầm nhìn khi chưa biết vị trí rừng đối thủ.\n'
                f'2. **Trừng phạt hồi chiêu:** Giao tranh ngay khi đối thủ vừa dùng chiêu thức dọn lính quan trọng.\n'
                f'3. **Lên đồ phòng ngự sớm:** Mua Giày Thép Gai (vs AD nặng) hoặc Giày Thủy Ngân (vs nhiều CC/AP) ngay lần về đầu.'
            ),
            color=COLOR_CYAN,
            timestamp=datetime.now()
        )
        await interaction.response.send_message(embed=embed)
        return

    embed = discord.Embed(
        title=f'🎯 BÁO CÁO KHẮC CHẾ: {data["name"].upper()} ({data["type"]})',
        description=(
            f'📍 **Vị trí thi đấu:** `{data["lane"].upper()}`\n\n'
            f'⚔️ **Top Tướng Khắc Chế (Hard Counters):**\n'
            f'👉 {", ".join([f"**{c}**" for c in data["counters"]])}\n\n'
            f'🛡️ **Điểm yếu then chốt:** {data["beaten_by"]}\n\n'
            f'💡 **Mẹo thi đấu Pro (VCS Playbook):**\n{data["vcs_tips"]}'
        ),
        color=COLOR_RED,
        timestamp=datetime.now()
    )
    embed.add_field(name='📦 Trang Bị Khắc Chế Khuyên Dùng', value=", ".join([f"`{it}`" for it in data["situational_items"]]), inline=False)
    embed.add_field(name='🤝 Tướng Đi Cùng Cực Mạnh (Synergies)', value=", ".join([f"`{s}`" for s in data["synergies"]]), inline=False)
    embed.set_footer(text='High Ego eSport • Cẩm Nang Chiến Thuật Đối Đầu')

    await interaction.response.send_message(embed=embed)


# ─────────────────────────── LỆNH 3: HIGH-ELO BUILD ───────────────────────────

@oracle_group.command(name='build', description='[Road to VCS] Giáo án trang bị High-Elo & Ngưỡng đột biến sức mạnh')
@app_commands.describe(tuong='Tên vị tướng muốn xem giáo án trang bị (VD: Azir, K\'Sante, Kalista, Rumble...)')
async def cmd_build(interaction: discord.Interaction, tuong: str):
    clean_name = tuong.lower().strip()
    data = None
    for key, c_info in odata.CHAMPIONS.items():
        if key == clean_name or clean_name in key:
            data = c_info
            break

    if not data:
        await interaction.response.send_message(f'❌ Chưa có dữ liệu giáo án cho `{tuong}`. Thử lại với các tướng hot pick: K\'Sante, Azir, Kalista, Sejuani, Yone...', ephemeral=True)
        return

    embed = discord.Embed(
        title=f'🛡️ GIÁO ÁN THI ĐẤU PRO: {data["name"].upper()}',
        description=f'**Đặc tính:** `{data["type"]}` | **Đường:** `{data["lane"].upper()}`',
        color=COLOR_CYAN,
        timestamp=datetime.now()
    )

    core_txt = "\n".join([f"`{idx+1}.` {it}" for idx, it in enumerate(data["core_items"])])
    embed.add_field(name='👑 Bộ 3 Trang Bị Cốt Lõi (Core 3 Items)', value=core_txt, inline=False)

    sit_txt = "\n".join([f"• {it}" for it in data["situational_items"]])
    embed.add_field(name='🔄 Nhánh Lên Đồ Phản Kích (Situational Tech)', value=sit_txt, inline=False)

    embed.add_field(name='⚡ Ngưỡng Đột Biến Sức Mạnh (Power Spikes)', value=data["vcs_tips"], inline=False)
    embed.set_footer(text='High Ego eSport • Competitive Itemization')

    await interaction.response.send_message(embed=embed)


# ─────────────────────────── LỆNH 4: META SYNERGY ───────────────────────────

@oracle_group.command(name='synergy', description='[Road to VCS] Các cặp đôi 2v2 và combo giao tranh thống trị meta VCS')
@app_commands.describe(loai_combo='Chọn loại bộ khung combo muốn tham khảo')
@app_commands.choices(loai_combo=[
    app_commands.Choice(name='🌲 Rừng & Đường Giữa (Mid - Jungle 2v2 Kings)', value='mid_jg'),
    app_commands.Choice(name='🏹 Đường Dưới (ADC - Support 2v2 Priority)', value='bot_duo'),
    app_commands.Choice(name='💥 Giao Tranh Tổng 5v5 (Womb-Combo Teamfight)', value='womb_combo'),
    app_commands.Choice(name='🏰 Đẩy Lẻ 1-3-1 & Cắt Cử (Split Push Skirmish)', value='split_push')
])
async def cmd_synergy(interaction: discord.Interaction, loai_combo: app_commands.Choice[str]):
    if loai_combo.value == 'mid_jg':
        embed = discord.Embed(
            title='🌲 BỘ KHUNG MID - JUNGLE 2v2 VÔ ĐỊCH VCS',
            description=(
                '**1. Sejuani + Yone / Sylas / Akali:**\n'
                '• Đánh giá: S+\n'
                '• Cơ chế: Nội tại Sejuani tích stack cực nhanh với các đòn đánh tay của Mid cận chiến. Đảm bảo 100% mạng khi gank level 3.\n\n'
                '**2. Jarvan IV + Orianna / Galio:**\n'
                '• Đánh giá: S\n'
                '• Cơ chế: Đại Địa Chấn (Jarvan R) gom đội hình đối phương cho Orianna kích hoạt Lệnh Sóng Âm (R) hoặc Galio giáng trần.\n\n'
                '**3. Renekton + Taliyah / Nidalee (VCS Classic):**\n'
                '• Đánh giá: S\n'
                '• Cơ chế: Choáng chỉ định W của Cá sấu setup cho Quăng Địa Chấn (W Taliyah) hoặc Phóng Lao (Q Nidalee) chuẩn xác tuyệt đối để Dive trụ.'
            ),
            color=COLOR_EMERALD,
            timestamp=datetime.now()
        )
    elif loai_combo.value == 'bot_duo':
        embed = discord.Embed(
            title='🏹 BỘ CẶP ĐÔI BOT LANE 2v2 ĐÈ ĐƯỜNG VCS',
            description=(
                '**1. Kalista + Renata Glasc / Nautilus:**\n'
                '• Đánh giá: S+\n'
                '• Cơ chế: Ép đường tuyệt đối từ cấp 1-3. Kiểm soát rồng và sứ giả. R Kalista ném Hỗ trợ vào giữa đội hình rồi bồi CC nối tiếp.\n\n'
                '**2. Lucian + Nami / Milio:**\n'
                '• Đánh giá: S\n'
                '• Cơ chế: Sốc sát thương trao đổi chiêu tức thì trong 0.5s. Áp đảo hoàn toàn các xạ thủ late game.\n\n'
                '**3. Ashe + Braum:**\n'
                '• Đánh giá: S\n'
                '• Cơ chế: Ashe bắn xa kích hoạt nội tại Choáng của Braum cực nhanh. Đại Băng Tiễn (R) mở góc giao tranh từ 2 màn hình.'
            ),
            color=COLOR_EMERALD,
            timestamp=datetime.now()
        )
    elif loai_combo.value == 'womb_combo':
        embed = discord.Embed(
            title='💥 BỘ KHUNG GIAO TRANH TỔNG 5v5 (WOMB-COMBO)',
            description=(
                '**Đội hình mẫu:** `Rumble (Top) + Jarvan IV (Jgl) + Orianna (Mid) + Miss Fortune / Varus (ADC) + Rell / Rakan (Sup)`\n\n'
                '• **Cách vận hành:**\n'
                '1. Ép góc đối thủ tại các địa hình hẹp (Cửa hang Rồng / Hang Baron).\n'
                '2. Rell / Jarvan mở giao tranh gom 3-4 thành viên địch.\n'
                '3. Orianna R + Rumble Rải Mưa Tên Lửa + Miss Fortune Bão Đạn hủy diệt hoàn toàn đối thủ trong 2 giây.'
            ),
            color=COLOR_EMERALD,
            timestamp=datetime.now()
        )
    else:
        embed = discord.Embed(
            title='🏰 BỘ KHUNG ĐẨY LẺ 1-3-1 (SPLIT PUSH)',
            description=(
                '**Đội hình mẫu:** `Fiora / Jax (Top) + Sejuani / Maokai (Jgl) + Azir / Corki (Mid) + Xayah / Varus (ADC) + Poppy / Braum (Sup)`\n\n'
                '• **Cách vận hành:**\n'
                '1. Đường Giữa & Đỡ đòn thủ trục giữa vững chắc không để bị ép giao tranh.\n'
                '2. Top đẩy lẻ cánh đối diện với mục tiêu lớn tiếp theo (Có Dịch Chuyển).\n'
                '3. Bắt buộc đối phương cử 2 người ra bắt lẻ, tạo tiền đề cho team 4 người ăn Baron hoặc Rồng miễn phí.'
            ),
            color=COLOR_EMERALD,
            timestamp=datetime.now()
        )

    embed.set_footer(text='High Ego eSport • Ban Huấn Luyện Road To VCS')
    await interaction.response.send_message(embed=embed)


# ─────────────────────────── LỆNH 5: LƯU & QUẢN LÝ BÀI ĐÁNH TEAM ───────────────────────────

@oracle_group.command(name='comp-save', description='[Role HE / Team] Lưu lại bài đánh / đội hình chiến thuật chuẩn của team')
@app_commands.describe(
    ten_bai_danh='Tên chiến thuật (VD: Bài Womb-Combo Hang Rồng, Bài 1-3-1 Fiora đẩy lẻ...)',
    top='Tướng Top',
    jungle='Tướng Rừng',
    mid='Tướng Mid',
    adc='Tướng ADC',
    support='Tướng Hỗ Trợ',
    loi_choi='Lối chơi (VD: Đánh xoay quanh bot, Snowball sứ giả...)',
    ghi_chu='Ghi chú thêm về cấm chọn hoặc điều kiện thắng'
)
async def cmd_comp_save(
    interaction: discord.Interaction,
    ten_bai_danh: str,
    top: str,
    jungle: str,
    mid: str,
    adc: str,
    support: str,
    loi_choi: str = "",
    ghi_chu: str = ""
):
    if not isinstance(interaction.user, discord.Member) or not has_he_role(interaction.user):
        await interaction.response.send_message('❌ Chỉ thành viên có role **HE** mới được lưu bài đánh chiến thuật!', ephemeral=True)
        return

    comp_id = db.save_comp(
        guild_id=interaction.guild_id,
        name=ten_bai_danh.strip(),
        top=top.strip().title(),
        jg=jungle.strip().title(),
        mid=mid.strip().title(),
        adc=adc.strip().title(),
        sup=support.strip().title(),
        playstyle=loi_choi.strip(),
        notes=ghi_chu.strip(),
        created_by=interaction.user.id
    )

    embed = discord.Embed(
        title=f'📁 ĐÃ LƯU BÀI ĐÁNH CHIẾN THUẬT: {ten_bai_danh.upper()}',
        description=(
            f'Mã bài đánh: `#{comp_id:03d}`\n\n'
            f'🛡️ **Top:** `{top.strip().title()}` | 🌲 **Jgl:** `{jungle.strip().title()}` | ⚡ **Mid:** `{mid.strip().title()}`\n'
            f'🏹 **ADC:** `{adc.strip().title()}` | 🛡️ **Sup:** `{support.strip().title()}`\n\n'
            f'📌 **Lối chơi:** {loi_choi or "Chưa ghi nhận"}\n'
            f'📝 **Ghi chú:** {ghi_chu or "Không có"}'
        ),
        color=COLOR_PURPLE,
        timestamp=datetime.now()
    )
    embed.set_footer(text='Dùng /oracle comp-list để xem tất cả bài đánh đã lưu.')
    await interaction.response.send_message(embed=embed)


@oracle_group.command(name='comp-list', description='Xem danh sách tất cả các bài đánh chiến thuật đã lưu của team')
async def cmd_comp_list(interaction: discord.Interaction):
    comps = db.list_saved_comps(interaction.guild_id)
    if not comps:
        await interaction.response.send_message('ℹ️ Hiện team chưa lưu bài đánh nào. Hãy dùng `/oracle comp-save` để tạo bài đánh đầu tiên!', ephemeral=True)
        return

    embed = discord.Embed(
        title='📋 DANH SÁCH BÀI ĐÁNH CHIẾN THUẬT TEAM ROAD TO VCS',
        description=f'Tổng cộng: `{len(comps)}` bộ khung chiến thuật',
        color=COLOR_PURPLE,
        timestamp=datetime.now()
    )

    for c in comps[:10]:
        embed.add_field(
            name=f'#{c["id"]:03d} • {c["name"]}',
            value=(
                f'🛡️ {c["top"]} | 🌲 {c["jungle"]} | ⚡ {c["mid"]} | 🏹 {c["adc"]} | 🛡️ {c["support"]}\n'
                f'💡 *{c["playstyle"] or "Không ghi chú"}*'
            ),
            inline=False
        )

    await interaction.response.send_message(embed=embed)


# ─────────────────────────── LỆNH 6: NHẬT KÝ SCRIMS & BÀI HỌC ───────────────────────────

@oracle_group.command(name='scrim-log', description='[Road to VCS] Ghi chép nhật ký phân tích & bài học rút ra sau trận Scrims')
@app_commands.describe(
    tieu_de='Tiêu đề buổi Scrims (VD: Scrim vs Team X trận 1)',
    team_ta='Đội hình team ta (VD: K\'Sante, Sejuani, Azir, Kalista, Nautilus)',
    team_dich='Đội hình đối phương (VD: Renekton, Nidalee, Tristana, Varus, Rell)',
    ket_qua='Kết quả trận đấu',
    bai_hoc_rut_ra='Bài học kinh nghiệm, sai lầm cần khắc phục hoặc điểm sáng'
)
@app_commands.choices(ket_qua=[
    app_commands.Choice(name='🏆 Chiến Thắng (Win)', value='win'),
    app_commands.Choice(name='💀 Thất Bại (Loss)', value='loss')
])
async def cmd_scrim_log(
    interaction: discord.Interaction,
    tieu_de: str,
    team_ta: str,
    team_dich: str,
    ket_qua: app_commands.Choice[str],
    bai_hoc_rut_ra: str
):
    if not isinstance(interaction.user, discord.Member) or not has_he_role(interaction.user):
        await interaction.response.send_message('❌ Chỉ thành viên mang **Role HE** mới có quyền ghi nhật ký Scrims!', ephemeral=True)
        return

    r_id = db.log_scrim(
        guild_id=interaction.guild_id,
        title=tieu_de.strip(),
        our_comp=team_ta.strip(),
        enemy_comp=team_dich.strip(),
        result=ket_qua.value,
        takeaway=bai_hoc_rut_ra.strip(),
        recorded_by=interaction.user.id
    )

    icon = '🏆 THẮNG' if ket_qua.value == 'win' else '💀 BẠI'
    color = COLOR_EMERALD if ket_qua.value == 'win' else COLOR_RED

    embed = discord.Embed(
        title=f'📝 NHẬT KÝ SCRIMS #{r_id:03d}: {tieu_de.strip()}',
        description=(
            f'**Kết quả:** `{icon}`\n\n'
            f'🟢 **Đội hình ta:** `{team_ta.strip()}`\n'
            f'🔴 **Đội hình đối thủ:** `{team_dich.strip()}`\n\n'
            f'💡 **Bài học rút ra & Phân tích chuyên môn:**\n{bai_hoc_rut_ra.strip()}'
        ),
        color=color,
        timestamp=datetime.now()
    )
    embed.set_footer(text=f'Ghi nhận bởi {interaction.user.display_name} • Road to VCS')
    await interaction.response.send_message(embed=embed)


@oracle_group.command(name='scrim-history', description='Xem lịch sử phân tích và bài học từ các trận Scrims gần nhất')
async def cmd_scrim_history(interaction: discord.Interaction):
    reports = db.list_scrim_reports(interaction.guild_id, limit=5)
    if not reports:
        await interaction.response.send_message('ℹ️ Hiện chưa có báo cáo Scrims nào. Dùng `/oracle scrim-log` sau mỗi trận tập luyện!', ephemeral=True)
        return

    embed = discord.Embed(
        title='📊 LỊCH SỬ THI ĐẤU SCRIMS GẦN NHẤT — ROAD TO VCS',
        description='Tổng hợp kinh nghiệm & bài học rút ra từ các trận đấu tập gần nhất:',
        color=COLOR_GOLD,
        timestamp=datetime.now()
    )

    for r in reports:
        icon = '🏆 THẮNG' if r['result'] == 'win' else '💀 THUA'
        embed.add_field(
            name=f'#{r["id"]:02d} • {r["title"]} ({icon})',
            value=(
                f'🟢 Ta: `{r["our_comp"]}`\n'
                f'🔴 Địch: `{r["enemy_comp"]}`\n'
                f'💡 *{r["key_takeaway"]}*'
            ),
            inline=False
        )

    await interaction.response.send_message(embed=embed)


bot.tree.add_command(oracle_group)

if __name__ == '__main__':
    if not BOT_TOKEN or BOT_TOKEN == 'YOUR_BOT_TOKEN_HERE':
        logger.error('BOT_TOKEN của HEe • Oracle chưa được cấu hình!')
        sys.exit(1)
    if not GUILD_ID:
        logger.error('GUILD_ID chưa được cấu hình!')
        sys.exit(1)
    bot.run(BOT_TOKEN, log_handler=None)
