import logging
import io
from PIL import Image, ImageDraw, ImageFont, ImageOps
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, constants
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
    ContextTypes,
    ConversationHandler
)

# --- Configuration ---
TOKEN = "7071486435:AAFD1TVkz9G1EuwQ39AEVmDJVn00vnSDgUc"
logging.basicConfig(format="%(asctime)s - %(levelname)s - %(message)s", level=logging.INFO)

# States
START_ROUTE, EDIT_ROUTE = range(2)

# --- Utility Functions ---

def get_main_keyboard():
    keyboard = [
        [InlineKeyboardButton("✏️ Line 1 (Top)", callback_data='L1'),
         InlineKeyboardButton("✏️ Line 2 (Hero)", callback_data='L2')],
        [InlineKeyboardButton("✏️ Line 3 (@User)", callback_data='L3'),
         InlineKeyboardButton("✏️ Line 4 (Sub)", callback_data='L4')],
        [InlineKeyboardButton("✏️ Line 5 (Footer)", callback_data='L5')],
        [InlineKeyboardButton("🖼 Change Background", callback_data='CHANGE_BG')],
        [InlineKeyboardButton("✅ GENERATE FINAL", callback_data='RENDER')]
    ]
    return InlineKeyboardMarkup(keyboard)

async def generate_banner(data):
    """Core rendering engine with rounded corners and border."""
    width, height = 1200, 675
    radius, border_w = 60, 14
    
    # 1. Background
    bg_stream = io.BytesIO(data['bg_bytes'])
    bg = Image.open(bg_stream).convert("RGBA")
    bg = ImageOps.fit(bg, (width, height), centering=(0.5, 0.5))
    
    # 2. Dark Overlay
    overlay = Image.new('RGBA', (width, height), (0, 0, 0, 160))
    bg = Image.alpha_composite(bg, overlay)
    
    # 3. Mask & Rounded Corners
    mask = Image.new('L', (width, height), 0)
    draw_mask = ImageDraw.Draw(mask)
    draw_mask.rounded_rectangle([0, 0, width, height], radius=radius, fill=255)
    
    final_img = Image.new('RGBA', (width, height), (0, 0, 0, 0))
    final_img.paste(bg, (0, 0), mask=mask)
    draw = ImageDraw.Draw(final_img)
    
    # 4. White Border
    draw.rounded_rectangle(
        [border_w//2, border_w//2, width - border_w//2, height - border_w//2], 
        radius=radius, outline="white", width=border_w
    )

    # 5. Text Rendering (Using default sizes, scalable)
    draw.text((600, 160), data.get('t1', 'TOP TEXT').upper(), fill="#00e5ff", anchor="mm", font_size=45)
    draw.text((600, 280), data.get('t2', 'MAIN TITLE').upper(), fill="white", anchor="mm", font_size=110)
    draw.text((600, 380), data.get('t3', '@username'), fill="white", anchor="mm", font_size=55)
    draw.text((600, 500), data.get('t4', 'SUBTITLE TEXT').upper(), fill="#00e5ff", anchor="mm", font_size=75)
    draw.text((600, 610), data.get('t5', 'Footer content here'), fill="white", anchor="mm", font_size=40)

    # Output
    bio = io.BytesIO()
    final_img.convert("RGB").save(bio, 'PNG')
    bio.seek(0)
    return bio

# --- Bot Handlers ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Default values
    context.user_data.update({
        't1': 'JAILBREAK PROMPT FOR',
        't2': 'LEGEND × TRICKS',
        't3': '@LEGENDXTRICKS',
        't4': "CHAT GPT AND OTHER AI'S",
        't5': 'Premium And Paid Content Absolutely Free'
    })
    
    await update.message.reply_text(
        "👋 *Welcome to Legend Banner Studio!*\n\n"
        "To begin, please send the **Background Image** you want to use.",
        parse_mode=constants.ParseMode.MARKDOWN
    )
    return START_ROUTE

async def handle_bg(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Visual Guidance: Download BG and show control panel
    photo = await update.message.photo[-1].get_file()
    context.user_data['bg_bytes'] = await photo.download_as_bytearray()
    
    await update.message.reply_text(
        "✅ *Background Loaded!*\n\nUse the buttons below to customize each line. When ready, click Generate.",
        reply_markup=get_main_keyboard(),
        parse_mode=constants.ParseMode.MARKDOWN
    )
    return EDIT_ROUTE

async def button_tap(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.data == 'RENDER':
        await query.edit_message_text("⏳ *Rendering your high-quality banner...*", parse_mode=constants.ParseMode.MARKDOWN)
        context.application.create_task(context.bot.send_chat_action(chat_id=query.message.chat_id, action="upload_photo"))
        
        image_result = await generate_banner(context.user_data)
        await query.message.reply_photo(photo=image_result, caption="🚀 *Here is your professional banner!*", parse_mode=constants.ParseMode.MARKDOWN)
        return EDIT_ROUTE

    if query.data == 'CHANGE_BG':
        await query.edit_message_text("🖼 Please send a new **Background Image**.")
        return START_ROUTE

    # Handle text editing requests
    context.user_data['editing'] = query.data
    labels = {"L1": "Line 1 (Cyan Top)", "L2": "Line 2 (White Hero)", "L3": "Line 3 (Handle)", "L4": "Line 4 (Cyan Sub)", "L5": "Line 5 (Footer)"}
    await query.edit_message_text(f"📝 Send the new text for: *{labels[query.data]}*", parse_mode=constants.ParseMode.MARKDOWN)
    return EDIT_ROUTE

async def update_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    target = context.user_data.get('editing')
    if target:
        key = target.lower().replace('l', 't')
        context.user_data[key] = update.message.text
        
    await update.message.reply_text(
        "✅ *Text Updated!* What's next?",
        reply_markup=get_main_keyboard(),
        parse_mode=constants.ParseMode.MARKDOWN
    )
    return EDIT_ROUTE

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Session ended. Type /start to begin.")
    return ConversationHandler.END

# --- Main ---

def main():
    app = Application.builder().token(TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            START_ROUTE: [MessageHandler(filters.PHOTO, handle_bg)],
            EDIT_ROUTE: [
                CallbackQueryHandler(button_tap),
                MessageHandler(filters.TEXT & ~filters.COMMAND, update_text),
                MessageHandler(filters.PHOTO, handle_bg)
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    app.add_handler(conv_handler)
    print("Professional Legend Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()
    
