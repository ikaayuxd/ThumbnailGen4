import telebot
from PIL import Image, ImageDraw, ImageFont
import os
import time
import textwrap

BOT_TOKEN = '6590125561:AAEyNdWy395PfKplBKUidOSHkLglx56NBsI' # Replace with your bot token
bot = telebot.TeleBot(BOT_TOKEN)

# Initial text sizes and font
default_font_size_center = 40
default_font_size_above_below = 30
center_text_size = default_font_size_center
above_text_size = default_font_size_above_below
below_text_size = default_font_size_above_below

# Dictionary to store user data (image, texts, sizes)
user_data = {}


def add_text_to_image(image_path, center_text, above_text, below_text, center_size, above_size, below_size):
    try:
        img = Image.open(image_path)
        draw = ImageDraw.Draw(img)
        width, height = img.size

        try:
            font_center = ImageFont.truetype("arial.ttf", center_size)
            font_above_below = ImageFont.truetype("arial.ttf", above_size) # Smaller for above/below
        except IOError:
            font_center = ImageFont.load_default()
            font_above_below = ImageFont.load_default()
            print("Default font used.")

        # Center text (with word wrapping)
        center_text = "\n".join(textwrap.wrap(center_text, width=30)) # Adjust width as needed
        center_text_size = draw.multiline_textsize(center_text, font=font_center)
        center_x = (width - center_text_size[0]) // 2
        center_y = (height - center_text_size[1]) // 2
        draw.multiline_text((center_x, center_y), center_text, font=font_center, fill=(255, 0, 0), align="center")

        # Above text (with word wrapping)
        if above_text:
            above_text = "\n".join(textwrap.wrap(above_text, width=30))
            above_text_size = draw.multiline_textsize(above_text, font=font_above_below)
            above_x = (width - above_text_size[0]) // 2
            above_y = center_y - center_text_size[1] - 10
            draw.multiline_text((above_x, above_y), above_text, font=font_above_below, fill=(0, 0, 255),
                                align="center")

        # Below text (with word wrapping)
        if below_text:
            below_text = "\n".join(textwrap.wrap(below_text, width=30))
            below_text_size = draw.multiline_textsize(below_text, font=font_above_below)
            below_x = (width - below_text_size[0]) // 2
            below_y = center_y + center_text_size[1] + 10
            draw.multiline_text((below_x, below_y), below_text, font=font_above_below, fill=(0, 255, 0),
                                align="center")

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

        user_data[message.chat.id] = {
            'image': image_filename,
            'center_text': '',
            'above_text': '',
            'below_text': '',
            'center_size': center_text_size,
            'above_size': above_text_size,
            'below_size': below_text_size,
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
    bot.register_next_step_handler(message, process_final_image)


def process_final_image(message):
    user_data[message.chat.id]['below_text'] = message.text
    data = user_data[message.chat.id]
    output_image_path = add_text_to_image(data['image'], data['center_text'], data['above_text'],
                                          data['below_text'], data['center_size'], data['above_size'], data['below_size'])

    if output_image_path.startswith("Error"):
        bot.reply_to(message, output_image_path)
    else:
        try:
            with open(output_image_path, 'rb') as f:
                markup = create_keyboard(message.chat.id)
                bot.send_photo(message.chat.id, f, reply_markup=markup)
            os.remove(data['image'])
            os.remove(output_image_path)
        except Exception as e:
            bot.reply_to(message, f"Error sending image: {e}")
        finally:
            del user_data[message.chat.id] # Remove user data after processing


def create_keyboard(chat_id):
    data = user_data[chat_id]
    markup = telebot.types.InlineKeyboardMarkup()

    markup.add(
        telebot.types.InlineKeyboardButton("+ Center", callback_data=f"center_plus"),
        telebot.types.InlineKeyboardButton("- Center", callback_data=f"center_minus")
    )
    markup.add(
        telebot.types.InlineKeyboardButton("+ Above", callback_data=f"above_plus"),
        telebot.types.InlineKeyboardButton("- Above", callback_data=f"above_minus")
    )
    markup.add(
        telebot.types.InlineKeyboardButton("+ Below", callback_data=f"below_plus"),
        telebot.types.InlineKeyboardButton("- Below", callback_data=f"below_minus")
    )
    markup.add(telebot.types.InlineKeyboardButton("Generate Image", callback_data=f"generate"))
    return markup


@bot.callback_query_handler(func=lambda call: True)
def callback_query(call):
    try:
        chat_id = call.message.chat.id
        data = user_data[chat_id]
        if call.data.endswith("plus"):
            text_area = call.data[:-5]
            if text_area == "center":
                data['center_size'] += 2
            elif text_area == "above":
                data['above_size'] += 2
            elif text_area == "below":
                data['below_size'] += 2
        elif call.data.endswith("minus"):
            text_area = call.data[:-6]
            if text_area == "center":
                data['center_size'] = max(10, data['center_size'] - 2) # prevent size from going too low
            elif text_area == "above":
                data['above_size'] = max(10, data['above_size'] - 2)
            elif text_area == "below":
                data['below_size'] = max(10, data['below_size'] - 2)
        elif call.data == "generate":
            process_final_image(call.message)
            return # prevent further processing

        markup = create_keyboard(chat_id)
        bot.edit_message_reply_markup(chat_id=chat_id, message_id=call.message.message_id, reply_markup=markup)
        bot.answer_callback_query(call.id, text=f"Text size adjusted!")

    except KeyError:
        bot.answer_callback_query(call.id, text="Please start by sending an image and setting the text.",
                                  show_alert=True)
    except Exception as e:
        bot.answer_callback_query(call.id, text=f"An error occurred: {e}", show_alert=True)


bot.infinity_polling()
    
