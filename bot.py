import telebot
from PIL import Image, ImageDraw, ImageFont
import os
import time
import textwrap

BOT_TOKEN = '6590125561:AAFEIckYYEM2wg9JIzZy9MCamgwRt_BfQsg' # Your token
bot = telebot.TeleBot(BOT_TOKEN)

def add_text_to_image(image_path, center_text, above_text, below_text):
    try:
        img = Image.open(image_path)
        draw = ImageDraw.Draw(img)
        width, height = img.size

        # Choose a font
        try:
            font_center = ImageFont.truetype("arial.ttf", 40) # Adjust size as needed
            font_above_below = ImageFont.truetype("arial.ttf", 30) # Smaller for above/below
        except IOError:
            font_center = ImageFont.load_default()
            font_above_below = ImageFont.load_default()
            print("Default font used.")

        # Center text
        center_text_size = draw.textsize(center_text, font=font_center)
        center_x = (width - center_text_size[0]) // 2
        center_y = (height - center_text_size[1]) // 2
        draw.text((center_x, center_y), center_text, font=font_center, fill=(255, 0, 0))

        # Text above center
        if above_text:
            above_text_size = draw.textsize(above_text, font=font_above_below)
            above_x = (width - above_text_size[0]) // 2
            above_y = center_y - center_text_size[1] - 10 # Adjust spacing as needed
            draw.text((above_x, above_y), above_text, font=font_above_below, fill=(0, 0, 255)) # Blue

        # Text below center
        if below_text:
            below_text_size = draw.textsize(below_text, font=font_above_below)
            below_x = (width - below_text_size[0]) // 2
            below_y = center_y + center_text_size[1] + 10 # Adjust spacing as needed
            draw.text((below_x, below_y), below_text, font=font_above_below, fill=(0, 255, 0)) # Green

        timestamp = int(time.time())
        output_filename = f"output_{timestamp}.jpg"
        img.save(output_filename)
        return output_filename
    except Exception as e:
        return f"Error processing image: {e}"

@bot.message_handler(commands=['start'])
def start(message):
    bot.reply_to(message, "Send me the image.")
    bot.register_next_step_handler(message, get_center_text)

def get_center_text(message):
    if message.photo:
        file_info = bot.get_file(message.photo[-1].file_id)
        downloaded_file = bot.download_file(file_info.file_path)
        image_filename = "temp_image.jpg"
        with open(image_filename, 'wb') as new_file:
            new_file.write(downloaded_file)

        bot.reply_to(message, "Enter the text for the center:")
        bot.register_next_step_handler(message, get_above_text, image_filename)
    else:
        bot.reply_to(message, "That's not an image!")


def get_above_text(message, image_filename):
    global center_text
    center_text = message.text
    bot.reply_to(message, "Enter the text for above the center (or leave empty):")
    bot.register_next_step_handler(message, get_below_text, image_filename, center_text)

def get_below_text(message, image_filename, center_text):
    global above_text
    above_text = message.text
    bot.reply_to(message, "Enter the text for below the center (or leave empty):")
    bot.register_next_step_handler(message, process_final_image, image_filename, center_text, above_text)

def process_final_image(message, image_filename, center_text, above_text):
    global below_text
    below_text = message.text
    output_image_path = add_text_to_image(image_filename, center_text, above_text, below_text)

    if output_image_path.startswith("Error"):
        bot.reply_to(message, output_image_path)
    else:
        try:
            with open(output_image_path, 'rb') as f:
                bot.send_photo(message.chat.id, f)
            os.remove(image_filename)
            os.remove(output_image_path)
        except Exception as e:
            bot.reply_to(message, f"Error sending image: {e}")

bot.infinity_polling()
