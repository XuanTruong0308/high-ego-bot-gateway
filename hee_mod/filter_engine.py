"""
filter_engine.py — Bộ lọc từ ngữ thô tục / xúc phạm cực đoan cho HEe Sentinel.
Hỗ trợ regex, chuẩn hóa ký tự lách luật (leetspeak, dấu chấm, dấu cách giữa các ký tự).
"""

import re
import unicodedata

# Danh sách từ cấm cốt lõi (tiếng Việt & biến thể)
DEFAULT_BANNED_WORDS = [
    # Nhóm bộ phận sinh dục thô thiển
    r"c[aặâăáàảãạ]c",
    r"l[oồôõọóòỏ]n",
    r"b[uúùủũụ]i",
    r"d[aáàảãạ]m",
    r"d[aáàảãạ]m\s*t[aáàảãạ]c",
    
    # Nhóm chửi bới xúc phạm gia đình / cha mẹ
    r"đ[iịíìỉĩ]t\s*m[eẹéèẻẽ]\s*m[aàyáảãạ]",
    r"đ[iịíìỉĩ]t\s*m[eẹéèẻẽ]",
    r"đ[iịíìỉĩ]t\s*c[oụùúủũ]",
    r"đ[iịíìỉĩ]t\s*b[aàáảãạ]",
    r"đ[uụùúủũ]\s*m[aáàảãạ]",
    r"đ[uụùúủũ]\s*m[eẹéèẻẽ]",
    r"đ[uụùúủũ]\s*c[aặâáàảãạ]c",
    r"m[eẹéèẻẽ]\s*m[aàyáảãạ]",
    r"b[aàáảãạ]\s*m[aàyáảãạ]",
    
    # Nhóm biến thể viết tắt / không dấu hay dùng
    r"dcm",
    r"dmm",
    r"vcl",
    r"clmm",
    r"ccmnr",
    r"dm",
    r"dmm",
    r"vkl",
    r"đmm",
    r"đcm",
    r"đclm",
    r"vl",
]

def normalize_text(text: str) -> str:
    """
    Chuẩn hóa chuỗi văn bản:
    1. Chuyển chữ thường.
    2. Khử các ký tự đặc biệt lách luật (chấm, phẩy, gạch, ký hiệu lạ kẹp giữa các chữ).
    """
    if not text:
        return ""
    text = text.lower()
    # Loại bỏ các ký tự phân cách cố ý chèn vào giữa chữ: c.ặ.c -> cặc, l_ồ_n -> lồn
    cleaned = re.sub(r"[\.\,\-\_\*\~\`\!\@\#\$\%\^\&\(\)\+\=\\\/\|]", "", text)
    return cleaned

class ProfanityFilter:
    def __init__(self, custom_words: list[str] | None = None):
        patterns = DEFAULT_BANNED_WORDS.copy()
        if custom_words:
            for w in custom_words:
                cleaned_w = re.escape(w.strip().lower())
                if cleaned_w:
                    patterns.append(cleaned_w)
        
        # Compile toàn bộ danh sách thành regex hiệu năng cao
        # Bắt đầu và kết thúc bằng ranh giới từ hoặc ký tự đặc biệt
        combined = "|".join([f"(?:{p})" for p in patterns])
        self.regex = re.compile(rf"(?:\b|_|^|\s)({combined})(?:\b|_|$|\s)", re.IGNORECASE)

    def check(self, content: str) -> tuple[bool, str | None]:
        """
        Kiểm tra xem nội dung có chứa từ cấm không.
        Trả về: (Có vi phạm hay không, Từ vi phạm phát hiện)
        """
        if not content:
            return False, None

        # Check chuỗi gốc
        match = self.regex.search(content.lower())
        if match:
            return True, match.group(1).strip()

        # Check chuỗi sau khi khử ký tự lách luật
        normalized = normalize_text(content)
        match_norm = self.regex.search(normalized)
        if match_norm:
            return True, match_norm.group(1).strip()

        return False, None
