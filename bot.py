#!/usr/bin/env python3
import asyncio
import io
import logging
import os
import re
import subprocess
import tempfile
import torch
from pathlib import Path
from flask import Flask, request, jsonify
from telegram import Update, InlineQueryResultVoice
from telegram.constants import ParseMode
from telegram.ext import (
    Application, CommandHandler, ContextTypes, ConversationHandler, 
    InlineQueryHandler, MessageHandler, filters
)
from TTS.api import TTS

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Config
TOKEN = ("6590125561:AAF-RwnhDkmgSB-F2NtyxbXvCidllzAUZqc")
if not TOKEN:
    raise ValueError("BOT_TOKEN environment variable required")

PORT = int(os.environ.get("PORT", 8080))
HOST = "0.0.0.0"

# TTS Setup
device = "cpu"  # Render has no GPU
tts = TTS("tts_models/multilingual/multi-dataset/xtts_v2").to(device)

# Bot state
ratelimit = {}
VOICES_DIR = Path("voices")
WAITING_VOICE, WAITING_TEXT = range(2)
SAMPLE_VOICES = ["en_sample.wav"]
application = None

# Flask app
app = Flask(__name__)

def synthesize(text, lang="en", speaker_wav=None, speed=1.0):
    """Generate TTS audio as OGG bytes"""
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp_wav, \
         tempfile.NamedTemporaryFile(suffix=".ogg", delete=False) as tmp_ogg:
        
        # Generate WAV
        tts.tts_to_file(
            text=text[:300],  # Render CPU limit
            speaker_wav=speaker_wav,
            language=lang,
            file_path=tmp_wav.name
        )
        
        # Convert to OGG Opus (Telegram format)
        subprocess.run([
            "ffmpeg", "-y", "-i", tmp_wav.name, 
            "-c:a", "libopus", "-b:a", "64k", tmp_ogg.name
        ], check=True, capture_output=True)
        
        # Read and cleanup
        with open(tmp_ogg.name, "rb") as f:
            audio = f.read()
        os.unlink(tmp_wav.name)
        os.unlink(tmp_ogg.name)
        return audio

async def rate_limit_check(user_id):
    """10s cooldown per user"""
    loop = asyncio.get_event_loop()
    now = loop.time()
    if user_id in ratelimit and now - ratelimit[user_id] < 10:
        return False
    ratelimit[user_id] = now
    return True

# Bot Handlers
async def start(update, context):
    await update.message.reply_text(
        "🚀 Advanced TTS Bot

"
        "• /tts Hello world --lang en --voice en_sample.wav
"
        "• /clone - Upload voice → send text
"
        "• /voices - Hear samples
"
        "• @botquery - Inline anywhere",
        parse_mode=ParseMode.HTML
    )

async def voices(update, context):
    await update.message.reply_text("🎤 Voice Samples:")
    for voice_file in SAMPLE_VOICES:
        voice_path = VOICES_DIR / voice_file
        if voice_path.exists():
            try:
                audio = synthesize("This is a voice sample.", speaker_wav=str(voice_path))
                await update.message.reply_voice(
                    io.BytesIO(audio), 
                    caption=f"Sample: {voice_file}"
                )
            except Exception as e:
                logger.error(f"Voice sample error: {e}")

async def tts_cmd(update, context):
    if not await rate_limit_check(update.effective_user.id):
        await update.message.reply_text("⏳ Wait 10 seconds (rate limit)")
        return
    
    if not context.args:
        await update.message.reply_text(
            "Usage:
/tts Hello --lang en --voice en_sample.wav --speed 1.2"
        )
        return
    
    # Parse args
    args_str = " ".join(context.args)
    text = args_str.split("--")[0].strip()
    
    lang = "en"
    voice_path = None
    speed = 1.0
    
    if "--" in args_str:
        params = " ".join(args_str.split("--")[1:])
        lang_match = re.search(r'langs+(w+)', params, re.I)
        if lang_match:
            lang = lang_match.group(1)
        
        voice_match = re.search(r'voices+([w_]+.wav)', params, re.I)
        if voice_match:
            voice_path = str(VOICES_DIR / voice_match.group(1))
        
        speed_match = re.search(r'speeds+([d.]+)', params, re.I)
        if speed_match:
            speed = float(speed_match.group(1))
    
    try:
        audio = synthesize(text, lang, voice_path, speed)
        await update.message.reply_voice(
            io.BytesIO(audio),
            title=text[:64],
            caption=f"Lang: {lang} | Speed: {speed}x"
        )
    except Exception as e:
        logger.error(f"TTS error: {e}")
        await update.message.reply_text(
            "❌ Error generating audio.
"
            "• Keep text short (<300 chars)
"
            "• Use valid language codes
"
            "• Check voice file exists"
        )

