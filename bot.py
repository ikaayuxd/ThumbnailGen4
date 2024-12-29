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

        # Choose a font (handling potential errors)
        try:
            font_center = ImageFont.truetype("arial.ttf", 40)  
            font_above_below = ImageFont.truetype("arial.ttf", 30) 
        except IOError:
            font_center = ImageFont.load_default()
            font_above_below = ImageFont.load_default()
            print("Default font used.")

        # Center text (with word wrapping for long text)
        center_text = "\n".join(textwrap.wrap(center_text, width=30)) # Adjust width as needed
        center_text_size = draw.multiline_textsize(center_text, font=font_center)
        center_x = (width - center_text_size[0]) // 2
        center_y = (height - center_text_size[1]) // 2
        draw.multiline_text((center_x, center_y), center_text, font=font_center, fill=(255, 0, 0), align="center")


        # Text above center (with word wrapping)
        if above_text:
            above_text = "\n".join(textwrap.wrap(above_text, width=30))
            above_text_size = draw.multiline_textsize(above_text, font=font_above_below)
            above_x = (width - above_text_size[0]) // 2
            above_y = center_y - center_text_size[1] - 10 
            draw.multiline_text((above_x, above_y), above_text, font=font_above_below, fill=(0, 0, 255), align="center")

        # Text below center (with word wrapping)
        if below_text:
            below_text = "\n".join(textwrap.wrap(below_text, width=30))
            below_text_size = draw.multiline_textsize(below_text, font=font_above_below)
            below_x = (width - below_text_size[0]) // 2
            below_y = center_y + center_text_size[1] + 10 
            draw.multiline_text((below_x, below_y), below_text, font=font_above_below, fill=(0, 255, 0), align="center")

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
                # Send photo with inline keyboard
                markup = telebot.types.InlineKeyboardMarkup()
                markup.add(telebot.types.InlineKeyboardButton("Button 1", callback_data="button1"),
                           telebot.types.InlineKeyboardButton("Button 2", callback_data="button2"),
                           telebot.types.InlineKeyboardButton("Button 3", callback_data="button3"))
                markup.add(telebot.types.InlineKeyboardButton("Button 4", callback_data="button4"),
                           telebot.types.InlineKeyboardButton("Button 5", callback_data="button5"),
                           telebot.types.InlineKeyboardButton("Button 6", callback_data="button6"))

                bot.send_photo(message.chat.id, f, reply_markup=markup)

            os.remove(image_filename)
            os.remove(output_image_path)
        except Exception as e:
            bot.reply_to(message, f"Error sending image: {e}")

@bot.callback_query_handler(func=lambda call: True)
def callback_query(call):
    # Process button clicks here. Add your button logic.
    bot.answer_callback_query(call.id, f"You pressed {call.data}")


bot.infinity_polling()
                
