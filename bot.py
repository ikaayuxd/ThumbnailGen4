import telebot
from PIL import Image, ImageDraw, ImageFont
import os
import time
import textwrap

BOT_TOKEN = '6590125561:AAGjbEGFss-Upn1B7BzC1Nimvb_njq-CEKY' # Replace with your actual bot token
bot = telebot.TeleBot(BOT_TOKEN)


# Default settings
default_font_size_center = 100
default_font_size_above_below = 75
default_font_path = "arial.ttf" # Or path to your preferred font
default_center_color = (0, 255, 255) # Cyan
default_other_color = (255, 255, 255) # White
default_stroke_width = 5

# Default positions (fractions of image width and height)
default_center_h_pos = 0.5 # Horizontal position (0-1)
default_center_v_pos = 0.5 # Vertical position (0-1)
default_above_h_pos = 0.5 # Horizontal position (0-1)
default_above_v_pos = 0.3 # Vertical position (0-1)
default_below_h_pos = 0.5 # Horizontal position (0-1)
default_below_v_pos = 0.7 # Vertical position (0-1)


# User data structure
user_data = {}

# Function to handle font loading errors
def load_font(font_path, size):
    try:
        return ImageFont.truetype(font_path, size)
    except IOError:
        print(f"Could not load font {font_path}. Using default font.")
        return ImageFont.load_default()


def add_text_to_image(image_path, center_text, above_text, below_text, center_size, above_size, below_size, font_path, center_color, other_color, stroke_width,
                      center_h_pos, center_v_pos, above_h_pos, above_v_pos, below_h_pos, below_v_pos):
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


        def add_text_with_stroke(text, font, color, x, y, stroke_width):
            draw.text((x - stroke_width, y - stroke_width), text, font=font, fill="black") # Stroke
            draw.text((x + stroke_width, y - stroke_width), text, font=font, fill="black") # Stroke
            draw.text((x - stroke_width, y + stroke_width), text, font=font, fill="black") # Stroke
            draw.text((x + stroke_width, y + stroke_width), text, font=font, fill="black") # Stroke
            draw.text((x, y), text, font=font, fill=color) # Text



        # Calculate text positions
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
    except Exception as e:
        return f"Error processing image: {str(e)}"



# ... (rest of the code remains largely the same, but generate_image needs updating)

def generate_image(message):
    user_data[message.chat.id]['below_text'] = message.text
    chat_id = message.chat.id
    data = user_data.get(chat_id)
    if data:
        image_path = data['image']
        # Pass all the position parameters explicitly:
        output_path = add_text_to_image(image_path, data['center_text'], data['above_text'], data['below_text'], data['center_size'], data['above_size'], data['below_size'], data['font_path'], data['center_color'], data['other_color'], default_stroke_width,
                                        default_center_h_pos, default_center_v_pos, default_above_h_pos, default_above_v_pos, default_below_h_pos, default_below_v_pos)

        if output_path.startswith("Error"):
            bot.reply_to(message, output_path)
        else:
            try:
                with open(output_path, 'rb') as f:
                    bot.send_photo(chat_id, f)
                os.remove(data['image'])
                os.remove(output_path)
                del user_data[chat_id]
            except Exception as e:
                bot.reply_to(message, f"Error sending image: {str(e)}")
    else:
        bot.reply_to(message, "An error occurred. Please start again.")


bot.infinity_polling()

