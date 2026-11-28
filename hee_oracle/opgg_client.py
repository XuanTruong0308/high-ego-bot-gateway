import asyncio
import aiohttp
import re
import html
import time
import urllib.parse
from typing import Dict, Any, List, Optional

# Riot Data Dragon champion list fallback + cache
DDRAGON_CHAMPIONS_URL = "https://ddragon.leagueoflegends.com/cdn/14.23.1/data/en_US/champion.json"

# In-memory caches
_CHAMPIONS_CACHE: List[Dict[str, str]] = []
_OPGG_CACHE: Dict[str, Dict[str, Any]] = {}
CACHE_TTL = 3600  # 1 hour

# Popular standard champion list fallback (with roles)
DEFAULT_CHAMPIONS = [
    {"id": "Aatrox", "name": "Aatrox", "role": "Top / Đấu Sĩ"},
    {"id": "Ahri", "name": "Ahri", "role": "Mid / Pháp Sư"},
    {"id": "Akali", "name": "Akali", "role": "Mid / Sát Thủ"},
    {"id": "Akshan", "name": "Akshan", "role": "Mid / Xạ Thủ"},
    {"id": "Alistar", "name": "Alistar", "role": "Sup / Đỡ Đòn"},
    {"id": "Ambessa", "name": "Ambessa", "role": "Top / Đấu Sĩ"},
    {"id": "Amumu", "name": "Amumu", "role": "Jungle / Đỡ Đòn"},
    {"id": "Anivia", "name": "Anivia", "role": "Mid / Pháp Sư"},
    {"id": "Annie", "name": "Annie", "role": "Mid / Pháp Sư"},
    {"id": "Aphelios", "name": "Aphelios", "role": "ADC / Xạ Thủ"},
    {"id": "Ashe", "name": "Ashe", "role": "ADC / Sup / Xạ Thủ"},
    {"id": "AurelionSol", "name": "Aurelion Sol", "role": "Mid / Pháp Sư"},
    {"id": "Aurora", "name": "Aurora", "role": "Mid / Top / Pháp Sư"},
    {"id": "Azir", "name": "Azir", "role": "Mid / Pháp Sư"},
    {"id": "Bard", "name": "Bard", "role": "Sup / Hỗ Trợ"},
    {"id": "Belveth", "name": "Bel'Veth", "role": "Jungle / Đấu Sĩ"},
    {"id": "Blitzcrank", "name": "Blitzcrank", "role": "Sup / Mở Giao Tranh"},
    {"id": "Brand", "name": "Brand", "role": "Sup / Jungle / Pháp Sư"},
    {"id": "Braum", "name": "Braum", "role": "Sup / Bảo Kê"},
    {"id": "Briar", "name": "Briar", "role": "Jungle / Đấu Sĩ"},
    {"id": "Caitlyn", "name": "Caitlyn", "role": "ADC / Xạ Thủ"},
    {"id": "Camille", "name": "Camille", "role": "Top / Đấu Sĩ"},
    {"id": "Cassiopeia", "name": "Cassiopeia", "role": "Mid / Top / Pháp Sư"},
    {"id": "Chogath", "name": "Cho'Gath", "role": "Top / Đỡ Đòn"},
    {"id": "Corki", "name": "Corki", "role": "Mid / ADC / Xạ Thủ"},
    {"id": "Darius", "name": "Darius", "role": "Top / Đấu Sĩ"},
    {"id": "Diana", "name": "Diana", "role": "Jungle / Mid / Sát Thủ"},
    {"id": "Draven", "name": "Draven", "role": "ADC / Xạ Thủ"},
    {"id": "DrMundo", "name": "Dr. Mundo", "role": "Top / Đỡ Đòn"},
    {"id": "Ekko", "name": "Ekko", "role": "Jungle / Mid / Sát Thủ"},
    {"id": "Elise", "name": "Elise", "role": "Jungle / Sát Thủ"},
    {"id": "Evelynn", "name": "Evelynn", "role": "Jungle / Sát Thủ"},
    {"id": "Ezreal", "name": "Ezreal", "role": "ADC / Xạ Thủ"},
    {"id": "Fiddlesticks", "name": "Fiddlesticks", "role": "Jungle / Pháp Sư"},
    {"id": "Fiora", "name": "Fiora", "role": "Top / Đấu Sĩ Đẩy Lẻ"},
    {"id": "Fizz", "name": "Fizz", "role": "Mid / Sát Thủ"},
    {"id": "Galio", "name": "Galio", "role": "Mid / Sup / Đỡ Đòn"},
    {"id": "Gangplank", "name": "Gangplank", "role": "Top / Đấu Sĩ"},
    {"id": "Garen", "name": "Garen", "role": "Top / Đấu Sĩ"},
    {"id": "Gnar", "name": "Gnar", "role": "Top / Đấu Sĩ"},
    {"id": "Gragas", "name": "Gragas", "role": "Top / Jungle / Mid"},
    {"id": "Graves", "name": "Graves", "role": "Jungle / Xạ Thủ"},
    {"id": "Gwen", "name": "Gwen", "role": "Top / Đấu Sĩ Phép"},
    {"id": "Hecarim", "name": "Hecarim", "role": "Jungle / Đấu Sĩ"},
    {"id": "Heimerdinger", "name": "Heimerdinger", "role": "Top / Sup / Pháp Sư"},
    {"id": "Hwei", "name": "Hwei", "role": "Mid / Sup / Pháp Sư"},
    {"id": "Illaoi", "name": "Illaoi", "role": "Top / Đấu Sĩ"},
    {"id": "Irelia", "name": "Irelia", "role": "Top / Mid / Đấu Sĩ"},
    {"id": "Ivern", "name": "Ivern", "role": "Jungle / Hỗ Trợ"},
    {"id": "Janna", "name": "Janna", "role": "Sup / Hỗ Trợ"},
    {"id": "JarvanIV", "name": "Jarvan IV", "role": "Jungle / Mở Giao Tranh"},
    {"id": "Jax", "name": "Jax", "role": "Top / Jungle / Đấu Sĩ"},
    {"id": "Jayce", "name": "Jayce", "role": "Top / Mid / Cấu Rỉa"},
    {"id": "Jhin", "name": "Jhin", "role": "ADC / Xạ Thủ"},
    {"id": "Jinx", "name": "Jinx", "role": "ADC / Xạ Thủ"},
    {"id": "Kaisa", "name": "Kai'Sa", "role": "ADC / Sát Thủ"},
    {"id": "Kalista", "name": "Kalista", "role": "ADC / Đè Đường"},
    {"id": "Karma", "name": "Karma", "role": "Sup / Mid / Hỗ Trợ"},
    {"id": "Karthus", "name": "Karthus", "role": "Jungle / ADC / Pháp Sư"},
    {"id": "Kassadin", "name": "Kassadin", "role": "Mid / Sát Thủ Late"},
    {"id": "Katarina", "name": "Katarina", "role": "Mid / Sát Thủ"},
    {"id": "Kayle", "name": "Kayle", "role": "Top / Mid / Hyper Carry"},
    {"id": "Kayn", "name": "Kayn", "role": "Jungle / Sát Thủ/Đấu Sĩ"},
    {"id": "Kennen", "name": "Kennen", "role": "Top / Giao Tranh Tổng"},
    {"id": "Khazix", "name": "Kha'Zix", "role": "Jungle / Sát Thủ"},
    {"id": "Kindred", "name": "Kindred", "role": "Jungle / Xạ Thủ"},
    {"id": "Kled", "name": "Kled", "role": "Top / Đấu Sĩ"},
    {"id": "KogMaw", "name": "Kog'Maw", "role": "ADC / Hyper Carry"},
    {"id": "KSante", "name": "K'Sante", "role": "Top / Đỡ Đòn"},
    {"id": "Leblanc", "name": "LeBlanc", "role": "Mid / Sát Thủ"},
    {"id": "LeeSin", "name": "Lee Sin", "role": "Jungle / Đấu Sĩ High-Elo"},
    {"id": "Leona", "name": "Leona", "role": "Sup / Khống Chế Cứng"},
    {"id": "Lillia", "name": "Lillia", "role": "Jungle / Pháp Sư"},
    {"id": "Lissandra", "name": "Lissandra", "role": "Mid / Khống Chế"},
    {"id": "Lucian", "name": "Lucian", "role": "ADC / Mid / Đè Đường"},
    {"id": "Lulu", "name": "Lulu", "role": "Sup / Buff Xạ Thủ"},
    {"id": "Lux", "name": "Lux", "role": "Mid / Sup / Cấu Rỉa"},
    {"id": "Malphite", "name": "Malphite", "role": "Top / Sup / Giao Tranh"},
    {"id": "Malzahar", "name": "Malzahar", "role": "Mid / Áp Chế"},
    {"id": "Maokai", "name": "Maokai", "role": "Jungle / Sup / Top"},
    {"id": "MasterYi", "name": "Master Yi", "role": "Jungle / Sát Thủ"},
    {"id": "Milio", "name": "Milio", "role": "Sup / Buff Tầm Xa"},
    {"id": "MissFortune", "name": "Miss Fortune", "role": "ADC / Giao Tranh"},
    {"id": "Mordekaiser", "name": "Mordekaiser", "role": "Top / Đấu Sĩ Bắt Lẻ"},
    {"id": "Morgana", "name": "Morgana", "role": "Sup / Mid / Khống Chế"},
    {"id": "Naafiri", "name": "Naafiri", "role": "Mid / Sát Thủ"},
    {"id": "Nami", "name": "Nami", "role": "Sup / Hỗ Trợ"},
    {"id": "Nasus", "name": "Nasus", "role": "Top / Đấu Sĩ"},
    {"id": "Nautilus", "name": "Nautilus", "role": "Sup / Mở Giao Tranh"},
    {"id": "Neeko", "name": "Neeko", "role": "Mid / Sup / Biến Ảo"},
    {"id": "Nidalee", "name": "Nidalee", "role": "Jungle / Sát Thủ"},
    {"id": "Nilah", "name": "Nilah", "role": "ADC / Cận Chiến"},
    {"id": "Nocturne", "name": "Nocturne", "role": "Jungle / Tắt Đèn"},
    {"id": "Nunu", "name": "Nunu & Willump", "role": "Jungle / Đỡ Đòn"},
    {"id": "Olaf", "name": "Olaf", "role": "Top / Jungle / Bất Tử"},
    {"id": "Orianna", "name": "Orianna", "role": "Mid / Giao Tranh Tổng"},
    {"id": "Ornn", "name": "Ornn", "role": "Top / Nâng Cấp Đồ"},
    {"id": "Pantheon", "name": "Pantheon", "role": "Top / Mid / Sup"},
    {"id": "Poppy", "name": "Poppy", "role": "Top / Sup / Jungle"},
    {"id": "Pyke", "name": "Pyke", "role": "Sup / Sát Thủ Vét Mạng"},
    {"id": "Qiyana", "name": "Qiyana", "role": "Mid / Sát Thủ"},
    {"id": "Quinn", "name": "Quinn", "role": "Top / Đảo Đường"},
    {"id": "Rakan", "name": "Rakan", "role": "Sup / Mở Giao Tranh"},
    {"id": "Rammus", "name": "Rammus", "role": "Jungle / Khắc Chế AD"},
    {"id": "RekSai", "name": "Rek'Sai", "role": "Jungle / Đấu Sĩ"},
    {"id": "Rell", "name": "Rell", "role": "Sup / Jungle / Gom Người"},
    {"id": "Renata", "name": "Renata Glasc", "role": "Sup / Lật Kèo"},
    {"id": "Renekton", "name": "Renekton", "role": "Top / Đè Đường VCS"},
    {"id": "Rengar", "name": "Rengar", "role": "Jungle / Sát Thủ"},
    {"id": "Riven", "name": "Riven", "role": "Top / Kỹ Năng Cao"},
    {"id": "Rumble", "name": "Rumble", "role": "Top / Mid / Rải Mưa Tên Lửa"},
    {"id": "Ryze", "name": "Ryze", "role": "Mid / Đảo Đường"},
    {"id": "Samira", "name": "Samira", "role": "ADC / Lao Vào Quét Sạch"},
    {"id": "Sejuani", "name": "Sejuani", "role": "Jungle / Top / Đỡ Đòn"},
    {"id": "Senna", "name": "Senna", "role": "Sup / ADC / Xạ Thủ Tầm Xa"},
    {"id": "Seraphine", "name": "Seraphine", "role": "Sup / Mid / ADC"},
    {"id": "Sett", "name": "Sett", "role": "Top / Đấu Sĩ / Đấm Phát Chết Luôn"},
    {"id": "Shaco", "name": "Shaco", "role": "Jungle / Phá Rối"},
    {"id": "Shen", "name": "Shen", "role": "Top / Sup / Nhất Thống"},
    {"id": "Shyvana", "name": "Shyvana", "role": "Jungle / Hóa Rồng"},
    {"id": "Singed", "name": "Singed", "role": "Top / Rải Độc Chặn Lính"},
    {"id": "Sion", "name": "Sion", "role": "Top / Xe Tông Đẩy Lẻ"},
    {"id": "Sivir", "name": "Sivir", "role": "ADC / Đẩy Đường Chạy Nhanh"},
    {"id": "Skarner", "name": "Skarner", "role": "Top / Jungle / Đỡ Đòn"},
    {"id": "Smolder", "name": "Smolder", "role": "ADC / Mid / Late Game God"},
    {"id": "Sona", "name": "Sona", "role": "Sup / Hỗ Trợ"},
    {"id": "Soraka", "name": "Soraka", "role": "Sup / Hồi Máu"},
    {"id": "Swain", "name": "Swain", "role": "Mid / Sup / Hút Hồn"},
    {"id": "Sylas", "name": "Sylas", "role": "Mid / Top / Cướp Chiêu Cuối"},
    {"id": "Syndra", "name": "Syndra", "role": "Mid / Sốc Sát Thương"},
    {"id": "TahmKench", "name": "Tahm Kench", "role": "Top / Sup / Nuốt Đồng Đội"},
    {"id": "Taliyah", "name": "Taliyah", "role": "Jungle / Mid / Dựng Tường"},
    {"id": "Talon", "name": "Talon", "role": "Mid / Jungle / Vượt Địa Hình"},
    {"id": "Taric", "name": "Taric", "role": "Sup / Bất Tử"},
    {"id": "Teemo", "name": "Teemo", "role": "Top / Nấm Tàng Hình"},
    {"id": "Thresh", "name": "Thresh", "role": "Sup / Án Tử & Đèn Lồng"},
    {"id": "Tristana", "name": "Tristana", "role": "ADC / Mid / Phá Trụ"},
    {"id": "Trundle", "name": "Trundle", "role": "Top / Jungle / Hút Chỉ Số"},
    {"id": "Tryndamere", "name": "Tryndamere", "role": "Top / Từ Chối Tử Thần"},
    {"id": "TwistedFate", "name": "Twisted Fate", "role": "Mid / Rút Bài & Định Mệnh"},
    {"id": "Twitch", "name": "Twitch", "role": "ADC / Jungle / Bắn Tỉa Tàng Hình"},
    {"id": "Udyr", "name": "Udyr", "role": "Jungle / Top / Đấu Sĩ"},
    {"id": "Urgot", "name": "Urgot", "role": "Top / Máy Xay Thịt"},
    {"id": "Varus", "name": "Varus", "role": "ADC / Mid / Cấu Rỉa & Khống Chế"},
    {"id": "Vayne", "name": "Vayne", "role": "ADC / Top / Bắn % Máu Chuẩn"},
    {"id": "Veigar", "name": "Veigar", "role": "Mid / Pháp Sư Vô Hạn AP"},
    {"id": "Velkoz", "name": "Vel'Koz", "role": "Mid / Sup / Cấu Rỉa Chuẩn"},
    {"id": "Vex", "name": "Vex", "role": "Mid / Khắc Chế Lướt"},
    {"id": "Vi", "name": "Vi", "role": "Jungle / Tả Xung Hữu Đột"},
    {"id": "Viego", "name": "Viego", "role": "Jungle / Chiếm Xác Snowball"},
    {"id": "Viktor", "name": "Viktor", "role": "Mid / Công Nghệ Cường Hóa"},
    {"id": "Vladimir", "name": "Vladimir", "role": "Mid / Top / Hút Máu Late"},
    {"id": "Volibear", "name": "Volibear", "role": "Top / Jungle / Tắt Trụ"},
    {"id": "Warwick", "name": "Warwick", "role": "Jungle / Top / Đánh Mùi Máu"},
    {"id": "Wukong", "name": "Wukong", "role": "Top / Jungle / Lốc Xoáy 2 Lần"},
    {"id": "Xayah", "name": "Xayah", "role": "ADC / Tự Bảo Vệ Cực Mạnh"},
    {"id": "Xerath", "name": "Xerath", "role": "Mid / Sup / Pháo Cao Xạ"},
    {"id": "XinZhao", "name": "Xin Zhao", "role": "Jungle / Lao Vào Đỡ Đạn"},
    {"id": "Yasuo", "name": "Yasuo", "role": "Mid / Top / Đấng Gió Lướt"},
    {"id": "Yone", "name": "Yone", "role": "Mid / Top / Xuất Hồn"},
    {"id": "Yorick", "name": "Yorick", "role": "Top / Ma Cà Rồng Đẩy Trụ"},
    {"id": "Yuumi", "name": "Yuumi", "role": "Sup / Ký Sinh Trùng"},
    {"id": "Zac", "name": "Zac", "role": "Jungle / Top / Bắn Thun Cực Xa"},
    {"id": "Zed", "name": "Zed", "role": "Mid / Sát Thủ Bóng"},
    {"id": "Zeri", "name": "Zeri", "role": "ADC / Tia Chớp Cơ Động"},
    {"id": "Ziggs", "name": "Ziggs", "role": "ADC / Mid / Ném Bom Phá Trụ"},
    {"id": "Zilean", "name": "Zilean", "role": "Sup / Mid / Hồi Sinh"},
    {"id": "Zoe", "name": "Zoe", "role": "Mid / Nghịch Sao One-Shot"},
    {"id": "Zyra", "name": "Zyra", "role": "Sup / Jungle / Bụi Cây Độc"}
]


