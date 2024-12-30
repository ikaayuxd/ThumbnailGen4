import telebot
from telebot import types
from PIL import Image, ImageDraw, ImageFont
import os
import time
import textwrap
import logging

# Configure logging to capture errors
logging.basicConfig(level=logging.ERROR, format='%(asctime)s - %(levelname)s - %(message)s')

BOT_TOKEN = '6590125561:AAFcvxs_j1d2w7gy76u1RJC9JY8TwcEK12k' # Replace with your actual bot token
bot = telebot.TeleBot(BOT_TOKEN)

# Default settings (made more robust)
default_font_size_center = 120
default_font_size_above_below = 90
default_font_path = "arial.ttf" # Or path to your preferred font. Consider checking if it exists.
default_center_color = (225, 255, 255) # White
default_other_color = (0, 255, 255) # Cyan
default_stroke_width = 5

# Default positions (fractions of image width and height)
default_center_h_pos = 0.5 # Horizontal position (0-1)
default_center_v_pos = 0.5 # Vertical position (0-1)
default_above_h_pos = 0.5 # Horizontal position (0-1)
default_above_v_pos = 0.3 # Vertical position (0-1)
default_below_h_pos = 0.5 # Horizontal position (0-1)
default_below_v_pos = 0.7 # Vertical position (0-1)
position_step = 0.05

user_states = {} # Dictionary to store user states


def load_font(font_path, size):
    try:
        return ImageFont.truetype(font_path, size)
    except IOError:
        print(f"Could not load font {font_path}. Using default font.")
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

        # Improved text wrapping to handle potential errors better
        center_text = "\n".join(textwrap.wrap(center_text or "", width=int(max_width / (font_center.getsize(" ")[0] or 1))))
        above_text = "\n".join(textwrap.wrap(above_text or "", width=int(max_width / (font_above_below.getsize(" ")[0] or 1))))
        below_text = "\n".join(textwrap.wrap(below_text or "", width=int(max_width / (font_above_below.getsize(" ")[0] or 1))))


        def add_text_with_stroke(text, font, color, x, y, stroke_width):
            if text: # Only add if text exists
                draw.text((x - stroke_width, y - stroke_width), text, font=font, fill="black")
                draw.text((x + stroke_width, y - stroke_width), text, font=font, fill="black")
                draw.text((x - stroke_width, y + stroke_width), text, font=font, fill="black")
                draw.text((x + stroke_width, y + stroke_width), text, font=font, fill="black")
                draw.text((x, y), text, font=font, fill=color)

        # Error handling for empty text
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
        'center_h_pos': default_center_h_pos,
        'center_v_pos': default_center_v_pos,
        'above_h_pos': default_above_h_pos,
        'above_v_pos': default_above_v_pos,
        'below_h_pos': default_below_h_pos,
        'below_v_pos': default_below_v_pos,
        'stage': 'text_input',
        'message_id': None
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
    output_path = add_text_to_image(**user_data) # unpacks the dictionary

    if output_path.startswith("Error"):
        bot.reply_to(message, output_path)
    else:
        try:
            with open(output_path, 'rb') as f:
                sent_message = bot.send_photo(message.chat.id, f, caption="Adjust positions using buttons below.")
                user_data['message_id'] = sent_message.message_id
                user_data['stage'] = 'position_adjustment'
                add_buttons(sent_message)

            # Clean up temporary files only if successful.
            os.remove(user_data['image'])

        except Exception as e:
            bot.reply_to(message, f"Error sending image: {str(e)}")


def add_buttons(message):
    markup = types.InlineKeyboardMarkup()
    button_list = []
    positions = ['center_h', 'center_v', 'above_h', 'above_v', 'below_h', 'below_v']
    directions = ['left', 'right']
    for pos in positions:
        for dir in directions:
            button_list.append(types.InlineKeyboardButton(f"{pos.replace('_', ' ').title()} {dir.title()}",
                                                          callback_data=f"{pos}_{dir}"))

    for i in range(0, len(button_list), 2):
        markup.add(button_list[i], button_list[i + 1] if i + 1 < len(button_list) else None)
    bot.edit_message_reply_markup(chat_id=message.chat.id, message_id=message.message_id, reply_markup=markup)


@bot.callback_query_handler(func=lambda call: True)
def handle_callback_query(call):
    chat_id = call.message.chat.id
    data = call.data
    state = user_states.get(chat_id)
    if state is None:
        bot.answer_callback_query(call.id, "Error: Session expired.", show_alert=True)
        return

    try:
        parts = data.split('_') # Split into multiple parts
        if len(parts) != 2:
            bot.answer_callback_query(call.id, "Error: Invalid callback data.", show_alert=True)
            return
        pos, direction = parts

        # Check if pos is a valid position
        valid_positions = ['center_h', 'center_v', 'above_h', 'above_v', 'below_h', 'below_v']
        if pos not in valid_positions:
            bot.answer_callback_query(call.id, "Error: Invalid position in callback data.", show_alert=True)
            return

        if direction == 'left':
            state[pos] = max(0, state[pos] - position_step)
        elif direction == 'right':
            state[pos] = min(1, state[pos] + position_step)
        else:
            bot.answer_callback_query(call.id, "Error: Invalid direction in callback data.", show_alert=True)
            return

        output_path = add_text_to_image(**state)

        if not output_path.startswith("Error"):
            with open(output_path, 'rb') as f:
                bot.edit_message_media(media=types.InputMediaPhoto(f), chat_id=chat_id, message_id=state['message_id'],
                                       caption="Adjust positions using buttons below.")
                add_buttons(call.message)
            os.remove(output_path) # Remove the temporary file after successful edit.
        else:
            bot.answer_callback_query(call.id, f"Error generating image: {output_path}", show_alert=True)


    except Exception as e:
        logging.exception(f"Error in callback query handler: {e}") # Log the full traceback for debugging
        bot.answer_callback_query(call.id, f"An unexpected error occurred: {str(e)}", show_alert=True)


bot.infinity_polling()
        
