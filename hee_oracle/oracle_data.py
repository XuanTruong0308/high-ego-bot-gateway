"""
oracle_data.py — Dữ liệu chiến thuật & Ma trận phân tích Meta LMHT Chuyên nghiệp (Road To VCS).
Bao gồm:
1. Thư viện tướng thi đấu (Role, Archetype, Tỷ lệ sát thương, Khống chế, Điểm rơi sức mạnh).
2. Ma trận khắc chế (Counter Picks, Cách kiểm soát lính, Kèo đấu kỹ năng).
3. Giáo án trang bị High-Elo & Tình huống đối đầu (Itemization, Power Spikes, Phản kích).
4. Phân tích đội hình 5 tướng (Damage Split, Win Condition, Điểm yếu, Đề xuất Ban/Pick).
5. Chiến thuật Macro Road to VCS (Kiểm soát Sâu hư không / Rồng, Cặp đôi Synergy 2v2).
"""

# Ma trận các tướng tiêu biểu trong Meta thi đấu chuyên nghiệp
CHAMPIONS = {
    # ─── TOP LANE ───
    "k'sante": {
        "name": "K'Sante", "lane": "top", "type": "Đỡ đòn / Đấu sĩ",
        "dmg_ad": 75, "dmg_ap": 25, "dmg_true": 0, "cc_level": 3, "engage": 2, "early": 2, "mid": 4, "late": 5,
        "counters": ["Gwen", "Fiora", "Vayne", "Poppy"],
        "beaten_by": "Sát thương theo % máu chuẩn hoặc cơ động thả diều né Q3/W.",
        "synergies": ["Sejuani", "Taliyah", "Orianna", "Tristana"],
        "core_items": ["Găng Tay Băng Hỏa", "Giáp Gai", "Giáp Tâm Linh / Jak'Sho"],
        "situational_items": ["Khiên Băng Randuin (chống chí mạng)", "Giáp Thiên Nhiên (chống cấu rỉa phép)"],
        "vcs_tips": "K'Sante đạt ngưỡng đột biến cấp 6 và khi hoàn thành món thủ đầu tiên. Tận dụng W chặn CC then chốt trước khi R kéo chủ lực địch qua tường cô lập."
    },
    "renekton": {
        "name": "Renekton", "lane": "top", "type": "Đấu sĩ càn quét",
        "dmg_ad": 85, "dmg_ap": 15, "dmg_true": 0, "cc_level": 2, "engage": 2, "early": 5, "mid": 4, "late": 2,
        "counters": ["Illaoi", "Quinn", "Kennen", "Poppy"],
        "beaten_by": "Thả diều tầm xa, câu kéo qua ngưỡng nộ và giai đoạn cấp 1-9.",
        "synergies": ["Nidalee", "Elise", "Taliyah", "Sejuani"],
        "core_items": ["Nguyệt Đao / Chùy Phản Kích", "Móng Vuốt Sterak", "Vũ Điệu Tử Thần"],
        "situational_items": ["Lời Nhắc Tử Vong / Cưa Xích Hóa Kỹ (trừ hồi máu)", "Giáp Gai"],
        "vcs_tips": "Đặc sản VCS: Cặp Renekton + Rừng sát thương AP (Nidalee/Taliyah) thiết lập Dive trụ từ đợt lính thứ 3. Ép đối thủ mất lính và sứ giả/sâu hư không đầu."
    },
    "rumble": {
        "name": "Rumble", "lane": "top", "type": "Pháp sư giao tranh tổng",
        "dmg_ad": 5, "dmg_ap": 95, "dmg_true": 0, "cc_level": 2, "engage": 3, "early": 5, "mid": 5, "late": 3,
        "counters": ["Tahm Kench", "Viktor", "Jayce", "Gwen"],
        "beaten_by": "Tướng chịu đòn hồi phục tốt hoặc tầm xa cấu rỉa không cho tích nhiệt.",
        "synergies": ["Jarvan IV", "Nocturne", "Varus", "Rell"],
        "core_items": ["Mặt Nạ Đọa Đày Liandry", "Đồng Hồ Cát Zhonya", "Trượng Hư Vô"],
        "situational_items": ["Ngọn Lửa Hắc Hóa", "Kính Nhắm Ma Pháp"],
        "vcs_tips": "Cấm/chọn cực mạnh ở VCS nhờ khả năng khép góc hang Rồng/Baron bằng Mưa Tên Lửa (R). Luôn giữ nhiệt 50%+ trước khi nổ giao tranh."
    },
    "aatrox": {
        "name": "Aatrox", "lane": "top", "type": "Đấu sĩ hồi phục",
        "dmg_ad": 90, "dmg_ap": 10, "dmg_true": 0, "cc_level": 2, "engage": 2, "early": 4, "mid": 5, "late": 3,
        "counters": ["Fiora", "Irelia", "Kled", "Malphite"],
        "beaten_by": "Trang bị Giảm Hồi Máu (Vết Thương Sâu 800g) ngay lần về đầu và tướng lướt né rìa Q.",
        "synergies": ["Maokai", "Ahri", "Nautilus", "Kai'Sa"],
        "core_items": ["Chùy Phản Kích / Nguyệt Đao", "Ngọn Giáo Shojin", "Móng Vuốt Sterak"],
        "situational_items": ["Cưa Xích Hóa Kỹ", "Rìu Đen (khi đối phương 2+ tank)"],
        "vcs_tips": "Quyết định giao tranh sứ giả phút thứ 8. Cần căn nhịp Q3 trúng tâm vào tuyến sau địch khi bật Chiến Binh Tận Thế."
    },
    "gnar": {
        "name": "Gnar", "lane": "top", "type": "Đấu sĩ đẩy lẻ / Mở giao tranh",
        "dmg_ad": 70, "dmg_ap": 25, "dmg_true": 5, "cc_level": 3, "engage": 4, "early": 3, "mid": 4, "late": 4,
        "counters": ["Irelia", "Yasuo", "Wukong", "Malphite"],
        "beaten_by": "Tướng áp sát dồn sát thương nhanh khi Gnar ở dạng Tí Nị hết nộ.",
        "synergies": ["Orianna", "Miss Fortune", "Jarvan IV"],
        "core_items": ["Tam Hợp Kiếm", "Móng Vuốt Sterak", "Giáp Gai"],
        "situational_items": ["Chùy Gai Malmortius", "Rìu Đen"],
        "vcs_tips": "Cực kỳ giá trị trong thế trận 1-3-1 kéo dài. Người chơi cần kiểm soát bình nộ ở mức 80-90% trước khi dịch chuyển giao tranh hang Baron."
    },

    "sett": {
        "name": "Sett", "lane": "top", "type": "Đấu sĩ càn lướt & Phản đòn sát thương chuẩn",
        "dmg_ad": 85, "dmg_ap": 0, "dmg_true": 15, "cc_level": 4, "engage": 4, "early": 5, "mid": 4, "late": 3,
        "counters": ["Renekton", "Jax", "K'Sante", "Aatrox"],
        "beaten_by": "Vayne, Quinn, Fiora (thả diều và chém % máu chuẩn né W Cuồng Thú), Renekton W phá khiên.",
        "synergies": ["Sejuani", "Jarvan IV", "Orianna", "Lulu", "Rakan"],
        "core_items": ["Chùy Phản Kích (Stridebreaker)", "Móng Vuốt Sterak", "Rìu Đại Mãng Xà / Tim Băng"],
        "situational_items": ["Giáp Gai", "Giáp Tâm Linh", "Giáp Liệt Sĩ", "Chùy Gai Malmortius"],
        "vcs_tips": "Đè đường cấp 1-2 với E + Đấm đôi nội tại. Trong combat, dùng R Hủy Diệt Đấu Trường ôm Tanker đối phương ném thẳng vào tuyến sau của địch, sau đó tích đầy Nộ bấm W dồn sát thương chuẩn sốc chết Xạ thủ / Pháp sư đối phương."
    },
    "jax": {
        "name": "Jax", "lane": "top", "type": "Đấu sĩ đẩy lẻ & Đấu tay đôi vô địch Late Game",
        "dmg_ad": 65, "dmg_ap": 35, "dmg_true": 0, "cc_level": 3, "engage": 3, "early": 3, "mid": 4, "late": 5,
        "counters": ["Camille", "Fiora", "Irelia", "K'Sante"],
        "beaten_by": "Gragas, Poppy, Malphite (chặn lướt Q và làm chậm tốc độ đánh).",
        "synergies": ["Sejuani", "Vi", "Orianna", "Ahri"],
        "core_items": ["Tam Hợp Kiếm", "Ngọn Giáo Shojin / Rìu Đen", "Móng Vuốt Sterak"],
        "situational_items": ["Tim Băng", "Đồng Hồ Cát Zhonya", "Giáp Tâm Linh"],
        "vcs_tips": "Vua đẩy lẻ cánh 1-3-1. Phản Công (E) né toàn bộ đòn đánh tay của Xạ thủ, R gia tăng giáp/kháng phép khổng lồ khi lao vào giữa đội hình đối phương."
    },
    "darius": {
        "name": "Darius", "lane": "top", "type": "Đấu sĩ càn quét & Máy chém sát thương chuẩn",
        "dmg_ad": 85, "dmg_ap": 0, "dmg_true": 15, "cc_level": 3, "engage": 2, "early": 5, "mid": 4, "late": 3,
        "counters": ["Sion", "Cho'Gath", "Shen", "Malphite"],
        "beaten_by": "Quinn, Vayne, Jayce (thả diều tầm xa không cho tích 5 điểm Xuất Huyết).",
        "synergies": ["Tốc Hành", "Jarvan IV", "Nautilus", "Lulu"],
        "core_items": ["Chùy Phản Kích", "Móng Vuốt Sterak", "Giáp Liệt Sĩ"],
        "situational_items": ["Giáp Gai", "Khiên Băng Randuin", "Chùy Gai Malmortius"],
        "vcs_tips": "Bật Tốc Hành ngay khi đối phương vượt nửa đường để dí tới cùng. Trong giao tranh, tích 5 tầng nội tại lên tướng đỡ đòn tuyến đầu trước, sau đó Tốc Biến R chém reset liên hoàn tuyến sau."
    },

    # ─── JUNGLE ───
    "lee sin": {
        "name": "Lee Sin", "lane": "jungle", "type": "Đấu sĩ kiểm soát đầu game & Mở combat Insec",
        "dmg_ad": 95, "dmg_ap": 5, "dmg_true": 0, "cc_level": 3, "engage": 5, "early": 5, "mid": 4, "late": 2,
        "counters": ["Nidalee", "Karthus", "Viego", "Kayn"],
        "beaten_by": "Poppy (W chặn lướt Q2/W), Rammus, Trundle (tay đôi khỏe hơn khi về mid game).",
        "synergies": ["Yasuo", "Orianna", "Ahri", "Renekton"],
        "core_items": ["Nguyệt Đao / Chùy Mãng Xà", "Rìu Đen", "Móng Vuốt Sterak"],
        "situational_items": ["Giáp Thiên Thần", "Chùy Gai Malmortius", "Vũ Điệu Tử Thần"],
        "vcs_tips": "Tạo sức ép gank cực sớm phút 2:40 - 3:00. Combo Q1 -> Cắm Mắt W ra sau lưng -> R Nộ Long Cước sút chủ lực đối phương về cho team dứt điểm."
    },
    "viego": {
        "name": "Viego", "lane": "jungle", "type": "Sát thủ chiếm xác & Lật kèo giao tranh liên hoàn",
        "dmg_ad": 90, "dmg_ap": 5, "dmg_true": 5, "cc_level": 2, "engage": 3, "early": 3, "mid": 5, "late": 4,
        "counters": ["Jarvan IV", "Graves", "Lee Sin", "Sejuani"],
        "beaten_by": "Khống chế cứng sốc chết trước khi kịp kích hoạt nội tại đoạt mệnh chiếm xác.",
        "synergies": ["Nautilus", "Renekton", "Ahri", "Rakan"],
        "core_items": ["Gươm Suy Hao", "Tam Hợp Kiếm / Móc Diệt", "Móng Vuốt Sterak"],
        "situational_items": ["Vũ Điệu Tử Thần", "Chùy Gai Malmortius", "Giáp Thiên Thần"],
        "vcs_tips": "Chờ đồng đội tạo mạng hạ gục đầu tiên, lướt vào chiếm xác lấy miễn nhiễm sát thương và reset chiêu cuối Tuyệt Mệnh (R) để quét sạch combat."
    },
    "sejuani": {
        "name": "Sejuani", "lane": "jungle", "type": "Đỡ đòn mở giao tranh",
        "dmg_ad": 10, "dmg_ap": 90, "dmg_true": 0, "cc_level": 5, "engage": 4, "early": 3, "mid": 5, "late": 4,
        "counters": ["Trundle", "Olaf", "Kindred", "Lillia"],
        "beaten_by": "Tướng cướp rừng mạnh đầu game hoặc kháng CC càn lướt (Olaf).",
        "synergies": ["Yone", "Sylas", "Akali", "Renekton", "Melee Solo Laners"],
        "core_items": ["Trái Tim Khổng Lồ / Băng Giáp", "Giáp Gai", "Giáp Tâm Linh"],
        "situational_items": ["Dây Chuyền Chuộc Tội", "Lời Thề Hiệp Sĩ"],
        "vcs_tips": "Trụ cột ban/pick: Tích stack nội tại cực nhanh khi đánh cùng mid/top cận chiến. Chiêu cuối R bắt lẻ chủ lực đối phương ở cự ly xa."
    },
    "jarvan iv": {
        "name": "Jarvan IV", "lane": "jungle", "type": "Đấu sĩ mở giao tranh Womb-Combo",
        "dmg_ad": 90, "dmg_ap": 10, "dmg_true": 0, "cc_level": 4, "engage": 5, "early": 5, "mid": 4, "late": 2,
        "counters": ["Poppy", "Gragas", "Vayne", "Viego"],
        "beaten_by": "Poppy (chặn E-Q), các tướng cơ động nhảy qua được Đại Địa Chấn (R).",
        "synergies": ["Orianna", "Rumble", "Miss Fortune", "Galio"],
        "core_items": ["Ngọn Giáo Shojin", "Nguyệt Đao / Chùy Phản Kích", "Móng Vuốt Sterak"],
        "situational_items": ["Khiên Băng Randuin", "Giáp Gai"],
        "vcs_tips": "Khởi động gank level 2 hoặc level 3 cực gắt. Combo R nhốt ép Tốc Biến của xạ thủ địch tạo tiền đề cho các ulti diện rộng bồi vào."
    },
    "vi": {
        "name": "Vi", "lane": "jungle", "type": "Đấu sĩ bắt chết chủ lực (Point & Click)",
        "dmg_ad": 85, "dmg_ap": 5, "dmg_true": 10, "cc_level": 4, "engage": 5, "early": 4, "mid": 5, "late": 3,
        "counters": ["Morgana", "Nocturne", "Poppy", "Jax"],
        "beaten_by": "Khiên đen Morgana, Dây Chuyền Chữ Thập, hoặc team bảo kê chặt.",
        "synergies": ["Ahri", "Taliyah", "Kai'Sa", "Varus"],
        "core_items": ["Tam Hợp Kiếm", "Móng Vuốt Sterak", "Khiên Băng / Giáp Gai"],
        "situational_items": ["Ngọn Giáo Shojin", "Chùy Gai Malmortius"],
        "vcs_tips": "Khắc chế cứng các siêu xạ thủ không có kỹ năng lướt (Jinx, Aphelios). R Tả Xung Hữu Đột không thể bị cản phá."
    },
    "maokai": {
        "name": "Maokai", "lane": "jungle", "type": "Kiểm soát bản đồ & Tầm nhìn",
        "dmg_ad": 10, "dmg_ap": 90, "dmg_true": 0, "cc_level": 5, "engage": 4, "early": 3, "mid": 5, "late": 4,
        "counters": ["Sylas", "Trundle", "Graves", "Lillia"],
        "beaten_by": "Sylas cướp ulti Maokai phản công, Trundle hút hết giáp/kháng phép.",
        "synergies": ["Jayce", "Tristana", "Corki", "Lucian"],
        "core_items": ["Băng Giáp", "Giáp Gai", "Mặt Nạ Liandry (tùy biến)"],
        "situational_items": ["Giáp Tâm Linh", "Trái Tim Khổng Lồ"],
        "vcs_tips": "Chồi non E lấy thông tin bụi trước 1 phút giao tranh rồng/baron. Không bao giờ để đối phương phục kích."
    },
    "nidalee": {
        "name": "Nidalee", "lane": "jungle", "type": "Sát thủ cấu rỉa Snowball",
        "dmg_ad": 5, "dmg_ap": 95, "dmg_true": 0, "cc_level": 0, "engage": 1, "early": 5, "mid": 4, "late": 2,
        "counters": ["Nocturne", "Xin Zhao", "Jarvan IV", "Vi"],
        "beaten_by": "Tướng mở giao tranh thẳng mặt, không cho khoảng trống để ném lao cấu rỉa.",
        "synergies": ["Renekton", "Nautilus", "Twisted Fate", "Pantheon"],
        "core_items": ["Ngọn Lửa Hắc Hóa", "Kiếm Tai Ương", "Đồng Hồ Cát Zhonya"],
        "situational_items": ["Trượng Hư Vô", "Mũ Phù Thủy Rabadon"],
        "vcs_tips": "Yêu cầu kỹ năng cá nhân cực cao. Chỉ pick khi có đường có khống chế cứng chắc chắn (Renekton/Nautilus) để setup lao trúng."
    },

    # ─── MID LANE ───
    "yasuo": {
        "name": "Yasuo", "lane": "mid", "type": "Đấu sĩ cơ động & Tường gió khắc chế xạ thủ",
        "dmg_ad": 95, "dmg_ap": 5, "dmg_true": 0, "cc_level": 3, "engage": 4, "early": 3, "mid": 4, "late": 5,
        "counters": ["Syndra", "Twisted Fate", "Ahri", "Varus"],
        "beaten_by": "Renekton, Pantheon, Malzahar (CC chỉ định cứng khóa chết lướt).",
        "synergies": ["Gragas", "Diana", "Malphite", "Lee Sin", "Nautilus"],
        "core_items": ["Gươm Suy Hao / Móc Diệt Thủy Quái", "Vô Cực Kiếm", "Móng Vuốt Sterak"],
        "situational_items": ["Nỏ Tử Thủ", "Vũ Điệu Tử Thần", "Giáp Thiên Thần"],
        "vcs_tips": "Tường Gió (W) chặn hoàn toàn đạn đạo của Xạ thủ đối phương. Phối hợp combo hất tung cùng Rừng (Gragas E-R, Lee Sin R, Diana R) kích hoạt Trăn Trối quét sạch đội hình."
    },
    "sylas": {
        "name": "Sylas", "lane": "mid", "type": "Pháp sư cận chiến cướp chiêu cuối & Lật kèo giao tranh",
        "dmg_ad": 5, "dmg_ap": 95, "dmg_true": 0, "cc_level": 3, "engage": 4, "early": 3, "mid": 5, "late": 4,
        "counters": ["Malphite", "Sejuani", "Ashe", "Nautilus"],
        "beaten_by": "Cassiopeia, Vex, Galio (chống lao vào và cản lướt E).",
        "synergies": ["Sejuani", "Jarvan IV", "Maokai", "Lee Sin"],
        "core_items": ["Đai Lưng Hextech / Ngọn Lửa Hắc Hóa", "Đồng Hồ Cát Zhonya", "Mũ Phù Thủy Rabadon"],
        "situational_items": ["Mặt Nạ Liandry", "Kính Nhắm Ma Pháp", "Trượng Hư Vô"],
        "vcs_tips": "Quân bài khắc chế cướp chiêu cuối giá trị cao (R Malphite, R Sejuani, R Alistar, R Ashe). Lướt E2 căn trúng để hồi máu W lật kèo khi còn dưới 30% máu."
    },
    "azir": {
        "name": "Azir", "lane": "mid", "type": "Pháp sư kiểm soát Late Game",
        "dmg_ad": 5, "dmg_ap": 95, "dmg_true": 0, "cc_level": 3, "engage": 3, "early": 2, "mid": 4, "late": 5,
        "counters": ["Syndra", "Jayce", "Viktor", "Xerath"],
        "beaten_by": "Tầm đánh xa hơn đè đường đầu game (Syndra/Jayce).",
        "synergies": ["Sejuani", "Jarvan IV", "Maokai", "K'Sante"],
        "core_items": ["Nanh Nashor", "Đồng Hồ Cát Zhonya", "Mũ Phù Thủy Rabadon"],
        "situational_items": ["Ngọn Lửa Hắc Hóa", "Trượng Hư Vô", "Dây Chuyền Chữ Thập"],
        "vcs_tips": "Lựa chọn tiêu chuẩn của các giải đấu lớn. Đẩy đường an toàn, dọn lính chống đẩy trụ và chiêu cuối Shurima Shuffle lật ngược thế cờ."
    },
    "orianna": {
        "name": "Orianna", "lane": "mid", "type": "Pháp sư giao tranh tổng cổ điển",
        "dmg_ad": 5, "dmg_ap": 95, "dmg_true": 0, "cc_level": 3, "engage": 3, "early": 3, "mid": 4, "late": 5,
        "counters": ["Syndra", "Zed", "Akali", "Tristana"],
        "beaten_by": "Sát thủ cơ động nhảy né Cầu và dồn sát thương sốc.",
        "synergies": ["Jarvan IV", "Rengar", "Malphite", "Nocturne"],
        "core_items": ["Vọng Âm Luden / Trượng Trường Sinh", "Ngọn Lửa Hắc Hóa", "Đồng Hồ Cát Zhonya"],
        "situational_items": ["Mũ Phù Thủy Rabadon", "Trượng Hư Vô"],
        "vcs_tips": "Bộ đôi Ball-Delivery huyền thoại với Jarvan IV / Nocturne. Cần giữ vị trí tối đa, không để bị bắt lẻ trước giao tranh."
    },
    "yone": {
        "name": "Yone", "lane": "mid", "type": "Sát thủ / Đấu sĩ càn quét",
        "dmg_ad": 70, "dmg_ap": 25, "dmg_true": 5, "cc_level": 3, "engage": 4, "early": 2, "mid": 4, "late": 5,
        "counters": ["Renekton", "Pantheon", "Vex", "Akali"],
        "beaten_by": "Khống chế cứng chỉ định (Point & click stun) và dồn sát thương sốc trước khi hút máu.",
        "synergies": ["Sejuani", "Maokai", "Rakan", "Alistar"],
        "core_items": ["Gươm Suy Hao / Móc Diệt Thủy Quái", "Vô Cực Kiếm", "Móng Vuốt Sterak / Khiên Băng"],
        "situational_items": ["Nỏ Tử Thủ", "Giáp Gai"],
        "vcs_tips": "Pick cực mạnh để chia cắt đội hình và đẩy lẻ 1-3-1. Chú ý quay về xác E đúng lúc để tránh bị CC dồn vào vị trí ban đầu."
    },
    "taliyah": {
        "name": "Taliyah", "lane": "mid", "type": "Pháp sư đảo đường & Chặn lướt",
        "dmg_ad": 5, "dmg_ap": 95, "dmg_true": 0, "cc_level": 3, "engage": 3, "early": 4, "mid": 5, "late": 4,
        "counters": ["Kassadin", "Zed", "Fizz", "Lucian"],
        "beaten_by": "Sát thủ vượt tường dồn damage né thảm đá E.",
        "synergies": ["Renekton", "Nautilus", "Vi", "Pantheon"],
        "core_items": ["Ngọn Lửa Hắc Hóa", "Đồng Hồ Cát Zhonya", "Trượng Hư Vô"],
        "situational_items": ["Mặt Nạ Liandry", "Mũ Phù Thủy"],
        "vcs_tips": "Bức tường R Mặt Đất Vỡ Vụn chia cắt hoàn toàn giao tranh hang rồng. Thảm đá E khắc chế cứng các đội hình lướt (Zeri, Rakan, Lee Sin)."
    },
    "tristana": {
        "name": "Tristana", "lane": "mid", "type": "Xạ thủ đè đường & Phá trụ",
        "dmg_ad": 95, "dmg_ap": 5, "dmg_true": 0, "cc_level": 1, "engage": 3, "early": 5, "mid": 4, "late": 4,
        "counters": ["Yasuo", "Malphite", "Diana", "Cassiopeia"],
        "beaten_by": "Tường gió Yasuo, khống chế cứng không cho bật nhảy W.",
        "synergies": ["Maokai", "Sejuani", "Ivern", "Rakan"],
        "core_items": ["Móc Diệt Thủy Quái", "Đoản Đao Navori", "Vô Cực Kiếm"],
        "situational_items": ["Nỏ Thiện Xạ / Nỏ Tử Thủ", "Đao Thủy Ngân"],
        "vcs_tips": "Tạo áp lực dồn lính lấy khiên trụ cấp 1-6. Cho phép team ăn sâu hư không và mở toang mid sớm."
    },

    # ─── ADC / BOT ───
    "kalista": {
        "name": "Kalista", "lane": "adc", "type": "Xạ thủ đè đường & Kiểm soát mục tiêu",
        "dmg_ad": 90, "dmg_ap": 0, "dmg_true": 10, "cc_level": 3, "engage": 4, "early": 5, "mid": 4, "late": 2,
        "counters": ["Ashe", "Nasus", "Varus", "Senna"],
        "beaten_by": "Làm chậm tốc đánh/tốc chạy (Slow làm Kalista giảm tốc độ nhảy), cấu rỉa tầm xa.",
        "synergies": ["Renata Glasc", "Nautilus", "Thresh", "Blitzcrank"],
        "core_items": ["Gươm Suy Hao", "Cuồng Đao Guinsoo", "Đao Tím / Nỏ Tử Thủ"],
        "situational_items": ["Nỏ Thiện Xạ", "Giáp Thiên Thần"],
        "vcs_tips": "Vua tranh chấp mục tiêu (Trừng phạt E Giày Vò không thể bị cướp). R Cứu Rỗi kết hợp Nautilus/Renata tạo chuỗi CC không lối thoát."
    },
    "varus": {
        "name": "Varus", "lane": "adc", "type": "Xạ thủ cấu rỉa / Hiệu ứng khống chế",
        "dmg_ad": 60, "dmg_ap": 40, "dmg_true": 0, "cc_level": 3, "engage": 3, "early": 5, "mid": 4, "late": 4,
        "counters": ["Samira", "Yasuo", "Braum", "Tristana"],
        "beaten_by": "Tường gió/Khiên Braum chặn Q và R, tướng lao vào áp sát nhanh.",
        "synergies": ["Ashe", "Rumble", "Renata Glasc", "Karma"],
        "core_items": ["Gươm Suy Hao / Kiếm Ma Youmuu", "Cuồng Đao Guinsoo", "Nỏ Thiện Xạ"],
        "situational_items": ["Đồng Hồ Cát Zhonya (lối lên đồ On-hit hybrid AP)", "Đao Thủy Ngân"],
        "vcs_tips": "Đa dụng bậc nhất: Có thể đánh cấu rỉa Poke hoặc On-hit diệt Tank. Chiêu cuối Sợi Xích Tội Lỗi là công cụ mở/phản giao tranh tuyệt hảo."
    },
    "ashe": {
        "name": "Ashe", "lane": "adc", "type": "Xạ thủ kiểm soát & Mở giao tranh tầm xa",
        "dmg_ad": 90, "dmg_ap": 10, "dmg_true": 0, "cc_level": 4, "engage": 5, "early": 4, "mid": 4, "late": 4,
        "counters": ["Braum", "Yasuo", "Samira", "Sivir"],
        "beaten_by": "Khiên Braum chặn tên, Khiên chống phép Sivir, tướng lao vào dồn sát thương.",
        "synergies": ["Braum", "Varus", "Renata Glasc", "Maokai"],
        "core_items": ["Móc Diệt Thủy Quái", "Ma Vũ Song Kiếm", "Vô Cực Kiếm"],
        "situational_items": ["Gươm Suy Hao", "Nỏ Thiện Xạ", "Đao Thủy Ngân"],
        "vcs_tips": "Ưng Tiễn (E) soi sáng vị trí rừng đối phương loại bỏ hoàn toàn yếu tố bất ngờ. Đại Băng Tiễn (R) là công cụ mở giao tranh từ xa số 1 LMHT."
    },
    "kai'sa": {
        "name": "Kai'Sa", "lane": "adc", "type": "Xạ thủ ám sát & Linh hoạt vị trí",
        "dmg_ad": 50, "dmg_ap": 45, "dmg_true": 5, "cc_level": 0, "engage": 3, "early": 2, "mid": 4, "late": 5,
        "counters": ["Caitlyn", "Draven", "Lucian", "Kalista"],
        "beaten_by": "Các xạ thủ tầm xa đè đường cực mạnh đầu game không cho tích tiến hóa.",
        "synergies": ["Nautilus", "Rell", "Leona", "Vi"],
        "core_items": ["Móc Diệt Thủy Quái", "Nanh Nashor", "Cuồng Đao Guinsoo"],
        "situational_items": ["Đồng Hồ Cát Zhonya", "Dây Chuyền Chữ Thập", "Mũ Phù Thủy"],
        "vcs_tips": "Cực kỳ hợp meta VCS với lối chơi giao tranh liên tục. Bay vào tuyến sau bằng R khi có đồng đội kích hoạt khống chế cứng."
    },

    # ─── SUPPORT ───
    "nautilus": {
        "name": "Nautilus", "lane": "support", "type": "Đỡ đòn mở giao tranh & Khóa mục tiêu",
        "dmg_ad": 10, "dmg_ap": 90, "dmg_true": 0, "cc_level": 5, "engage": 5, "early": 5, "mid": 4, "late": 3,
        "counters": ["Morgana", "Braum", "Renata Glasc", "Poppy"],
        "beaten_by": "Khiên đen Morgana chặn R, Braum chặn kéo và phản công.",
        "synergies": ["Kai'Sa", "Kalista", "Samira", "Tristana"],
        "core_items": ["Dây Chuyền Solari", "Lời Thề Hiệp Sĩ", "Giáp Gai"],
        "situational_items": ["Bình Thải Hóa Dược / Giáp Tâm Linh"],
        "vcs_tips": "Chiêu cuối R Thủy Lôi Tầm Nhiệt là án tử cho các xạ thủ cơ động. Đảo đường ra Mid/Sâu hư không cùng Rừng ở phút thứ 6."
    },
    "renata glasc": {
        "name": "Renata Glasc", "lane": "support", "type": "Hỗ trợ phản giao tranh & Cứu nguy",
        "dmg_ad": 5, "dmg_ap": 95, "dmg_true": 0, "cc_level": 4, "engage": 2, "early": 3, "mid": 5, "late": 5,
        "counters": ["Soraka", "Milio", "Janna", "Karma"],
        "beaten_by": "Hỗ trợ cấu rỉa tầm xa giải trừ khống chế (Milio R giải toàn bộ ulti Renata).",
        "synergies": ["Kalista", "Varus", "Ashe", "Jinx"],
        "core_items": ["Dây Chuyền Solari", "Dây Chuyền Chuộc Tội", "Trượng Lưu Thủy"],
        "situational_items": ["Vương Miện Shurelya", "Tim Băng"],
        "vcs_tips": "Khắc chế cứng các đội hình lao vào đánh cận chiến hoặc nhiều tốc đánh (Master Yi, Yone, Tristana). R Hợp Đồng Vay Nợ biến sát thương đối thủ thành vũ khí tự hủy."
    },
    "rakan": {
        "name": "Rakan", "lane": "support", "type": "Mở giao tranh cơ động & Bảo kê",
        "dmg_ad": 10, "dmg_ap": 90, "dmg_true": 0, "cc_level": 4, "engage": 5, "early": 3, "mid": 5, "late": 4,
        "counters": ["Poppy", "Janna", "Thresh", "Morgana"],
        "beaten_by": "Poppy W chặn toàn bộ lướt W và E của Rakan; Gió mùa Janna hất văng.",
        "synergies": ["Xayah", "Kai'Sa", "Orianna", "Yone"],
        "core_items": ["Vương Miện Shurelya", "Dây Chuyền Chuộc Tội", "Dây Chuyền Solari"],
        "situational_items": ["Bình Thải Hóa Dược", "Lời Thề Hiệp Sĩ"],
        "vcs_tips": "Combo Tốc Biến + R + W là công cụ mở giao tranh bất ngờ nhất giải đấu. Cực kỳ nguy hiểm khi kết hợp cùng Cầu Orianna hoặc Yone."
    },
    "braum": {
        "name": "Braum", "lane": "support", "type": "Vệ binh bảo kê & Chặn kỹ năng",
        "dmg_ad": 10, "dmg_ap": 90, "dmg_true": 0, "cc_level": 4, "engage": 2, "early": 3, "mid": 4, "late": 5,
        "counters": ["Senna", "Zyra", "Karma", "Lulu"],
        "beaten_by": "Các hỗ trợ cấu rỉa phép tầm xa bào mòn máu từ đầu game.",
        "synergies": ["Lucian", "Ashe", "Varus", "Jinx"],
        "core_items": ["Dây Chuyền Solari", "Lời Thề Hiệp Sĩ", "Tim Băng / Giáp Gai"],
        "situational_items": ["Dây Chuyền Chuộc Tội"],
        "vcs_tips": "Lá chắn E Tối Kiên Cường chặn đứng toàn bộ đạn pháo của Ornn, Ezreal, Nami, Miss Fortune. Khắc chế triệt để đội hình Poke và Kalista."
    }
}


