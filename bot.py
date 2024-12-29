import telebot
from PIL import Image, ImageDraw, ImageFont
import os
import time
import textwrap

BOT_TOKEN = '6590125561:AAFcDw2FhMA8FMBDeERyjgYsNWnQqDsuo9U'
bot = telebot.TeleBot(BOT_TOKEN)


# Default text sizes and font
default_font_size_center = 40
default_font_size_above_below = 30

# Dictionary to store user data (image, texts, sizes, etc.) Using chat ID as key.
user_data = {}

# Function to handle potential errors during font loading
def load_font(font_path, size):
    try:
        return ImageFont.truetype(font_path, size)
    except IOError:
        print(f"Could not load font {font_path}. Using default font.")
        return ImageFont.load_default()


def add_text_to_image(image_path, center_text, above_text, below_text, center_size, above_size, below_size, font_path="arial.ttf"):
    """Adds text to an image and returns the path to the modified image."""
    try:
        img = Image.open(image_path)
        draw = ImageDraw.Draw(img)
        width, height = img.size

        font_center = load_font(font_path, center_size)
        font_above_below = load_font(font_path, above_size)

        # Wrap text to fit image width. Adjust max_width as needed
        max_width = width * 0.8 # Adjust this percentage as needed

        center_text = "\n".join(textwrap.wrap(center_text, width=int(max_width / font_center.getsize(" ")[0])))
        above_text = "\n".join(textwrap.wrap(above_text, width=int(max_width / font_above_below.getsize(" ")[0]))) if above_text else ""
        below_text = "\n".join(textwrap.wrap(below_text, width=int(max_width / font_above_below.getsize(" ")[0]))) if below_text else ""

        # Calculate text positions. Improved centering and spacing.
        center_text_size = draw.multiline_textsize(center_text, font=font_center)
        center_x = (width - center_text_size[0]) // 2
        center_y = (height - center_text_size[1]) // 2

        draw.multiline_text((center_x, center_y), center_text, font=font_center, fill=(255, 0, 0), align="center")

        if above_text:
            above_text_size = draw.multiline_textsize(above_text, font=font_above_below)
            above_x = (width - above_text_size[0]) // 2
            above_y = center_y - center_text_size[1] - 10 # Adjust spacing as needed
            draw.multiline_text((above_x, above_y), above_text, font=font_above_below, fill=(0, 0, 255), align="center")

        if below_text:
            below_text_size = draw.multiline_textsize(below_text, font=font_above_below)
            below_x = (width - below_text_size[0]) // 2
            below_y = center_y + center_text_size[1] + 10 # Adjust spacing as needed
            draw.multiline_text((below_x, below_y), below_text, font=font_above_below, fill=(0, 255, 0), align="center")

        timestamp = int(time.time())
        output_filename = f"output_{timestamp}.jpg"
        img.save(output_filename)
        return output_filename
    except Exception as e:
        return f"Error processing image: {e}"


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
            'image': image_filename,
            'center_text': '',
            'above_text': '',
            'below_text': '',
            'center_size': default_font_size_center,
            'above_size': default_font_size_above_below,
            'below_size': default_font_size_above_below,
            'font_path': "arial.ttf", # Add font path here. Change as needed.
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
    data = user_data[chat_id]
    output_path = add_text_to_image(**data)

    try:
        with open(output_path, 'rb') as f:
            bot.send_photo(chat_id, f)
        os.remove(output_path) # Clean up the temporary image file
        os.remove(data['image']) # Clean up the original image file
        del user_data[chat_id] # Remove user data from the dictionary
    except Exception as e:
        bot.reply_to(message, f"An error occurred: {e}")


bot.infinity_polling()