async def clone_voice(update, context):
    """Start voice cloning conversation"""
    await update.message.reply_text(
        "🎤 Send a voice message (6-10 seconds, clear speech)"
    )
    return WAITING_VOICE

async def receive_voice(update, context):
    """Receive and save uploaded voice"""
    if update.message.voice:
        voice_file = await update.message.voice.get_file()
    elif update.message.audio:
        voice_file = await update.message.audio.get_file()
    else:
        await update.message.reply_text("Please send a voice message")
        return WAITING_VOICE
    
    # Download and convert
    temp_path = f"/tmp/{update.effective_user.id}.ogg"
    wav_path = f"/tmp/{update.effective_user.id}.wav"
    
    await voice_file.download_to_drive(temp_path)
    
    # Convert to WAV for XTTS
    subprocess.run([
        "ffmpeg", "-y", "-i", temp_path, wav_path, "-ar", "22050"
    ], check=True, capture_output=True)
    os.unlink(temp_path)
    
    context.user_data["custom_voice"] = wav_path
    await update.message.reply_text("✅ Voice cloned! Now send text to synthesize.")
    return WAITING_TEXT

async def receive_text(update, context):
    """Generate TTS with cloned voice"""
    if not await rate_limit_check(update.effective_user.id):
        await update.message.reply_text("⏳ Wait 10 seconds")
        return WAITING_TEXT
    
    text = update.message.text
    voice_path = context.user_data.get("custom_voice")
    
    if not voice_path or not os.path.exists(voice_path):
        await update.message.reply_text("❌ No voice saved. Use /clone first.")
        return ConversationHandler.END
    
    try:
        audio = synthesize(text, "en", voice_path)
        await update.message.reply_voice(
            io.BytesIO(audio),
            caption="🎙️ Voice cloned successfully!"
        )
    except Exception as e:
        logger.error(f"Clone synthesis error: {e}")
        await update.message.reply_text("❌ Voice synthesis failed")
    
    # Cleanup
    if os.path.exists(voice_path):
        os.unlink(voice_path)
    context.user_data.clear()
    return ConversationHandler.END

async def cancel(update, context):
    """Cancel conversation"""
    voice_path = context.user_data.get("custom_voice")
    if voice_path and os.path.exists(voice_path):
        os.unlink(voice_path)
    context.user_data.clear()
    await update.message.reply_text("❌ Cancelled")
    return ConversationHandler.END

async def inline_tts(update, context):
    """Inline query handler"""
    query = update.inline_query.query
    if not query or len(query) > 100:
        return
    
    try:
        audio = synthesize(query[:100])
        results = [InlineQueryResultVoice(
            id="tts1",
            voice=io.BytesIO(audio),
            title=query[:64],
            caption=f"{query[:100]} (en)"
        )]
        await update.inline_query.answer(results, cache_time=10)
    except:
        pass  # Silent fail for inline

# Flask Routes
@app.route("/webhook", methods=["POST"])
def webhook():
    """Telegram webhook endpoint"""
    try:
        json_data = request.get_json()
        update = Update.de_json(json_data, application.bot)
        asyncio.run(application.process_update(update))
        return jsonify({"status": "ok"}), 200
    except Exception as e:
        logger.error(f"Webhook error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/")
def home():
    return "TTS Bot is running!"

# Bot Setup
def create_application():
    global application
    application = Application.builder().token(TOKEN).concurrent_updates(True).build()
    
    # Conversation handler for voice cloning
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("clone", clone_voice)],
        states={
            WAITING_VOICE: [MessageHandler(filters.VOICE | filters.AUDIO, receive_voice)],
            WAITING_TEXT: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_text)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )
    
    # Handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("voices", voices))
    application.add_handler(CommandHandler("tts", tts_cmd))
    application.add_handler(conv_handler)
    application.add_handler(InlineQueryHandler(inline_tts))
    
    return application

def main():
    # Create directories
    VOICES_DIR.mkdir(exist_ok=True)
    
    # Initialize bot
    create_application()
    
    # Development polling
    if os.getenv("ENV") != "production":
        logger.info("Starting in polling mode...")
        application.run_polling(drop_pending_updates=True)
    else:
        logger.info(f"Starting webhook server on {HOST}:{PORT}")
        app.run(host=HOST, port=PORT, debug=False)

if __name__ == "__main__":
    main()
