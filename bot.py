import telebot
from PIL import Image, ImageDraw, ImageFont
import os
import time
import textwrap

BOT_TOKEN = '6590125561:AAFl8DodgcPO_3Z5oyUkU-B6zlYc1Aumgrk' # Replace with your actual bot token
bot = telebot.TeleBot(BOT_TOKEN)

# Default settings
default_font_size_center = 100
default_font_size_above_below = 75
default_font_path = "arial.ttf" # Or path to your preferred font
default_center_color = (0, 255, 255) # Cyan
default_other_color = (255, 255, 255) # White

# User data structure
user_data = {}

# Function to handle font loading errors
def load_font(font_path, size):
    try:
        return ImageFont.truetype(font_path, size)
    except IOError:
        print(f"Could not load font {font_path}. Using default font.")
        return ImageFont.load_default()


def add_text_to_image(image_path, center_text, above_text, below_text, center_size, above_size, below_size, font_path, center_color, other_color):
    try:
        img = Image.open(image_path)
        draw = ImageDraw.Draw(img)
        width, height = img.size

        font_center = load_font(font_path, center_size)
        font_above_below = load_font(font_path, above_size)

        # Dynamic text wrapping based on available width
        max_width = width * 0.8 # Use 80% of image width for text

        center_text = "\n".join(textwrap.wrap(center_text, width=int(max_width / font_center.getsize(" ")[0])))
        above_text = "\n".join(textwrap.wrap(above_text, width=int(max_width / font_above_below.getsize(" ")[0]))) if above_text else ""
        below_text = "\n".join(textwrap.wrap(below_text, width=int(max_width / font_above_below.getsize(" ")[0]))) if below_text else ""

        # Calculate text positions and add text to image
        center_text_size = draw.multiline_textsize(center_text, font=font_center)
        center_x = (width - center_text_size[0]) // 2
        center_y = (height - center_text_size[1]) // 2
        draw.multiline_text((center_x, center_y), center_text, font=font_center, fill=center_color, align="center")

        if above_text:
            above_text_size = draw.multiline_textsize(above_text, font=font_above_below)
            above_x = (width - above_text_size[0]) // 2
            above_y = center_y - center_text_size[1] - 10 # Adjust vertical spacing as needed
            draw.multiline_text((above_x, above_y), above_text, font=font_above_below, fill=other_color, align="center")

        if below_text:
            below_text_size = draw.multiline_textsize(below_text, font=font_above_below)
            below_x = (width - below_text_size[0]) // 2
            below_y = center_y + center_text_size[1] + 10 # Adjust vertical spacing as needed
            draw.multiline_text((below_x, below_y), below_text, font=font_above_below, fill=other_color, align="center")

        timestamp = int(time.time())
        output_filename = f"output_{timestamp}.jpg"
        img.save(output_filename)
        return output_filename
    except Exception as e:
        return f"Error processing image: {str(e)}"


@bot.message_handler(commands=['start'])
def start(message):
    bot.reply_to(message, "Send me an image.")
    bot.register_next_step_handler(message, process_image)


def process_image(message):
    if message.photo:
        file_info = bot.get_file(message.photo[-1].file_id)
        downloaded_file = bot.download_file(file_info.file_path)
        image_filename = "temp_image.jpg"
        with open(image_filename, 'wb') as new_file:
            new_file.write(downloaded_file)

        user_data[message.chat.id] = {
            'center_text': '',
            'above_text': '',
            'below_text': '',
            'center_size': default_font_size_center,
            'above_size': default_font_size_above_below,
            'below_size': default_font_size_above_below,
            'font_path': default_font_path,
            'center_color': default_center_color,
            'other_color': default_other_color,
        }

        bot.reply_to(message, "Enter the text for the center:")
        bot.register_next_step_handler(message, get_above_text)
    else:
        bot.reply_to(message, "That's not an image!")


def get_above_text(message):
    user_data[message.chat.id]['center_text'] = message.text
    bot.reply_to(message, "Enter the text for above the center (or leave empty):")
    bot.register_next_step_handler(message, get_below_text)


def get_below_text(message):
    user_data[message.chat.id]['above_text'] = message.text
    bot.reply_to(message, "Enter the text for below the center (or leave empty):")
    bot.register_next_step_handler(message, generate_image)


def generate_image(message):
    user_data[message.chat.id]['below_text'] = message.text
    chat_id = message.chat.id
    data = user_data.get(chat_id)
    if data:
        image_path = user_data[chat_id]['image'] # Access image path separately
        output_path = add_text_to_image(image_path, **data) # Pass image_path explicitly
        if output_path.startswith("Error"):
            bot.reply_to(message, output_path)
        else:
            try:
                with open(output_path, 'rb') as f:
                    bot.send_photo(chat_id, f)
                os.remove(data['image']) # Clean up temp image files
                os.remove(output_path)
                del user_data[chat_id]
            except Exception as e:
                bot.reply_to(message, f"Error sending image: {str(e)}")
    else:
        bot.reply_to(message, "An error occurred. Please start again.")


bot.infinity_polling()
            