def get_champ_slug(name: str) -> str:
    """Normalize champion name to OP.GG slug."""
    s = name.lower().strip()
    s = s.replace("'", "").replace(" ", "").replace(".", "")
    # Special OP.GG slug mappings
    mappings = {
        "wukong": "monkeyking",
        "renataglasc": "renata",
        "nunu&willump": "nunu",
        "drmundo": "drmundo",
    }
    return mappings.get(s, s)


async def init_champion_database():
    """Load all 169+ champions from Riot Data Dragon or fallback."""
    global _CHAMPIONS_CACHE
    if _CHAMPIONS_CACHE:
        return _CHAMPIONS_CACHE

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(DDRAGON_CHAMPIONS_URL, timeout=5) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    champ_dict = data.get("data", {})
                    loaded = []
                    role_map = {
                        "Fighter": "Đấu Sĩ",
                        "Tank": "Đỡ Đòn",
                        "Mage": "Pháp Sư",
                        "Assassin": "Sát Thủ",
                        "Marksman": "Xạ Thủ",
                        "Support": "Hỗ Trợ"
                    }
                    for cid, cinfo in champ_dict.items():
                        c_name = cinfo.get("name", cid)
                        tags = cinfo.get("tags", [])
                        viet_tags = " / ".join([role_map.get(t, t) for t in tags])
                        loaded.append({
                            "id": cid,
                            "name": c_name,
                            "role": viet_tags or "Tướng Thi Đấu"
                        })
                    _CHAMPIONS_CACHE = sorted(loaded, key=lambda x: x["name"])
                    return _CHAMPIONS_CACHE
    except Exception:
        pass

    _CHAMPIONS_CACHE = DEFAULT_CHAMPIONS
    return _CHAMPIONS_CACHE


