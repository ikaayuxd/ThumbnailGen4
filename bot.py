import logging
import io
from PIL import Image, ImageDraw, ImageFont, ImageOps
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ConversationHandler,
    ContextTypes,
)

# 1. Setup Logging & Token
TOKEN = "7071486435:AAFD1TVkz9G1EuwQ39AEVmDJVn00vnSDgUc"
logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)

# Define States
GET_BG, GET_T1, GET_T2, GET_T3, GET_T4, GET_T5 = range(6)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🚀 **Cyber Banner Bot Started!**\n\nStep 1: Please send me the **Background Image** you want to use."
    )
    return GET_BG

async def handle_bg(update: Update, context: ContextTypes.DEFAULT_TYPE):
    photo_file = await update.message.photo[-1].get_file()
    image_data = await photo_file.download_as_bytearray()
    context.user_data['bg'] = io.BytesIO(image_data)
    
    await update.message.reply_text("✅ Background received. Now enter **Line 1** (Top Cyan Text):")
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

async def generate_and_send(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['t5'] = update.message.text
    await update.message.reply_text("🎨 Generating your banner... please wait.")

    # IMAGE GENERATION LOGIC
    width, height = 1200, 675
    radius = 60
    border_w = 14
    
    # Create Base Canvas
    base = Image.new('RGB', (width, height), (0, 0, 0))
    
    # Process Background
    bg = Image.open(context.user_data['bg']).convert("RGBA")
    bg = ImageOps.fit(bg, (width, height), centering=(0.5, 0.5))
    
    # Create dark overlay (0.4 opacity)
    overlay = Image.new('RGBA', (width, height), (0, 0, 0, 150))
    bg = Image.alpha_composite(bg, overlay)
    
    # Create Mask for Rounded Corners
    mask = Image.new('L', (width, height), 0)
    draw_mask = ImageDraw.Draw(mask)
    draw_mask.rounded_rectangle([0, 0, width, height], radius=radius, fill=255)
    
    # Apply Mask to BG
    final_img = Image.new('RGBA', (width, height), (0, 0, 0, 0))
    final_img.paste(bg, (0, 0), mask=mask)
    
    # Draw Text & Border
    draw = ImageDraw.Draw(final_img)
    
    # Draw the White Rounded Border
    draw.rounded_rectangle(
        [border_w//2, border_w//2, width - border_w//2, height - border_w//2], 
        radius=radius, outline="white", width=border_w
    )

    # Note: Using default fonts because specific .ttf files aren't on all servers.
    # To use Montserrat, upload the .ttf file to your server and use ImageFont.truetype("font.ttf", size)
    try:
        f1 = ImageFont.load_default() # Replace with your .ttf path
    except:
        f1 = ImageFont.load_default()

    # Draw Text (Simplified positioning for Bot)
    draw.text((600, 160), context.user_data['t1'].upper(), fill="#00e5ff", anchor="mm", font_size=45)
    draw.text((600, 280), context.user_data['t2'].upper(), fill="white", anchor="mm", font_size=100)
    draw.text((600, 380), context.user_data['t3'], fill="white", anchor="mm", font_size=55)
    draw.text((600, 500), context.user_data['t4'].upper(), fill="#00e5ff", anchor="mm", font_size=75)
    draw.text((600, 610), context.user_data['t5'], fill="white", anchor="mm", font_size=40)

    # Convert to RGB to save as JPG/PNG
    final_img = final_img.convert("RGB")
    bio = io.BytesIO()
    bio.name = 'banner.png'
    final_img.save(bio, 'PNG')
    bio.seek(0)

    await update.message.reply_photo(photo=bio, caption="✅ Here is your custom banner!")
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Process cancelled.", reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END

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
    print("Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()
    
