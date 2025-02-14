import telebot
from telebot import types
from PIL import Image, ImageDraw, ImageFont
import os
import time
import textwrap
import logging

# Configure logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(filename)s - %(lineno)d - %(message)s')

BOT_TOKEN = '7011113724:AAGwhzsP2Jhp0jJwe47XC5IkWIw7MnYO5iI' # Replace with your bot token
bot = telebot.TeleBot(BOT_TOKEN)

# Default settings
default_font_size_center = 250
default_font_size_above_below = 250
default_font_path = "arial.ttf" # Or path to your preferred font. MUST exist!
default_center_color = (255, 255, 255) # Cyan
default_other_color = (0, 255, 255) # White
default_stroke_width = 3

# Default positions (fractions of image width and height) - Now fixed
default_center_h_pos = 0.5 # Horizontal position (0-1)
default_center_v_pos = 0.5 # Vertical position (0-1)
default_above_h_pos = 0.5 # Horizontal position (0-1)
default_above_v_pos = 0.3 # Vertical position (0-1)
default_below_h_pos = 0.5 # Horizontal position (0-1)
default_below_v_pos = 0.7 # Vertical position (0-1)

user_states = {} # Properly initialized global dictionary


def load_font(font_path, size):
    try:
        return ImageFont.truetype(font_path, size)
    except IOError:
        logging.error(f"Could not load font {font_path}. Using default font.")
        return ImageFont.load_default()


def add_text_to_image(image_path, center_text, above_text, below_text,
                      center_size=default_font_size_center,
                      above_size=default_font_size_above_below,
                      below_size=default_font_size_above_below,
                      font_path=default_font_path,
                      center_color=default_center_color,
                      other_color=default_other_color,
                      stroke_width=default_stroke_width,
                      center_h_pos=default_center_h_pos,
                      center_v_pos=default_center_v_pos,
                      above_h_pos=default_above_h_pos,
                      above_v_pos=default_above_v_pos,
                      below_h_pos=default_below_h_pos,
                      below_v_pos=default_below_v_pos):
    try:
        img = Image.open(image_path)
        draw = ImageDraw.Draw(img)
        width, height = img.size

        font_center = load_font(font_path, center_size)
        font_above_below = load_font(font_path, above_size)

        max_width = width * 0.8

        center_text = "\n".join(textwrap.wrap(center_text or "", width=int(max_width / (font_center.getsize(" ")[0] or 1))))
        above_text = "\n".join(textwrap.wrap(above_text or "", width=int(max_width / (font_above_below.getsize(" ")[0] or 1))))
        below_text = "\n".join(textwrap.wrap(below_text or "", width=int(max_width / (font_above_below.getsize(" ")[0] or 1))))

        def add_text_with_stroke(text, font, color, x, y, stroke_width):
            if text:
                draw.text((x - stroke_width, y - stroke_width), text, font=font, fill="black")
                draw.text((x + stroke_width, y - stroke_width), text, font=font, fill="black")
                draw.text((x - stroke_width, y + stroke_width), text, font=font, fill="black")
                draw.text((x + stroke_width, y + stroke_width), text, font=font, fill="black")
                draw.text((x, y), text, font=font, fill=color)

        if not center_text and not above_text and not below_text:
            return "Error: No text provided."

        center_text_size = draw.multiline_textsize(center_text, font=font_center)
        center_x = int(width * center_h_pos - center_text_size[0] / 2)
        center_y = int(height * center_v_pos - center_text_size[1] / 2)
        add_text_with_stroke(center_text, font_center, center_color, center_x, center_y, stroke_width)

        if above_text:
            above_text_size = draw.multiline_textsize(above_text, font=font_above_below)
            above_x = int(width * above_h_pos - above_text_size[0] / 2)
            above_y = int(height * above_v_pos - above_text_size[1] / 2)
            add_text_with_stroke(above_text, font_above_below, other_color, above_x, above_y, stroke_width)

        if below_text:
            below_text_size = draw.multiline_textsize(below_text, font=font_above_below)
            below_x = int(width * below_h_pos - below_text_size[0] / 2)
            below_y = int(height * below_v_pos - below_text_size[1] / 2)
            add_text_with_stroke(below_text, font_above_below, other_color, below_x, below_y, stroke_width)

        timestamp = int(time.time())
        output_filename = f"output_{timestamp}.jpg"
        img.save(output_filename)
        return output_filename
    except FileNotFoundError:
        return "Error: Image file not found."
    except IOError as e:
        return f"Error processing image: {e}"
    except Exception as e:
        return f"An unexpected error occurred: {e}"


def initialize_user_state(chat_id, image_filename):
    return {
        'image': image_filename,
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

        user_states[message.chat.id] = initialize_user_state(message.chat.id, image_filename)
        bot.reply_to(message, "Enter the text for the center:")
        bot.register_next_step_handler(message, get_above_text)
    else:
        bot.reply_to(message, "That's not an image!")


def get_above_text(message):
    user_states[message.chat.id]['center_text'] = message.text
    bot.reply_to(message, "Enter the text for above the center (or leave empty):")
    bot.register_next_step_handler(message, get_below_text)


def get_below_text(message):
    user_states[message.chat.id]['above_text'] = message.text
    bot.reply_to(message, "Enter the text for below the center (or leave empty):")
    bot.register_next_step_handler(message, generate_image)


def generate_image(message):
    user_data = user_states[message.chat.id]
    user_data['below_text'] = message.text

    output_path = add_text_to_image(user_data['image'], user_data['center_text'], user_data['above_text'],
                                    user_data['below_text'], user_data['center_size'], user_data['above_size'],
                                    user_data['below_size'], user_data['font_path'], user_data['center_color'],
                                    user_data['other_color'], default_stroke_width,
                                    default_center_h_pos, default_center_v_pos, default_above_h_pos,
                                    default_above_v_pos, default_below_h_pos, default_below_v_pos)

    if output_path.startswith("Error"):
        bot.reply_to(message, output_path)
    else:
        try:
            with open(output_path, 'rb') as f:
                bot.send_photo(message.chat.id, f)
            os.remove(output_path)
            os.remove(user_data['image'])
        except Exception as e:
            bot.reply_to(message, f"Error sending image: {str(e)}")
            logging.exception(f"Error sending image: {e}")


bot.infinity_polling()
