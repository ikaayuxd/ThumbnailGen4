import telebot
from PIL import Image, ImageDraw, ImageFont
import os
import time
# Replace 'YOUR_BOT_TOKEN' with your actual bot token
BOT_TOKEN = 'YOUR_BOT_TOKEN'
bot = telebot.TeleBot("6590125561:AAHbumkUHB5654HOPGGaIzIOn5OyhgiQLV4")

def add_text_to_image(image_path, text):
    try:
        img = Image.open(image_path)
        draw = ImageDraw.Draw(img)

        # Get image dimensions
        width, height = img.size

        # Simple text positioning (adjust as needed)
        text_x = 10
        text_y = 10

        # Choose a font (you might need to adjust the path)
        try:
            font = ImageFont.truetype("arial.ttf", 30) # Replace 'arial.ttf' with your font if needed.
        except IOError:
            font = ImageFont.load_default()
            print("Default font used.")

        # Wrap text if it's too long for a single line
        wrapped_text = textwrap.fill(text, width=int(width/10)) # Adjust width as needed

        # Draw text (using multiple lines if wrapped)
        draw.text((text_x, text_y), wrapped_text, font=font, fill=(255, 0, 0)) # Red text

        timestamp = int(time.time())
        output_filename = f"output_{timestamp}.jpg"
        img.save(output_filename)
        return output_filename
    except Exception as e:
        return f"Error processing image: {e}"

import textwrap # Added for text wrapping

@bot.message_handler(commands=['start'])
def start(message):
    bot.reply_to(message, "Hello! Send me the text you want to add to an image.")
    bot.register_next_step_handler(message, get_text)

def get_text(message):
    global user_text
    user_text = message.text
    bot.reply_to(message, "Now send me the image.")
    bot.register_next_step_handler(message, process_image)

def process_image(message):
    if message.photo:
        file_info = bot.get_file(message.photo[-1].file_id)
        downloaded_file = bot.download_file(file_info.file_path)
        image_filename = "temp_image.jpg"
        with open(image_filename, 'wb') as new_file:
            new_file.write(downloaded_file)

        output_image_path = add_text_to_image(image_filename, user_text)

        if output_image_path.startswith("Error"):
            bot.reply_to(message, output_image_path)
        else:
            try:
                with open(output_image_path, 'rb') as f:
                    bot.send_photo(message.chat.id, f)
                os.remove(image_filename) #Clean up temp file
                os.remove(output_image_path) #Clean up output file
            except Exception as e:
                bot.reply_to(message, f"Error sending image: {e}")
    else:
        bot.reply_to(message, "That's not an image!")

bot.infinity_polling()