def analyze_composition(top: str, jg: str, mid: str, adc: str, sup: str) -> dict:
    """
    Phân tích đội hình 5 người chuẩn VCS:
    - Tính toán tỷ lệ sát thương AD / AP / True Dmg.
    - Đánh giá khả năng mở giao tranh (Engage) và Khống chế cứng (Hard CC).
    - Đo lường đường cong sức mạnh theo thời gian (Early, Mid, Late).
    - Nhận diện lối chơi cốt lõi (Teamfight, 1-3-1, Dive, Poke, Pick-off).
    - Phát hiện điểm yếu chí mạng & Đề xuất tướng cần cấm (Target Bans).
    """
    roles = {"top": top.lower().strip(), "jungle": jg.lower().strip(), "mid": mid.lower().strip(), "adc": adc.lower().strip(), "support": sup.lower().strip()}
    
    total_ad = 0
    total_ap = 0
    total_true = 0
    cc_score = 0
    engage_score = 0
    early_score = 0
    mid_score = 0
    late_score = 0
    
    recognized_champs = []
    missing_champs = []

    for role_name, c_name in roles.items():
        found = None
        for key, data in CHAMPIONS.items():
            if key == c_name or c_name in key:
                found = data
                break
        
        if found:
            recognized_champs.append(found)
            total_ad += found["dmg_ad"]
            total_ap += found["dmg_ap"]
            total_true += found["dmg_true"]
            cc_score += found["cc_level"]
            engage_score += found["engage"]
            early_score += found["early"]
            mid_score += found["mid"]
            late_score += found["late"]
        else:
            missing_champs.append(c_name.capitalize())
            # Default fallback generic stats
            total_ad += 50
            total_ap += 50
            cc_score += 2
            engage_score += 2
            early_score += 3
            mid_score += 3
            late_score += 3

    # Normalize damage percentages
    total_dmg = max(1, total_ad + total_ap + total_true)
    pct_ad = round((total_ad / total_dmg) * 100)
    pct_ap = round((total_ap / total_dmg) * 100)
    pct_true = 100 - pct_ad - pct_ap

    # Xác định chiến thuật chính (Archetype)
    archetype = "Giao Tranh Tổng (5v5 Teamfight)"
    win_con = "Đánh xoay quanh các mục tiêu lớn (Rồng 3, Sứ giả, Baron), thiết lập giao tranh tổng diện rộng."
    
    if engage_score >= 18:
        archetype = "⚡ Bắt Lẻ & Băng Trụ Thần Tốc (Hard Engage / Pick-off)"
        win_con = "Kiểm soát tầm nhìn rừng đối phương, dùng CC đơn mục tiêu bắt lẻ chủ lực trước khi mục tiêu lớn xuất hiện."
    elif cc_score >= 18:
        archetype = "🛡️ Giao Tranh Chặn Đứng & Bảo Kê (Front-to-Back Teamfight)"
        win_con = "Dựng dàn chắn vững chắc phía trước, để xạ thủ và pháp sư xả sát thương tự do trong giao tranh dài hơi."
    elif any(c.get("name") in ["Fiora", "Camille", "Jax", "Yone", "Gnar"] for c in recognized_champs):
        archetype = "🗡️ Đẩy Lẻ Cánh & Phân Tỏa Áp Lực (1-3-1 Split Push)"
        win_con = "Kiểm soát tầm nhìn hai cánh, kéo dãn đội hình đối phương để đấu sĩ cánh đẩy đổ trụ và cô lập đối thủ."

    # Cảnh báo điểm yếu
    warnings = []
    if pct_ad >= 80:
        warnings.append("⚠️ **NGUY HIỂM: Full Sát Thương Vật Lý (AD).** Đối phương chỉ cần lên Giáp Gai + Tim Băng + Giày Thép Gai sẽ hoàn toàn vô hiệu hóa sát thương của team.")
    elif pct_ap >= 75:
        warnings.append("⚠️ **NGUY HIỂM: Full Sát Thương Phép (AP).** Đối phương lên Giáp Tâm Linh + Dây Chuyền Chữ Thập + Jak'Sho sẽ vô cùng cứng cáp.")
    
    if cc_score <= 10:
        warnings.append("⚠️ **THIẾU KHỐNG CHẾ CỨNG (Hard CC).** Đội hình sẽ bất lực trước các sát thủ cơ động hoặc đấu sĩ càn quét như Yone, Irelia, Master Yi.")

    if engage_score <= 10:
        warnings.append("⚠️ **THIẾU CÔNG CỤ MỞ GIAO TRANH.** Đội hình dễ bị rơi vào thế bị động, bị đối phương thả diều câu kéo và ép góc tại hang rồng.")

    # Target bans gợi ý
    target_bans = set()
    for c in recognized_champs:
        for ban in c.get("counters", []):
            target_bans.add(ban)

    return {
        "pct_ad": pct_ad,
        "pct_ap": pct_ap,
        "pct_true": pct_true,
        "cc_score": cc_score,
        "engage_score": engage_score,
        "early": early_score,
        "mid": mid_score,
        "late": late_score,
        "archetype": archetype,
        "win_con": win_con,
        "warnings": warnings,
        "target_bans": list(target_bans)[:4],
        "missing_champs": missing_champs
    }


