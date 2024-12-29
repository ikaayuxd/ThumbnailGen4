import telebot
from PIL import Image, ImageDraw, ImageFont
import os
import time
import textwrap

BOT_TOKEN = '6590125561:AAFcDw2FhMA8FMBDeERyjgYsNWnQqDsuo9U' # Replace with your bot token
bot = telebot.TeleBot(BOT_TOKEN)

# Default settings
default_font_size_center = 80
default_font_size_above_below = 50
default_text_color_center = (255, 0, 0) # Red
default_text_color_above = (0, 0, 255) # Blue
default_text_color_below = (0, 255, 0) # Green
default_wrap_width = 20
min_font_size = 10
max_font_size = 150
min_image_width = 200
min_image_height = 100
above_y_offset = 20
below_y_offset = 20

# User data structure (using chat ID as key)
user_data = {}


def add_text_to_image(image_path, center_text, above_text, below_text, center_size, above_size, below_size,
                      center_color, above_color, below_color):
    try:
        img = Image.open(image_path)
        draw = ImageDraw.Draw(img)
        width, height = img.size

        if width < min_image_width or height < min_image_height:
            return "Image is too small. Please provide a larger image."

        try:
            font_center = ImageFont.truetype("arial.ttf", center_size)
            font_above_below = ImageFont.truetype("arial.ttf", above_size)
        except IOError:
            font_center = ImageFont.load_default()
            font_above_below = ImageFont.load_default()
            print("Default font used.")

        # Wrap text dynamically
        center_text = "\n".join(textwrap.wrap(center_text, width=int(width / center_size)))
        above_text = "\n".join(textwrap.wrap(above_text, width=int(width / above_size))) if above_text else ""
        below_text = "\n".join(textwrap.wrap(below_text, width=int(width / above_size))) if below_text else ""

        # Calculate text positions
        center_text_size = draw.multiline_textsize(center_text, font=font_center)
        center_x = (width - center_text_size[0]) // 2
        center_y = (height - center_text_size[1]) // 2

        draw.multiline_text((center_x, center_y), center_text, font=font_center, fill=center_color, align="center")

        if above_text:
            above_text_size = draw.multiline_textsize(above_text, font=font_above_below)
            above_x = (width - above_text_size[0]) // 2
            above_y = above_y_offset
            draw.multiline_text((above_x, above_y), above_text, font=font_above_below, fill=above_color, align="center")

        if below_text:
            below_text_size = draw.multiline_textsize(below_text, font=font_above_below)
            below_x = (width - below_text_size[0]) // 2
            below_y = height - below_text_size[1] - below_y_offset
            draw.multiline_text((below_x, below_y), below_text, font=font_above_below, fill=below_color, align="center")

        timestamp = int(time.time())
        output_filename = f"output_{timestamp}.jpg"
        img.save(output_filename)
        return output_filename
    except Exception as e:
        return f"Error: {str(e)}"


@bot.message_handler(commands=['start'])
def start_command(message):
    bot.reply_to(message, "Send me an image.")
    bot.register_next_step_handler(message, process_image)


def process_image(message):
    if message.photo:
        file_info = bot.get_file(message.photo[-1].file_id)
        downloaded_file = bot.download_file(file_info.file_path)
        image_filename = "temp_image.jpg"
        with open(image_filename, 'wb') as new_file:
            new_file.write(downloaded_file)

        # Store initial user data (including default values)
        user_data[message.chat.id] = {
            'image': image_filename,
            'center_text': '',
            'above_text': '',
            'below_text': '',
            'center_size': default_font_size_center,
            'above_size': default_font_size_above_below,
            'below_size': default_font_size_above_below,
            'center_color': default_text_color_center,
            'above_color': default_text_color_above,
            'below_color': default_text_color_below,
            'wrap_width': default_wrap_width
        }
        bot.reply_to(message, "Enter the text for the center:")
        bot.register_next_step_handler(message, get_center_text)
    else:
        bot.reply_to(message, "That's not an image!")


def get_center_text(message):
    user_data[message.chat.id]['center_text'] = message.text
    bot.reply_to(message, "Enter the text for above the center (or leave empty):")
    bot.register_next_step_handler(message, get_above_text)


def get_above_text(message):
    user_data[message.chat.id]['above_text'] = message.text
    bot.reply_to(message, "Enter the text for below the center (or leave empty):")
    bot.register_next_step_handler(message, generate_image)


def generate_image(message):
    user_data[message.chat.id]['below_text'] = message.text
    send_image_with_keyboard(message)


def send_image_with_keyboard(message):
    chat_id = message.chat.id
    data = user_data.get(chat_id)

    if not data:
        bot.reply_to(message, "An error occurred. Please start again.")
        return


    output_image_path = add_text_to_image(**data)

    if output_image_path.startswith("Error"):
        bot.reply_to(message, output_image_path)
    else:
        try:
            with open(output_image_path, 'rb') as f:
                markup = create_keyboard(chat_id)
                bot.send_photo(chat_id, f, reply_markup=markup)
            os.remove(data['image'])
            os.remove(output_image_path)
            del user_data[chat_id]
        except Exception as e:
            bot.reply_to(message, f"Error sending image: {str(e)}")


def create_keyboard(chat_id):
    markup = telebot.types.InlineKeyboardMarkup()
    markup.row(
        telebot.types.InlineKeyboardButton("+ Center", callback_data=f'{chat_id}:center:plus'),
        telebot.types.InlineKeyboardButton("- Center", callback_data=f'{chat_id}:center:minus')
    )
    markup.row(
        telebot.types.InlineKeyboardButton("+ Above", callback_data=f'{chat_id}:above:plus'),
        telebot.types.InlineKeyboardButton("- Above", callback_data=f'{chat_id}:above:minus')
    )
    markup.row(
        telebot.types.InlineKeyboardButton("+ Below", callback_data=f'{chat_id}:below:plus'),
        telebot.types.InlineKeyboardButton("- Below", callback_data=f'{chat_id}:below:minus')
    )
    markup.row(telebot.types.InlineKeyboardButton("Generate Image", callback_data=f'{chat_id}:generate'))
    return markup


@bot.callback_query_handler(func=lambda call: True)
def handle_callback_query(call):
    try:
        chat_id, text_area, action = call.data.split(':')
        chat_id = int(chat_id)
        data = user_data.get(chat_id)
        if not data:
            bot.answer_callback_query(call.id, text="Session expired. Please start again.", show_alert=True)
            return

        if action == 'plus':
            size_key = f'{text_area}_size'
            data[size_key] = min(max_font_size, data[size_key] + 2)
        elif action == 'minus':
            size_key = f'{text_area}_size'
            data[size_key] = max(min_font_size, data[size_key] - 2)
        elif action == 'generate':
            send_image_with_keyboard(call.message)
            return

        markup = create_keyboard(chat_id)
        bot.edit_message_reply_markup(chat_id=chat_id, message_id=call.message.message_id, reply_markup=markup)
        bot.answer_callback_query(call.id, text=f"Text size adjusted!")

    except Exception as e:
        bot.answer_callback_query(call.id, text=f"An error occurred: {str(e)}", show_alert=True)



bot.infinity_polling()
    
