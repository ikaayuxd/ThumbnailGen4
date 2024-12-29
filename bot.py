import telebot
import os
from PIL import Image, ImageDraw, ImageFont

# Replace '6590125561:AAFcDw2FhMA8FMBDeERyjgYsNWnQqDsuo9U' with your actual bot token
BOT_TOKEN = 'YOUR_BOT_TOKEN'
bot = telebot.TeleBot(BOT_TOKEN)

user_data = {} # Dictionary to store user data

# Default font size and other parameters
DEFAULT_FONT_SIZE = 30
DEFAULT_FONT_PATH = "arial.ttf" # Replace with your font path. Ensure it exists!


def add_text_to_image(image_path, center_text, above_text, below_text, center_size, above_size, below_size):
    try:
        img = Image.open(image_path)
        draw = ImageDraw.Draw(img)
        font = ImageFont.truetype(DEFAULT_FONT_PATH, size=center_size) # Use specified font size

        # Text wrapping function - prevents long text from overflowing the image
        def wrap_text(text, font, max_width):
            words = text.split()
            lines = []
            current_line = ""
            for word in words:
                test_line = current_line + " " + word if current_line else word
                if font.getsize(test_line)[0] <= max_width:
                    current_line = test_line
                else:
                    lines.append(current_line)
                    current_line = word
            lines.append(current_line)
            return "\n".join(lines)


        # Center Text
        center_text = wrap_text(center_text, font, img.width - 50) #added text wrapping
        text_width, text_height = draw.textsize(center_text, font=font)
        text_x = (img.width - text_width) / 2
        text_y = (img.height - text_height) / 2
        draw.text((text_x, text_y), center_text, font=font, fill=(255, 255, 255))

        # Above Text (smaller font size)
        font_above = ImageFont.truetype(DEFAULT_FONT_PATH, size=above_size)
        above_text = wrap_text(above_text, font_above, img.width - 50) #added text wrapping
        text_width, text_height = draw.textsize(above_text, font=font_above)
        text_x = (img.width - text_width) / 2
        text_y = text_y - text_height - 10 #adjust position
        draw.text((text_x, text_y), above_text, font=font_above, fill=(255, 255, 255))


        # Below Text (smaller font size)
        font_below = ImageFont.truetype(DEFAULT_FONT_PATH, size=below_size)
        below_text = wrap_text(below_text, font_below, img.width - 50) #added text wrapping
        text_width, text_height = draw.textsize(below_text, font=font_below)
        text_x = (img.width - text_width) / 2
        text_y = text_y + text_height + 10 #adjust position
        draw.text((text_x, text_y), below_text, font=font_below, fill=(255, 255, 255))

        output_path = "output.jpg" # Define the output image path
        img.save(output_path)
        return output_path

    except FileNotFoundError:
        return "Error: Font file not found. Please ensure arial.ttf exists in the same directory."
    except Exception as e:
        return f"Error processing image: {e}"


def get_image(message):
    if message.photo:
        file_id = message.photo[-1].file_id
        file_info = bot.get_file(file_id)
        downloaded_file = bot.download_file(file_info.file_path)
        image_path = "input.jpg" # Define the image path
        with open(image_path, "wb") as new_file:
            new_file.write(downloaded_file)

        user_data[message.chat.id] = {
            'image': image_path,
            'center_text': "",
            'above_text': "",
            'below_text': "",
            'center_size': DEFAULT_FONT_SIZE,
            'above_size': DEFAULT_FONT_SIZE - 5,
            'below_size': DEFAULT_FONT_SIZE - 5,

        }
        bot.reply_to(message, "Enter the text for the center:")
        bot.register_next_step_handler(message, get_above_text)
    else:
        bot.reply_to(message, "Please send an image.")



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
            del user_data[message.chat.id]


def create_keyboard(chat_id):
    markup = telebot.types.InlineKeyboardMarkup()
    markup.add(
        telebot.types.InlineKeyboardButton("+ Center", callback_data=f"center_plus_{chat_id}"),
        telebot.types.InlineKeyboardButton("- Center", callback_data=f"center_minus_{chat_id}")
    )
    markup.add(
        telebot.types.InlineKeyboardButton("+ Above", callback_data=f"above_plus_{chat_id}"),
        telebot.types.InlineKeyboardButton("- Above", callback_data=f"above_minus_{chat_id}")
    )
    markup.add(
        telebot.types.InlineKeyboardButton("+ Below", callback_data=f"below_plus_{chat_id}"),
        telebot.types.InlineKeyboardButton("- Below", callback_data=f"below_minus_{chat_id}")
    )
    markup.add(telebot.types.InlineKeyboardButton("Generate Image", callback_data=f"generate_{chat_id}"))
    return markup


@bot.callback_query_handler(func=lambda call: True)
def callback_query(call):
    try:
        chat_id_str = call.data.split('_')[-1] #get chat id from callback data

        try:
            chat_id = int(chat_id_str)
        except ValueError:
            bot.answer_callback_query(call.id, text="Invalid chat ID", show_alert=True)
            return

        if chat_id not in user_data:
            bot.answer_callback_query(call.id,
                                      text="Please start by sending an image and entering text.",
                                      show_alert=True)
            return

        data = user_data[chat_id]
        if call.data.startswith("center_plus"):
            data['center_size'] += 2
        elif call.data.startswith("center_minus"):
            data['center_size'] = max(10, data['center_size'] - 2)
        elif call.data.startswith("above_plus"):
            data['above_size'] += 2
        elif call.data.startswith("above_minus"):
            data['above_size'] = max(10, data['above_size'] - 2)
        elif call.data.startswith("below_plus"):
            data['below_size'] += 2
        elif call.data.startswith("below_minus"):
            data['below_size'] = max(10, data['below_size'] - 2)
        elif call.data.startswith("generate"):
            process_final_image(call.message)
            return

        markup = create_keyboard(chat_id)
        bot.edit_message_reply_markup(chat_id=chat_id, message_id=call.message.message_id, reply_markup=markup)
        bot.answer_callback_query(call.id, text=f"Text size adjusted!")

    except Exception as e:
        bot.answer_callback_query(call.id, text=f"An unexpected error occurred: {e}", show_alert=True)


@bot.message_handler(content_types=['photo'])
def handle_photo(message):
    get_image(message)


bot.infinity_polling()
  
