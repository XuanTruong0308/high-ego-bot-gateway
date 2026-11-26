"""
crawl_banners.py — Tự động tìm kiếm & tải Banner GIF (Pinterest, Tenor, Google Images) bằng Playwright.

Cách dùng:
    python crawl_banners.py
    python crawl_banners.py "t1 lol red banner gif"
"""

import asyncio
import os
import sys
import json
import urllib.request
import urllib.parse
from pathlib import Path
from playwright.async_api import async_playwright

OUTPUT_DIR = Path(__file__).parent / "assets" / "crawled_banners"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


async def search_and_download_banners(query: str = "league of legends red banner gif", max_downloads: int = 6):
    print(f"🔍 Bắt đầu dùng Playwright tìm kiếm banner: '{query}'...")
    found_links = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 800}
        )
        page = await context.new_page()

        # 1. Tìm trên Pinterest
        encoded_query = urllib.parse.quote(query)
        pinterest_url = f"https://www.pinterest.com/search/pins/?q={encoded_query}"
        print(f"📌 Đang quét Pinterest: {pinterest_url} ...")
        try:
            await page.goto(pinterest_url, timeout=30000, wait_until="domcontentloaded")
            await page.wait_for_timeout(4000)
            for _ in range(2):
                await page.mouse.wheel(0, 1200)
                await page.wait_for_timeout(1500)

            imgs = await page.query_selector_all("img")
            for img in imgs:
                src = await img.get_attribute("src")
                if src and "i.pinimg.com" in src:
                    # Nâng độ phân giải từ thumbnail sang bản chất lượng cao
                    hd_src = src.replace("/236x/", "/736x/").replace("/474x/", "/736x/")
                    if hd_src not in found_links:
                        found_links.append(hd_src)
        except Exception as e:
            print(f"⚠️ Lỗi quét Pinterest: {e}")

        # 2. Tìm ảnh động GIF trên Tenor
        tenor_query = query.replace(" ", "-")
        tenor_url = f"https://tenor.com/search/{tenor_query}-gifs"
        print(f"🎬 Đang quét Tenor GIFs: {tenor_url} ...")
        try:
            await page.goto(tenor_url, timeout=30000, wait_until="domcontentloaded")
            await page.wait_for_timeout(3000)
            imgs = await page.query_selector_all("img")
            for img in imgs:
                src = await img.get_attribute("src")
                if src and ".gif" in src and "tenor.com" in src:
                    if src not in found_links:
                        found_links.append(src)
        except Exception as e:
            print(f"⚠️ Lỗi quét Tenor: {e}")

        await browser.close()

    print(f"\n✅ Đã tìm thấy tổng cộng {len(found_links)} link banner tiềm năng!")

    # Lưu danh sách link JSON
    json_path = OUTPUT_DIR / "banner_links.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(found_links, f, indent=2, ensure_ascii=False)
    print(f"📝 Đã lưu danh sách link tại: {json_path}")

    # Tải về máy
    downloaded = 0
    for idx, url in enumerate(found_links, start=1):
        if downloaded >= max_downloads:
            break
        try:
            ext = ".gif" if ".gif" in url else ".jpg"
            dest = OUTPUT_DIR / f"banner_{downloaded + 1}{ext}"
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=10) as resp, open(dest, "wb") as f_out:
                f_out.write(resp.read())
            print(f"  📥 [{downloaded + 1}/{max_downloads}] Tải thành công: {dest.name}")
            downloaded += 1
        except Exception as ex:
            pass

    print(f"\n🎉 Hoàn thành! Đã tải {downloaded} banner vào: {OUTPUT_DIR}\n")


if __name__ == "__main__":
    search_term = sys.argv[1] if len(sys.argv) > 1 else "league of legends red banner gif"
    asyncio.run(search_and_download_banners(search_term))
