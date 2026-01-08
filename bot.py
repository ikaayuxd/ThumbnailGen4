#!/usr/bin/env python3
# Advanced TTS Telegram Bot with XTTS-v2 - Local, Multi-lang, Voice Cloning

import asyncio
import io
import logging
import os
import re
import subprocess
import tempfile
from pathlib import Path

import torch
from flask import Flask, request
from telegram import Update, InlineQueryResultVoice, Voice
from telegram.constants import ParseMode
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    InlineQueryHandler,
    MessageHandler,
    filters,
)
from TTS.api import TTS

# Enable logging
logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

TOKEN = ("6590125561:AAF-RwnhDkmgSB-F2NtyxbXvCidllzAUZqc")
if not TOKEN:
    raise ValueError("BOT_TOKEN env var required")

PORT = int(os.environ.get("PORT", 8080))
URL = f"https://{request.host}" if request else "https://yourapp.onrender.com"  # Update post-deploy

device = "cuda" if torch.cuda.is_available() else "cpu"
tts = TTS("tts_models/multilingual/multi-dataset/xtts_v2").to(device)

# State for conversation (voice upload)
WAITING_VOICE, WAITING_TEXT = range(2)

# Rate limit: user_id -> last_time
ratelimit = {}

VOICES_DIR = Path("voices")
SAMPLE_VOICES = ["en_sample.wav", "hi_sample.wav"]  # Add more

app = Flask(__name__)

async def rate_limit_check(user_id: int) -> bool:
    now = asyncio.get_event_loop().time()
    if user_id in ratelimit and now - ratelimit[user_id] < 10:  # 10s cooldown
        return False
    ratelimit[user_id] = now
    return True

def synthesize(text: str, lang: str = "en", speaker_wav: str = None, speed: float = 1.0) -> bytes:
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp_in, \
         tempfile.NamedTemporaryFile(suffix=".ogg", delete=False) as tmp_out:
        tts.tts_to_file(
            text=text[:400],  # Limit length for CPU
            speaker_wav=speaker_wav,
            language=lang,
            file_path=tmp_in.name,
            speed=speed
        )
        subprocess.run(["ffmpeg", "-i", tmp_in.name, "-c:a", "libopus", tmp_out.name], check=True)
        with open(tmp_out.name, "rb") as f:
            audio = f.read()
        os.unlink(tmp_in.name)
        os.unlink(tmp_out.name)
        return audio

@app.route("/webhook", methods=["POST"])
async def webhook():
    update = Update.de_json(request.get_json(), application.bot)
    await application.process_update(update)
    return "", 200

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "🚀 Futuristic TTS Bot!

"
        "/tts <text> [--lang en|hi|es] [--speed 1.0] [--voice sample]
"
        "/clone - Upload voice then text
"
        "/voices - Samples
"
        "@bot text (inline)",
        parse_mode=ParseMode.HTML
    )

async def voices(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    msg = "🎤 Sample Voices:
"
    for v in SAMPLE_VOICES:
        audio = synthesize("Voice sample.", speaker_wav=str(VOICES_DIR / v), lang="en")
        await update.message.reply_voice(io.BytesIO(audio), caption=v)
    await update.message.reply_text("Upload your 6s WAV for /clone")

async def tts_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await rate_limit_check(update.effective_user.id):
        await update.message.reply_text("⏳ Wait 10s (rate limit)")
        return
    if not context.args:
        await update.message.reply_text("Usage: /tts Hello --lang en --voice en_sample.wav --speed 1.2")
        return
    text = " ".join(context.args).split("--")[0].strip()
    args = " ".join(context.args).split("--")[1:]
    lang = re.search(r"langs+(w+)", " ".join(args), re.I)
    lang = lang.group(1) if lang else "en"
    voice = re.search(r"voices+([w_]+.wav)", " ".join(args), re.I)
    voice_path = str(VOICES_DIR / (voice.group(1) if voice else "en_sample.wav")) if voice else None
    speed_match = re.search(r"speeds+([d.]+)", " ".join(args), re.I)
    speed = float(speed_match.group(1)) if speed_match else 1.0

    try:
        audio = synthesize(text, lang, voice_path, speed)
        await update.message.reply_voice(io.BytesIO(audio), title=text[:64])
    except Exception as e:
        logger.error(e)
        await update.message.reply_text("❌ Error: Short text, check voice/lang")

async def receive_voice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    voice_file = await update.voice.get_file()
    voice_path = f"/tmp/{update.effective_user.id}.wav"
    await voice_file.download_to_drive(voice_path)
    context.user_data["custom_voice"] = voice_path
    await update.message.reply_text("✅ Voice saved! Send text to synthesize.")
    return WAITING_TEXT

async def receive_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not await rate_limit_check(update.effective_user.id):
        return WAITING_TEXT
    text = update.message.text
    voice_wav = context.user_data.get("custom_voice")
    if not voice_wav:
        await update.message.reply_text("❌ No voice uploaded. Use /clone first.")
        return ConversationHandler.END
    try:
        audio = synthesize(text, "en", voice_wav)  # Default en for clone
        await update.message.reply_voice(io.BytesIO(audio), caption="Cloned!")
        os.unlink(voice_wav)
        context.user_data.pop("custom_voice", None)
    except Exception as e:
        logger.error(e)
        await update.message.reply_text("❌ Synthesis failed.")
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if "custom_voice" in context.user_data:
        os.unlink(context.user_data["custom_voice"])
    context.user_data.clear()
    await update.message.reply_text("Cancelled.")
    return ConversationHandler.END

async def inline_tts(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.inline_query.query or "Demo TTS"
    if len(query) > 200:
        return
    # Simple inline: use default
    try:
        audio = synthesize(query[:100])
        results = [InlineQueryResultVoice(
            id="1", voice=io.BytesIO(audio),
            title=query[:64], caption=f"{query} (en default)"
        )]
        await update.inline_query.answer(results, cache_time=1)
    except:
        pass  # Silent fail on inline

def main():
    global application
    application = (
        Application.builder().token(TOKEN).concurrent_updates(True).build()
    )

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("clone", receive_voice)],
        states={
            WAITING_VOICE: [MessageHandler(filters.VOICE | filters.AUDIO, receive_voice)],
            WAITING_TEXT: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_text)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("voices", voices))
    application.add_handler(CommandHandler("tts", tts_cmd))
    application.add_handler(conv_handler)
    application.add_handler(InlineQueryHandler(inline_tts))
    application.add_handler(MessageHandler(filters.AUDIO | filters.VOICE, voices))  # Fallback

    # Webhook in production
    if os.getenv("ENV") == "production":
        application.run_webhook(
            listen="0.0.0.0",
            port=PORT,
            url_path="/webhook",
            webhook_url=f"{URL}/webhook"
        )
    else:
        application.run_polling()

if __name__ == "__main__":
    VOICES_DIR.mkdir(exist_ok=True)
    main()
