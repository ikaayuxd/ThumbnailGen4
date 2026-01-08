#!/usr/bin/env python3
import asyncio
import io
import logging
import os
import re
import subprocess
import tempfile
from pathlib import Path
import torch
from quart import Flask, request
from telegram import Update, InlineQueryResultVoice
from telegram.constants import ParseMode
from telegram.ext import Application, CommandHandler, ContextTypes, ConversationHandler, InlineQueryHandler, MessageHandler, filters
from TTS.api import TTS

logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

TOKEN = ("6590125561:AAF-RwnhDkmgSB-F2NtyxbXvCidllzAUZqc")
if not TOKEN:
    raise ValueError("BOT_TOKEN env var required")

PORT = int(os.environ.get("PORT", 8080))

device = "cuda" if torch.cuda.is_available() else "cpu"
tts = TTS("tts_models/multilingual/multi-dataset/xtts_v2").to(device)

ratelimit = {}
VOICES_DIR = Path("voices")
SAMPLE_VOICES = ["en_sample.wav", "hi_sample.wav"]
WAITING_VOICE, WAITING_TEXT = range(2)

app = Flask(__name__)
application = None

async def rate_limit_check(user_id):
    loop = asyncio.get_event_loop()
    now = loop.time()
    if user_id in ratelimit and now - ratelimit[user_id] < 10:
        return False
    ratelimit[user_id] = now
    return True

def synthesize(text, lang="en", speaker_wav=None, speed=1.0):
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp_in, tempfile.NamedTemporaryFile(suffix=".ogg", delete=False) as tmp_out:
        tts.tts_to_file(text=text[:400], speaker_wav=speaker_wav, language=lang, file_path=tmp_in.name)
        subprocess.run(["ffmpeg", "-i", tmp_in.name, "-c:a", "libopus", tmp_out.name], check=True, capture_output=True)
        with open(tmp_out.name, "rb") as f:
            audio = f.read()
        os.unlink(tmp_in.name)
        os.unlink(tmp_out.name)
        return audio

@app.route("/webhook", methods=["POST"])
async def webhook():
    json_data = await request.get_json()
    update = Update.de_json(json_data, application.bot)
    await application.process_update(update)
    return "", 200

async def start(update, context):
    text = "🚀 Futuristic TTS Bot! /tts <text> [--lang en|hi] [--voice sample] [--speed 1.2] /clone /voices Inline: @bot text"
    await update.message.reply_text(text, parse_mode=ParseMode.HTML)

async def voices(update, context):
    msg = "🎤 Samples:"
    await update.message.reply_text(msg)
    for v in SAMPLE_VOICES:
        p = VOICES_DIR / v
        if p.exists():
            audio = synthesize("Voice sample.", speaker_wav=str(p), lang="en")
            await update.message.reply_voice(io.BytesIO(audio), caption=v)

async def tts_cmd(update, context):
    if not await rate_limit_check(update.effective_user.id):
        await update.message.reply_text("⏳ Wait 10s")
        return
    if not context.args:
        await update.message.reply_text("Usage: /tts Hello --lang en --voice en_sample.wav --speed 1.2")
        return
    args_str = " ".join(context.args)
    text = args_str.split("--")[0].strip()
    params = " ".join(args_str.split("--")[1:])
    lang_match = re.search(r"langs+(w+)", params, re.I)
    lang = lang_match.group(1) if lang_match else "en"
    voice_match = re.search(r"voices+([w_]+.wav)", params, re.I)
    voice_path = str(VOICES_DIR / voice_match.group(1)) if voice_match else None
    speed_match = re.search(r"speeds+([d.]+)", params, re.I)
    speed = float(speed_match.group(1)) if speed_match else 1.0

    try:
        audio = synthesize(text, lang, voice_path, speed)
        await update.message.reply_voice(io.BytesIO(audio), title=text[:64])
    except Exception as e:
        logger.error(str(e))
        await update.message.reply_text("❌ Error: Short text, valid lang/voice")

async def receive_voice(update, context):
    voice_file = await update.message.voice.get_file() if update.message.voice else await update.message.audio.get_file()
    voice_path = f"/tmp/{update.effective_user.id}.ogg"
    await voice_file.download_to_drive(voice_path)
    # Convert to wav if needed
    wav_path = voice_path.replace(".ogg", ".wav")
    subprocess.run(["ffmpeg", "-i", voice_path, wav_path], check=True, capture_output=True)
    os.unlink(voice_path)
    context.user_data["custom_voice"] = wav_path
    await update.message.reply_text("✅ Voice cloned! Send text.")
    return WAITING_TEXT

async def receive_text(update, context):
    if not await rate_limit_check(update.effective_user.id):
        return WAITING_TEXT
    text = update.message.text
    voice_wav = context.user_data.get("custom_voice")
    if not voice_wav:
        await update.message.reply_text("❌ No voice. /clone first.")
        return ConversationHandler.END
    try:
        audio = synthesize(text, "en", voice_wav)
        await update.message.reply_voice(io.BytesIO(audio), caption="Cloned!")
        if os.path.exists(voice_wav):
            os.unlink(voice_wav)
        context.user_data.pop("custom_voice", None)
    except Exception as e:
        logger.error(str(e))
        await update.message.reply_text("❌ Failed.")
    return ConversationHandler.END

async def cancel(update, context):
    if "custom_voice" in context.user_data and os.path.exists(context.user_data["custom_voice"]):
        os.unlink(context.user_data["custom_voice"])
    context.user_data.clear()
    await update.message.reply_text("Cancelled.")
    return ConversationHandler.END

async def inline_tts(update, context):
    query = update.inline_query.query
    if not query or len(query) > 100:
        return
    try:
        audio = synthesize(query)
        results = [InlineQueryResultVoice(id="tts", voice=io.BytesIO(audio), title=query[:64])]
        await update.inline_query.answer(results, cache_time=5)
    except:
        pass

def main():
    global application
    application = Application.builder().token(TOKEN).concurrent_updates(True).build()

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

    app.run(host="0.0.0.0", port=PORT, debug=False)

if __name__ == "__main__":
    VOICES_DIR.mkdir(exist_ok=True)
    main()