# ─────────────────────────── MA TRẬN POWER PICKS & COUNTERS THEO LANE ───────────────────────────

POWER_PICKS = {
    "top": [
        {
            "name": "Rumble", "tier": "S+ (God Tier)", "win_rate": "53.2%", "ban_rate": "42%",
            "why_hot": "Hưởng lợi lớn từ buff Mặt Nạ Liandry và khả năng ép góc tuyệt đối tại hang Sâu Hư Không & Rồng bằng Mưa Tên Lửa (R).",
            "core_build": "Mặt Nạ Liandry ➔ Đồng Hồ Cát Zhonya ➔ Trượng Hư Vô",
            "runes": "Thiên Thạch Bí Ẩn • Áo Choàng Mây • Tập Trung Tuyệt Đối • Thiêu Rụi",
            "counters": [
                {"champ": "Tahm Kench", "wr": "55.4%", "reason": "Quá trâu bò, nuốt cô lập và nuốt đồng đội cứu khỏi Mưa Tên Lửa."},
                {"champ": "Jayce", "wr": "53.8%", "reason": "Đẩy lính và cấu rỉa tầm xa ngoài tầm phun lửa của Rumble."},
                {"champ": "Gwen", "wr": "53.1%", "reason": "Sương Lam Bất Tử (W) miễn nhiễm hoàn toàn chiêu cuối của Rumble từ xa."}
            ],
            "counter_strategy": "Lên Giày Thủy Ngân + Áo Choàng Ám Ảnh lần về đầu. Ép giao tranh khi Nhiệt của Rumble dưới 40% hoặc khi hắn vừa quá nhiệt tự câm lặng."
        },
        {
            "name": "K'Sante", "tier": "S+ (Pro Priority)", "win_rate": "51.8%", "ban_rate": "48%",
            "why_hot": "Độ đa dụng tối đa trong thi đấu chuyên nghiệp: Vừa là Đỡ Đòn vững chắc vừa có thể bật Khô Máu (R) thành Đấu Sĩ sát thủ.",
            "core_build": "Găng Tay Băng Hỏa ➔ Giáp Gai ➔ Băng Giáp / Jak'Sho",
            "runes": "Quyền Năng Bất Diệt • Tàn Phá Hủy Diệt • Ngọn Gió Thứ Hai • Lan Tràn",
            "counters": [
                {"champ": "Gwen", "wr": "54.8%", "reason": "Sát thương theo % máu chuẩn xuyên qua toàn bộ lượng giáp của K'Sante."},
                {"champ": "Fiora", "wr": "54.2%", "reason": "Phản Đòn (W) chặn W/Q3 của K'Sante, chém điểm yếu sát thương chuẩn."},
                {"champ": "Poppy", "wr": "53.9%", "reason": "Không Thể Lay Chuyển (W) chặn toàn bộ lướt E và R Khô Máu của K'Sante."}
            ],
            "counter_strategy": "Đánh bằng các tướng có sát thương chuẩn hoặc thả diều tầm xa né Q3. Không đứng gần tường để tránh bị R kéo qua."
        }
    ],
    "jungle": [
        {
            "name": "Sejuani", "tier": "S+ (VCS / LCK King)", "win_rate": "52.9%", "ban_rate": "38%",
            "why_hot": "Dọn rừng nhanh, trâu bò và chuỗi khống chế đóng băng kích hoạt tức thì khi đi cùng Solo Laner cận chiến.",
            "core_build": "Băng Giáp ➔ Giáp Gai ➔ Giáp Tâm Linh / Lời Thề Hiệp Sĩ",
            "runes": "Dư Chấn • Suối Nguồn Sinh Mệnh • Kiểm Soát Điều Kiện • Tiếp Sức",
            "counters": [
                {"champ": "Trundle", "wr": "55.8%", "reason": "Chinh Phục (R) hút sạch giáp/kháng phép biến Sejuani thành bia đỡ đạn giấy."},
                {"champ": "Olaf", "wr": "54.7%", "reason": "Tận Thế Ragnarok (R) kháng 100% mọi hiệu ứng làm chậm và đóng băng của Sejuani."},
                {"champ": "Kindred", "wr": "53.5%", "reason": "Cơ động nhảy thả diều cướp rừng và R Cừu Cứu Sinh cứu đồng đội bị đóng băng."}
            ],
            "counter_strategy": "Pick tướng xâm lăng cướp rừng đầu game hoặc các đấu sĩ kháng CC càn quét. Tránh giao tranh 2v2 khi Mid đối thủ là tướng cận chiến."
        },
        {
            "name": "Jarvan IV", "tier": "S (Snowball Meta)", "win_rate": "52.4%", "ban_rate": "32%",
            "why_hot": "Gank sớm phút 2:35 cực gắt, ép Tốc Biến đối thủ và tạo tiền đề ăn sâu hư không / rồng đầu tiên.",
            "core_build": "Ngọn Giáo Shojin ➔ Nguyệt Đao / Chùy Phản Kích ➔ Móng Vuốt Sterak",
            "runes": "Chinh Phục • Đắc Thắng • Huyền Thoại: Tốc Độ Đánh • Chốt Chặn Cuối Cùng",
            "counters": [
                {"champ": "Poppy", "wr": "56.2%", "reason": "W chặn đứng toàn bộ combo lướt E-Q của Jarvan IV."},
                {"champ": "Viego", "wr": "53.1%", "reason": "Tay đôi khỏe hơn về giữa trận, cướp xác Jarvan lật ngược combat."},
                {"champ": "Gragas", "wr": "53.4%", "reason": "Lấy Thịt Đè Người (E) ngắt E-Q của Jarvan, R hất tung phá tan Đại Địa Chấn."}
            ],
            "counter_strategy": "Cắm mắt sớm ở phút 1:20 tại bụi sông để phát hiện gank level 2-3. Pick tướng có chiêu thức vượt qua được tường R."
        }
    ],
    "mid": [
        {
            "name": "Azir", "tier": "S+ (Pro Priority)", "win_rate": "51.5%", "ban_rate": "45%",
            "why_hot": "Khả năng dọn lính chống đẩy trụ, an toàn tuyệt đối và chiêu cuối Shurima Shuffle lật kèo giao tranh lớn.",
            "core_build": "Nanh Nashor ➔ Đồng Hồ Cát Zhonya ➔ Mũ Phù Thủy Rabadon",
            "runes": "Chinh Phục / Nhịp Độ Chết Người • Hiện Diện Trí Tuệ • Huyền Thoại: Tốc Độ Đánh",
            "counters": [
                {"champ": "Syndra", "wr": "54.6%", "reason": "Tầm dùng chiêu xa hơn đè Azir từ cấp 1-5, E ngắt lướt E-Q của Azir."},
                {"champ": "Jayce", "wr": "53.9%", "reason": "Cầu Sấm dồn sát thương sốc cấu rỉa máu Azir trước khi nổ giao tranh."},
                {"champ": "Zed", "wr": "53.2%", "reason": "Dấu Ấn Tử Thần (R) né hoàn toàn Phân Chia Thiên Hạ (R) của Azir."}
            ],
            "counter_strategy": "Đè đường và ép giao tranh từ phút 1 đến 15 trước khi Azir có món đồ thứ 2. Chọn tướng tầm xa hoặc sát thủ cơ động né lính cát."
        },
        {
            "name": "Yone", "tier": "S+ (Meta Flex)", "win_rate": "52.2%", "ban_rate": "50%",
            "why_hot": "Khả năng phân chia sát thương AD/AP/True, cơ động cao, đẩy lẻ cánh 1-3-1 và mở giao tranh diện rộng cực mạnh.",
            "core_build": "Gươm Suy Hao / Móc Diệt ➔ Vô Cực Kiếm ➔ Móng Vuốt Sterak / Khiên Băng",
            "runes": "Nhịp Độ Chết Người • Đắc Thắng • Huyền Thoại: Tốc Độ Đánh • Chốt Chặn Cuối Cùng",
            "counters": [
                {"champ": "Renekton", "wr": "56.1%", "reason": "Choáng W phá khiên W của Yone, dồn sát thương sốc chết Yone trong 1 combo."},
                {"champ": "Pantheon", "wr": "55.3%", "reason": "W Choáng chỉ định (Point & click) không thể né, E chặn 100% sát thương phản công."},
                {"champ": "Vex", "wr": "54.2%", "reason": "Nội tại Hoảng Sợ trừng phạt mỗi khi Yone dùng Q3 hoặc E lướt tới."}
            ],
            "counter_strategy": "Sử dụng khống chế cứng chỉ định (Targeted Stun) và lên Khiên Băng Randuin + Giày Thép Gai để giảm 30% sát thương bạo kích."
        }
    ],
    "adc": [
        {
            "name": "Kalista", "tier": "S+ (Early Dominance)", "win_rate": "53.0%", "ban_rate": "46%",
            "why_hot": "Vua đè đường cấp 1-3, kiểm soát 100% mục tiêu lớn nhờ E Giày Vò và ulti R setup giao tranh với SP mở.",
            "core_build": "Gươm Suy Hao ➔ Cuồng Đao Guinsoo ➔ Đao Tím / Nỏ Tử Thủ",
            "runes": "Mưa Kiếm / Nhịp Độ Chết Người • Vị Máu • Thu Thập Nhãn Cầu",
            "counters": [
                {"champ": "Ashe", "wr": "55.7%", "reason": "Băng Tiễn làm chậm làm giảm trực tiếp tốc độ nhảy nội tại của Kalista."},
                {"champ": "Nasus", "wr": "56.4%", "reason": "Lão Hóa (W) làm giảm 75% tốc chạy & tốc đánh biến Kalista thành bia tập bắn."},
                {"champ": "Varus", "wr": "53.5%", "reason": "Cấu rỉa tầm xa và R trói chân không cho Kalista nhảy nhót."}
            ],
            "counter_strategy": "Sử dụng hiệu ứng Làm Chậm (Slow) hoặc Kiệt Sức. Không tranh chấp trừng phạt mục tiêu 50-50 với Kalista khi cô ta đã cắm nhiều giáo."
        },
        {
            "name": "Varus", "tier": "S (Flexibility King)", "win_rate": "52.1%", "ban_rate": "35%",
            "why_hot": "Cực kỳ đa dụng: Có thể lên Sát Lực cấu rỉa hoặc On-hit diệt Đỡ Đòn, chiêu cuối R mở/phản giao tranh hoàn hảo.",
            "core_build": "Gươm Suy Hao ➔ Cuồng Đao Guinsoo ➔ Nỏ Thiện Xạ / Đồng Hồ Cát",
            "runes": "Nhịp Độ Chết Người • Đắc Thắng • Huyền Thoại: Tốc Độ Đánh • Nhát Chém Ân Huệ",
            "counters": [
                {"champ": "Braum", "wr": "54.9%", "reason": "Khiên E Tối Kiên Cường chặn đứng toàn bộ Q cấu rỉa và chiêu cuối R của Varus."},
                {"champ": "Samira", "wr": "54.2%", "reason": "Lốc Kiếm (W) chém tan toàn bộ mũi tên và sợi xích tội lỗi của Varus."},
                {"champ": "Yasuo", "wr": "53.8%", "reason": "Tường Gió vô hiệu hóa hoàn toàn Varus trong giao tranh tổng."}
            ],
            "counter_strategy": "Pick các tướng có khiên chặn đạn đạo (Braum, Samira, Yasuo) hoặc đấu sĩ lao thẳng vào áp sát nhanh."
        }
    ],
    "support": [
        {
            "name": "Nautilus", "tier": "S+ (Engage King)", "win_rate": "52.8%", "ban_rate": "40%",
            "why_hot": "Lượng khống chế cứng khổng lồ: Q kéo, Nội tại trói chân, R Thủy Lôi Tầm Nhiệt chỉ định không thể né.",
            "core_build": "Dây Chuyền Solari ➔ Lời Thề Hiệp Sĩ ➔ Giáp Gai",
            "runes": "Dư Chấn • Nện Khiên • Kiểm Soát Điều Kiện • Lan Tràn",
            "counters": [
                {"champ": "Morgana", "wr": "56.3%", "reason": "Khiên Đen (E) vô hiệu hóa hoàn toàn kéo Q và ulti R của Nautilus."},
                {"champ": "Braum", "wr": "54.1%", "reason": "Nhảy lên chắn kéo cho xạ thủ, phản công bằng nội tại làm choáng."},
                {"champ": "Renata Glasc", "wr": "53.6%", "reason": "Cứu nguy Xạ Thủ bằng W và dùng R biến sát thương team địch đánh lẫn nhau khi Nautilus mở vào."}
            ],
            "counter_strategy": "Pick Morgana hoặc lên Khăn Giải Thuật / Dây Chuyền Chữ Thập. Giữ vị trí sau lính để tránh bị Q kéo bất ngờ."
        },
        {
            "name": "Renata Glasc", "tier": "S (Counter-Engage Queen)", "win_rate": "52.5%", "ban_rate": "36%",
            "why_hot": "Khắc chế cứng mọi đội hình lao vào và tốc đánh cao. W Cứu Nguy tạo cơ hội lật kèo ngoạn mục.",
            "core_build": "Dây Chuyền Solari ➔ Dây Chuyền Chuộc Tội ➔ Vương Miện Shurelya",
            "runes": "Hộ Vệ • Nện Khiên • Giáp Cốt • Tiếp Sức",
            "counters": [
                {"champ": "Milio", "wr": "55.8%", "reason": "Chiêu cuối R Khúc Ca Hoàn Sinh giải trừ toàn bộ hiệu ứng Cuồng Bạo từ ulti của Renata."},
                {"champ": "Soraka", "wr": "54.2%", "reason": "Câm lặng E đặt dưới chân ngắt combo của Renata, hồi máu diện rộng."},
                {"champ": "Karma", "wr": "53.7%", "reason": "Cấu rỉa tầm xa và bật khiên tốc chạy E né hoàn toàn làn sóng R của Renata."}
            ],
            "counter_strategy": "Pick Milio để giải chiêu cuối R của Renata. Không dồn đội hình tụ lại một cụm khi giao tranh ở cửa hang rồng/baron."
        }
    ]
}

