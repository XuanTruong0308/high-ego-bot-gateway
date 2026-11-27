"""
filter_engine.py — Bộ lọc từ ngữ thô tục / xúc phạm cực đoan cho HEe Sentinel.
Được tối ưu để triệt tiêu False-Positive (không bao giờ phạt nhầm các từ tiếng Việt thông dụng như: các, khác, bác, chắc, dám, bụi...).
"""

import re
import unicodedata

# Danh sách từ tiếng Việt an toàn TUYỆT ĐỐI không bao giờ bị coi là vi phạm (Whitelist)
SAFE_WORDS = {
    "các", "khác", "bác", "chắc", "thắc", "mắc", "thắc mắc", "rác", "lạc", "vác", "hạc",
    "tác", "xác", "nhạc", "phác", "thác", "mác", "khắc", "nấc", "giác",
    "bùi", "bụi", "ngậm ngùi", "bùi ngùi", "dám", "can đảm", "đàm", "hội đàm",
    "lộn", "lộn xộn", "nhầm lộn", "nhầm lẫn", "con lợn", "lợn", "lái buôn",
    "buôn", "buộc", "buồng", "cúc", "cục", "cóc", "cọc", "cộc", "cực"
}

# Danh sách Regex từ cấm chính xác (bắt buộc đúng ngữ cảnh ranh giới từ)
STRICT_BANNED_PATTERNS = [
    # Nhóm "cặc / cac" (TUYỆT ĐỐI không chứa ký tự 'á', 'à', 'ả', 'ã' để tránh dính từ "các")
    r"\b(?:cặ[ck]|kặ[ck]|c[aă]k|k[aă]k)\b",
    r"\b(?:c[aă]c|kac)\b",

    # Nhóm "buồi / buoi" (Không dính "bùi", "bụi")
    r"\b(?:bu[ồò]i|buoi|b[uồò]y)\b",

    # Nhóm "lồn / lon" (Không dính "lợn", "lộn xộn")
    r"\b(?:l[ồòõ]n|l0n|l[o0]z|l[o0]zz)\b",

    # Nhóm "dâm" thô tục
    r"\b(?:d[aâ]m\s*(?:tặc|dục|dê|loàn|đãng))\b",

    # Nhóm chửi thề / bộ phận sinh dục
    r"\b(?:đ[iị]t|d[iị]t|đjt|djt)\b",
    r"\b(?:đ[ụu]|d[ụu])\s*(?:m[ẹe]|má|ma|c[ặa]c|cac|bà|cha|con)\b",
    r"\b(?:đ[iị]t|d[iị]t)\s*(?:m[ẹe]|c[oụùú]|b[aà]|cha)\b",
    r"\b(?:m[ẹe]\s*m[aày]|b[aà]\s*m[aày])\b",

    # Nhóm viết tắt tục tĩu phổ biến
    r"\b(?:dcm|dmm|vcl|clmm|ccmnr|đmm|đcm|đclm|vkl)\b",
]


def clean_leetspeak(text: str) -> str:
    """Loại bỏ ký tự đặc biệt lách luật nằm giữa các chữ cái: c.ặ.c -> cặc, l_ồ_n -> lồn"""
    if not text:
        return ""
    # Thay thế các ký tự lách luật nhưng giữ khoảng trắng
    return re.sub(r"[\.\,\-\_\*\~\`\!\@\#\$\%\^\&\(\)\+\=\\\/\|]", "", text)


class ProfanityFilter:
    def __init__(self, custom_words: list[str] | None = None):
        patterns = STRICT_BANNED_PATTERNS.copy()
        if custom_words:
            for w in custom_words:
                cleaned_w = re.escape(w.strip().lower())
                if cleaned_w:
                    patterns.append(rf"\b{cleaned_w}\b")

        combined = "|".join([f"(?:{p})" for p in patterns])
        self.regex = re.compile(combined, re.IGNORECASE)

    def check(self, content: str) -> tuple[bool, str | None]:
        """
        Kiểm tra vi phạm:
        - Kiểm tra trực tiếp trên chuỗi thô.
        - Kiểm tra trên chuỗi đã giải mã leetspeak (c.ặ.c).
        - Đảm bảo các từ an toàn trong SAFE_WORDS không bao giờ kích hoạt phạt.
        """
        if not content:
            return False, None

        lower_content = content.lower()

        # 1. Kiểm tra chuỗi gốc
        match = self.regex.search(lower_content)
        if match:
            matched_word = match.group(0).strip()
            # Bỏ qua nếu từ match nằm trong whitelist an toàn
            if matched_word not in SAFE_WORDS:
                return True, matched_word

        # 2. Kiểm tra chuỗi sau khi lọc ký tự lách luật
        cleaned_content = clean_leetspeak(lower_content)
        if cleaned_content != lower_content:
            match_cleaned = self.regex.search(cleaned_content)
            if match_cleaned:
                matched_word = match_cleaned.group(0).strip()
                if matched_word not in SAFE_WORDS:
                    return True, matched_word

        return False, None
