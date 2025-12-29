import logging
import io
from PIL import Image, ImageDraw, ImageFont, ImageOps
from telegram import Update, ReplyKeyboardRemove
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ConversationHandler,
    ContextTypes,
)

# 1. Configuration
TOKEN = "7071486435:AAFD1TVkz9G1EuwQ39AEVmDJVn00vnSDgUc"

# Setup Logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)

# Define States
GET_BG, GET_T1, GET_T2, GET_T3, GET_T4, GET_T5 = range(6)

# --- State Functions ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🚀 *Cyber Banner Bot Started!*\n\n"
        "Please send me the **Background Image** you want to use.",
        parse_mode="Markdown"
    )
    return GET_BG

async def handle_bg(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Get the highest resolution photo
    photo_file = await update.message.photo[-1].get_file()
    image_data = await photo_file.download_as_bytearray()
    context.user_data['bg'] = io.BytesIO(image_data)
    
    await update.message.reply_text("✅ Background received.\n\nEnter **Line 1** (Top Cyan Text):")
    return GET_T1

async def handle_t1(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['t1'] = update.message.text
    await update.message.reply_text("Enter **Line 2** (Main Large White Title):")
    return GET_T2

async def handle_t2(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['t2'] = update.message.text
    await update.message.reply_text("Enter **Line 3** (@Handle):")
    return GET_T3

async def handle_t3(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['t3'] = update.message.text
    await update.message.reply_text("Enter **Line 4** (Bottom Cyan Sub-title):")
    return GET_T4

async def handle_t4(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['t4'] = update.message.text
    await update.message.reply_text("Enter **Line 5** (Footer Serif Text):")
    return GET_T5

async def handle_t5(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['t5'] = update.message.text
    # All data collected, move to generation
    return await generate_and_send(update, context)

# --- Generation Logic ---

async def generate_and_send(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🎨 Generating your banner... please wait.")

    try:
        # Dimensions and style settings
        width, height = 1200, 675
        radius = 60
        border_w = 14
        
        # Load and process Background
        bg_stream = context.user_data.get('bg')
        bg_stream.seek(0)
        bg = Image.open(bg_stream).convert("RGBA")
        bg = ImageOps.fit(bg, (width, height), centering=(0.5, 0.5))
        
        # Create dark overlay (match the original darkened look)
        overlay = Image.new('RGBA', (width, height), (0, 0, 0, 160))
        bg = Image.alpha_composite(bg, overlay)
        
        # Create Rounded Mask
        mask = Image.new('L', (width, height), 0)
        draw_mask = ImageDraw.Draw(mask)
        draw_mask.rounded_rectangle([0, 0, width, height], radius=radius, fill=255)
        
        # Final Transparent Canvas
        final_img = Image.new('RGBA', (width, height), (0, 0, 0, 0))
        final_img.paste(bg, (0, 0), mask=mask)
        draw = ImageDraw.Draw(final_img)
        
        # Draw the White Rounded Border
        draw.rounded_rectangle(
            [border_w//2, border_w//2, width - border_w//2, height - border_w//2], 
            radius=radius, outline="white", width=border_w
        )

        # Draw Text Lines
        # Note: Using font_size parameter (requires Pillow 10+)
        draw.text((600, 160), context.user_data['t1'].upper(), fill="#00e5ff", anchor="mm", font_size=45)
        draw.text((600, 280), context.user_data['t2'].upper(), fill="white", anchor="mm", font_size=110)
        draw.text((600, 380), context.user_data['t3'], fill="white", anchor="mm", font_size=55)
        draw.text((600, 500), context.user_data['t4'].upper(), fill="#00e5ff", anchor="mm", font_size=75)
        draw.text((600, 610), context.user_data['t5'], fill="white", anchor="mm", font_size=40)

        # Save to buffer
        final_img = final_img.convert("RGB")
        bio = io.BytesIO()
        bio.name = 'banner.png'
        final_img.save(bio, 'PNG')
        bio.seek(0)

        await update.message.reply_photo(photo=bio, caption="✅ Your custom banner is ready!")
        
    except Exception as e:
        logging.error(f"Generation error: {e}")
        await update.message.reply_text("❌ An error occurred during image generation.")

    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Process cancelled. Use /start to begin again.", reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END

# --- Main App ---

def main():
    app = Application.builder().token(TOKEN).build()
    
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            GET_BG: [MessageHandler(filters.PHOTO, handle_bg)],
            GET_T1: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_t1)],
            GET_T2: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_t2)],
            GET_T3: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_t3)],
            GET_T4: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_t4)],
            GET_T5: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_t5)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    app.add_handler(conv_handler)
    print("Bot is live... Press Ctrl+C to stop.")
    app.run_polling()

if __name__ == "__main__":
    main()
    
