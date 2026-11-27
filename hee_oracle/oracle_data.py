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

    # ─── JUNGLE ───
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
