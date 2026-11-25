"""
transcript.py — Trình tạo file Transcript lưu lại toàn bộ lịch sử tin nhắn của Ticket.
Hỗ trợ xuất định dạng HTML / Markdown đẹp mắt kèm avatar, hình ảnh, embeds và timestamp.
"""

import os
import html
from datetime import datetime
import discord

TRANSCRIPT_DIR = os.path.join(os.path.dirname(__file__), "data", "transcripts")

def ensure_transcript_dir() -> None:
    os.makedirs(TRANSCRIPT_DIR, exist_ok=True)

async def generate_html_transcript(
    channel: discord.TextChannel,
    ticket_id: int,
    category_type: str,
    creator: discord.Member | discord.User,
    closed_by: str
) -> str:
    """
    Thu thập tin nhắn từ kênh và tạo file HTML transcript.
    Trả về đường dẫn tuyệt đối của file HTML.
    """
    ensure_transcript_dir()
    now_str = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"ticket-{ticket_id:04d}_{category_type}_{now_str}.html"
    filepath = os.path.join(TRANSCRIPT_DIR, filename)

    messages = []
    async for msg in channel.history(limit=1000, oldest_first=True):
        messages.append(msg)

    # Xây dựng nội dung HTML tông màu Dark/Red chuẩn HEe
    html_items = []
    for msg in messages:
        author_name = html.escape(msg.author.display_name)
        author_avatar = msg.author.display_avatar.url if msg.author.display_avatar else ""
        time_str = msg.created_at.strftime("%d/%m/%Y %H:%M:%S")
        content = html.escape(msg.content).replace("\n", "<br>")

        attachments_html = ""
        for att in msg.attachments:
            if att.content_type and att.content_type.startswith("image/"):
                attachments_html += f'<div class="att"><a href="{att.url}" target="_blank"><img src="{att.url}" style="max-width:300px;border-radius:8px;margin-top:6px;" /></a></div>'
            else:
                attachments_html += f'<div class="att"><a href="{att.url}" target="_blank" style="color:#E11D48;">📎 {html.escape(att.filename)}</a></div>'

        html_items.append(f"""
        <div class="msg">
            <img class="avatar" src="{author_avatar}" alt="{author_name}">
            <div class="msg-content">
                <div class="meta">
                    <span class="author">{author_name}</span>
                    <span class="time">{time_str}</span>
                </div>
                <div class="text">{content}</div>
                {attachments_html}
            </div>
        </div>
        """)

    full_html = f"""<!DOCTYPE html>
<html lang="vi">
<head>
    <meta charset="UTF-8">
    <title>Transcript #{ticket_id:04d} — {category_type} | HEe Tribunal</title>
    <style>
        body {{
            background-color: #0F172A;
            color: #E2E8F0;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            margin: 0;
            padding: 24px;
        }}
        .header {{
            background: linear-gradient(135deg, #881337 0%, #1E293B 100%);
            padding: 20px;
            border-radius: 12px;
            margin-bottom: 24px;
            border-left: 6px solid #E11D48;
        }}
        .header h1 {{ margin: 0 0 8px 0; font-size: 22px; color: #FFFFFF; }}
        .header p {{ margin: 4px 0; font-size: 14px; color: #CBD5E1; }}
        .msg {{
            display: flex;
            align-items: flex-start;
            margin-bottom: 16px;
            padding: 10px;
            border-radius: 8px;
            background-color: #1E293B;
        }}
        .avatar {{
            width: 40px;
            height: 40px;
            border-radius: 50%;
            margin-right: 14px;
            border: 2px solid #E11D48;
        }}
        .msg-content {{ flex: 1; }}
        .meta {{ margin-bottom: 4px; }}
        .author {{ font-weight: bold; color: #F43F5E; margin-right: 10px; font-size: 15px; }}
        .time {{ font-size: 12px; color: #64748B; }}
        .text {{ font-size: 14px; line-height: 1.5; color: #F1F5F9; word-break: break-word; }}
        .footer {{ text-align: center; margin-top: 30px; font-size: 12px; color: #475569; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>🎮 High Ego eSport — Ticket #{ticket_id:04d}</h1>
        <p><strong>Loại hỗ trợ:</strong> {html.escape(category_type)}</p>
        <p><strong>Người tạo:</strong> {html.escape(creator.display_name)} ({creator.id})</p>
        <p><strong>Đóng bởi:</strong> {html.escape(closed_by)} | <strong>Tổng số tin nhắn:</strong> {len(messages)}</p>
    </div>
    <div class="chat-container">
        {''.join(html_items)}
    </div>
    <div class="footer">
        Được ghi lại tự động bởi HEe • Tribunal | Bản quyền High Ego eSport
    </div>
</body>
</html>"""

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(full_html)

    return filepath