def search_champions(query: str, limit: int = 25) -> List[Dict[str, str]]:
    """Autocomplete search for champions based on query."""
    champs = _CHAMPIONS_CACHE if _CHAMPIONS_CACHE else DEFAULT_CHAMPIONS
    q = query.lower().strip()
    if not q:
        # Return popular meta champions as default suggestions
        popular = ["Aatrox", "Ahri", "Azir", "Kalista", "K'Sante", "Lee Sin", "Renekton", "Sejuani", "Sett", "Sylas", "Yone", "Yasuo"]
        res = [c for c in champs if c["name"] in popular or c["id"] in popular]
        return res[:limit]

    # Filter champions: starts with first, then contains
    starts = [c for c in champs if c["name"].lower().startswith(q) or c["id"].lower().startswith(q)]
    contains = [c for c in champs if q in c["name"].lower() and c not in starts]
    return (starts + contains)[:limit]


async def fetch_opgg_data(champion_name: str) -> Dict[str, Any]:
    """Fetch live build, win rate, and items from OP.GG."""
    slug = get_champ_slug(champion_name)
    now = time.time()

    # Check cache
    if slug in _OPGG_CACHE and (now - _OPGG_CACHE[slug].get("_ts", 0) < CACHE_TTL):
        return _OPGG_CACHE[slug]

    url = f"https://www.op.gg/champions/{slug}/build"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept-Language": "en-US,en;q=0.9,vi;q=0.8",
    }

    result = {
        "slug": slug,
        "name": champion_name.strip().title(),
        "win_rate": None,
        "pick_rate": None,
        "ban_rate": None,
        "tier": None,
        "core_items": [],
        "boots": [],
        "starter_items": [],
        "opgg_url": url,
        "counters_url": f"https://www.op.gg/champions/{slug}/counters",
        "deeplol_url": f"https://www.deeplol.gg/champions/{slug}/build",
        "_ts": now
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers, timeout=8) as resp:
                if resp.status == 200:
                    content = await resp.text()

                    # Extract stats
                    wr = re.search(r'Win\s*rate\s*([\d\.]+\s*%)', content, re.I)
                    pr = re.search(r'Pick\s*rate\s*([\d\.]+\s*%)', content, re.I)
                    br = re.search(r'Ban\s*rate\s*([\d\.]+\s*%)', content, re.I)
                    tier = re.search(r'Tier\s*(\d+)', content, re.I)

                    if wr: result["win_rate"] = wr.group(1).strip()
                    if pr: result["pick_rate"] = pr.group(1).strip()
                    if br: result["ban_rate"] = br.group(1).strip()
                    if tier: result["tier"] = f"Tier {tier.group(1).strip()}"

                    # Extract items from alt attributes where src includes item
                    raw_items = re.findall(r'<img[^>]+alt="([^"]+)"[^>]+src="[^"]+item[^"]+"', content, re.I)
                    clean_items = []
                    seen = set()
                    for item in raw_items:
                        item_clean = html.unescape(item).strip()
                        # Skip potions and wards in core items
                        if item_clean and item_clean not in seen:
                            seen.add(item_clean)
                            clean_items.append(item_clean)

                    # Classify items
                    starter_names = {"Doran's Blade", "Doran's Shield", "Doran's Ring", "Dark Seal", "Tear of the Goddess", "World Atlas", "Gustwalker Hatchling", "Scorchclaw Pup", "Mosstomper Seedling"}
                    boot_names = {"Plated Steelcaps", "Mercury's Treads", "Berserker's Greaves", "Ionian Boots of Lucidity", "Sorcerer's Shoes", "Boots of Swiftness", "Symbiotic Soles"}

                    starters = [it for it in clean_items if it in starter_names or "Doran" in it or "Potion" in it]
                    boots = [it for it in clean_items if it in boot_names or "Boots" in it or "Treads" in it or "Steelcaps" in it or "Greaves" in it or "Shoes" in it]
                    core = [it for it in clean_items if it not in starters and it not in boots and "Potion" not in it and "Ward" not in it]

                    result["starter_items"] = starters[:2]
                    result["boots"] = boots[:2]
                    result["core_items"] = core[:4]
    except Exception as e:
        result["error"] = str(e)

    _OPGG_CACHE[slug] = result
    return result
