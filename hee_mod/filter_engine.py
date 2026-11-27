"""
filter_engine.py — Bộ lọc từ ngữ thô tục / xúc phạm cực đoan cho HEe Sentinel.
Chỉ giới hạn nghiêm ngặt ở các từ ngữ xúc phạm nặng theo yêu cầu:
- địt mẹ, địt mẹ mày
- đụ má, đụ má mày
- lồn
- cặc
Cho phép hoàn toàn các từ viết tắt / cảm thán thông thường như: vl, dcm, dcmm, dmm, dm, vcl, vcc, vc...
Đảm bảo 100% không bao giờ phạt nhầm từ tiếng Việt như: các, khác, bác, chắc, dám, bụi, lộn xộn...
"""

import re

# Danh sách từ an toàn tuyệt đối (Whitelist)
SAFE_WORDS = {
    "các", "khác", "bác", "chắc", "thắc", "mắc", "thắc mắc", "rác", "lạc", "vác", "hạc",
    "tác", "xác", "nhạc", "phác", "thác", "mác", "khắc", "nấc", "giác",
    "bùi", "bụi", "ngậm ngùi", "bùi ngùi", "dám", "can đảm", "đàm", "hội đàm",
    "lộn", "lộn xộn", "nhầm lộn", "nhầm lẫn", "con lợn", "lợn",
    "cúc", "cục", "cóc", "cọc", "cộc", "cực", "cac ban", "cac"
}

# CHỈ BẮT ĐÚNG CÁC TỪ THÔ TỤC CỰC ĐOAN CHỈ ĐỊNH:
TARGET_BANNED_PATTERNS = [
    # 1. Nhóm "địt mẹ", "địt mẹ mày"
    r"\b(?:đ[iị]t|d[iị]t|đjt|djt)\s*m[ẹe](?:\s*m[aày])?\b",

    # 2. Nhóm "đụ má", "đụ má mày"
    r"\b(?:đ[ụu]|d[ụu])\s*m[áa](?:\s*m[aày])?\b",

    # 3. Nhóm "lồn" (Không bắt "lộn", "lộn xộn", "lợn")
    r"\b(?:l[ồòõ]n|l0n)\b",

    # 4. Nhóm "cặc" (Bắt buộc phải có chữ 'ặ' để tuyệt đối không bao giờ dính chữ "các" hoặc "cac")
    r"\b(?:cặ[ck]|kặ[ck])\b",
]


def clean_leetspeak(text: str) -> str:
    """Loại bỏ ký tự đặc biệt lách luật chèn giữa chữ cái: c.ặ.c -> cặc, l_ồ_n -> lồn"""
    if not text:
        return ""
    return re.sub(r"[\.\,\-\_\*\~\`\!\@\#\$\%\^\&\(\)\+\=\\\/\|]", "", text)


class ProfanityFilter:
    def __init__(self, custom_words: list[str] | None = None):
        patterns = TARGET_BANNED_PATTERNS.copy()
        if custom_words:
            for w in custom_words:
                cleaned_w = re.escape(w.strip().lower())
                if cleaned_w:
                    patterns.append(rf"\b{cleaned_w}\b")

        combined = "|".join([f"(?:{p})" for p in patterns])
        self.regex = re.compile(combined, re.IGNORECASE)

    def check(self, content: str) -> tuple[bool, str | None]:
        """
        Kiểm tra xem nội dung có chứa các từ thô tục bị cấm hay không.
        Trả về: (Có vi phạm hay không, Từ vi phạm phát hiện)
        """
        if not content:
            return False, None

        lower_content = content.lower()

        # 1. Kiểm tra chuỗi gốc
        match = self.regex.search(lower_content)
        if match:
            matched_word = match.group(0).strip()
            if matched_word not in SAFE_WORDS:
                return True, matched_word

        # 2. Kiểm tra chuỗi đã khử leetspeak (ví dụ: đ.ị.t m.ẹ, c.ặ.c)
        cleaned_content = clean_leetspeak(lower_content)
        if cleaned_content != lower_content:
            match_cleaned = self.regex.search(cleaned_content)
            if match_cleaned:
                matched_word = match_cleaned.group(0).strip()
                if matched_word not in SAFE_WORDS:
                    return True, matched_word

        return False, None
