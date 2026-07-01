"""
Telegram Video Downloader Bot
A simple Telegram bot with quality selection.
"""

import asyncio
import os
from dotenv import load_dotenv

from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import FSInputFile, InlineKeyboardMarkup, InlineKeyboardButton

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN is not set in .env file!")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

DOWNLOADS_DIR = "downloads"
os.makedirs(DOWNLOADS_DIR, exist_ok=True)

# Store user pending URLs (simple in-memory storage)
user_pending = {}  # user_id: url

# Quality options
QUALITY_OPTIONS = {
    "360": "best[height<=360]",
    "720": "best[height<=720]",
    "1080": "best[height<=1080]",
    "audio": "bestaudio/best"
}


@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📖 Help", callback_data="help")]
    ])
    
    await message.answer(
        "👋 Welcome to Video Downloader Bot!\n\n"
        "Send me a video link from YouTube, Instagram, TikTok, Aparat, etc.\n"
        "Then choose the quality.",
        reply_markup=keyboard
    )


@dp.message(F.text)
async def handle_link(message: types.Message):
    """Save link and show quality buttons"""
    url = message.text.strip()
    
    if not url.startswith(("http://", "https://")):
        await message.answer("❌ Please send a valid link.")
        return

    user_pending[message.from_user.id] = url

    # Quality selection keyboard
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📱 360p", callback_data="q_360")],
        [InlineKeyboardButton(text="📺 720p (Recommended)", callback_data="q_720")],
        [InlineKeyboardButton(text="🎥 1080p", callback_data="q_1080")],
        [InlineKeyboardButton(text="🎵 Audio Only (MP3)", callback_data="q_audio")]
    ])

    await message.answer(
        "✅ Link received!\n"
        "Choose the quality:",
        reply_markup=keyboard
    )


@dp.callback_query(F.data.startswith("q_"))
async def handle_quality(callback: types.CallbackQuery):
    """Process download with selected quality"""
    user_id = callback.from_user.id
    quality_key = callback.data.split("_")[1]
    
    if user_id not in user_pending:
        await callback.message.edit_text("❌ Link expired. Please send the link again.")
        return

    url = user_pending.pop(user_id)
    quality_format = QUALITY_OPTIONS.get(quality_key, QUALITY_OPTIONS["720"])
    
    status_msg = await callback.message.edit_text(f"⏳ Downloading in {quality_key.upper()} quality...")

    try:
        ydl_opts = {
            'format': quality_format,
            'outtmpl': os.path.join(DOWNLOADS_DIR, '%(title)s.%(ext)s'),
            'noplaylist': True,
            'quiet': True,
            'no_warnings': True,
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)

        file_size_mb = os.path.getsize(filename) / (1024 * 1024)

        await status_msg.edit_text(
            f"✅ Download completed!\n"
            f"Quality: {quality_key.upper()}\n"
            f"Title: {info.get('title', 'Video')}\n"
            f"Size: {file_size_mb:.1f} MB\n"
            f"📤 Sending..."
        )

        if quality_key == "audio":
            await callback.message.answer_audio(FSInputFile(filename))
        else:
            await callback.message.answer_video(
                FSInputFile(filename),
                caption=f"Downloaded by @{callback.from_user.username or 'user'}",
                supports_streaming=True
            )

        # Cleanup
        if os.path.exists(filename):
            os.remove(filename)

    except Exception as e:
        await status_msg.edit_text(f"❌ Error:\n{str(e)[:300]}")


@dp.callback_query(F.data == "help")
async def show_help(callback: types.CallbackQuery):
    await callback.message.answer(
        "🔗 Send any video link.\n"
        "Supported: YouTube, Instagram, TikTok, Aparat, and more.\n\n"
        "After sending link, choose quality."
    )
    await callback.answer()


async def main():
    print("🚀 Bot is running with quality selection...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
