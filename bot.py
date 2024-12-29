import telebot
from PIL import Image, ImageDraw, ImageFont
import os
import time
import textwrap

BOT_TOKEN = '6590125561:AAH1OrC59xKzrSxm3gEkCbP_5LSGD7hcag4' # Replace with your bot token
bot = telebot.TeleBot(BOT_TOKEN)

# Significantly increased default font sizes
default_font_size_center = 80 # Increased
default_font_size_above_below = 50 # Increased
center_text_size = default_font_size_center
above_text_size = default_font_size_above_below
below_text_size = default_font_size_above_below

user_data = {}

def add_text_to_image(image_path, center_text, above_text, below_text, center_size, above_size, below_size):
    try:
        img = Image.open(image_path)
        draw = ImageDraw.Draw(img)
        width, height = img.size

        # Check for minimum image dimensions
        if width < 200 or height < 100:
            return "Image is too small. Please provide a larger image."

        try:
            font_center = ImageFont.truetype("arial.ttf", center_size)
            font_above_below = ImageFont.truetype("arial.ttf", above_size)
        except IOError:
            font_center = ImageFont.load_default()
            font_above_below = ImageFont.load_default()
            print("Default font used.")

        # Adjust text wrapping for better fit
        center_text = "\n".join(textwrap.wrap(center_text, width=int(width/center_size)))
        above_text = "\n".join(textwrap.wrap(above_text, width=int(width/above_size))) if above_text else ""
        below_text = "\n".join(textwrap.wrap(below_text, width=int(width/above_size))) if below_text else ""


        # Center text
        center_text_size = draw.multiline_textsize(center_text, font=font_center)
        center_x = (width - center_text_size[0]) // 2
        center_y = (height - center_text_size[1]) // 2
        draw.multiline_text((center_x, center_y), center_text, font=font_center, fill=(255, 0, 0), align="center")

        # Adjust vertical positioning to be closer to edges
        above_y_offset = 20 # Adjust as needed
        below_y_offset = 20 # Adjust as needed

        # Above text
        if above_text:
            above_text_size = draw.multiline_textsize(above_text, font=font_above_below)
            above_x = (width - above_text_size[0]) // 2
            above_y = above_y_offset
            draw.multiline_text((above_x, above_y), above_text, font=font_above_below, fill=(0, 0, 255), align="center")

        # Below text
        if below_text:
            below_text_size = draw.multiline_textsize(below_text, font=font_above_below)
            below_x = (width - below_text_size[0]) // 2
            below_y = height - below_text_size[1] - below_y_offset
            draw.multiline_text((below_x, below_y), below_text, font=font_above_below, fill=(0, 255, 0), align="center")

        timestamp = int(time.time())
        output_filename = f"output_{timestamp}.jpg"
        img.save(output_filename)
        return output_filename
    except Exception as e:
        return f"Error processing image: {str(e)}" # More informative error message


# ... (The rest of the code up to `create_keyboard` remains almost the same, except for the initial values)
# The only significant change is handling the 'generate' button callback. The rest remains the same.



@bot.callback_query_handler(func=lambda call: True)
def callback_query(call):
    try:
        chat_id = call.message.chat.id
        if chat_id not in user_data:
            bot.answer_callback_query(call.id, text="Please send an image and enter text first.", show_alert=True)
            return

        data = user_data[chat_id]
        if call.data.endswith("plus") or call.data.endswith("minus"):
            text_area = call.data[:-5] if call.data.endswith("plus") else call.data[:-6]
            if text_area == "center":
                data['center_size'] += 2 if call.data.endswith("plus") else -2
            elif text_area == "above":
                data['above_size'] += 2 if call.data.endswith("plus") else -2
            elif text_area == "below":
                data['below_size'] += 2 if call.data.endswith("plus") else -2
            data['center_size'] = max(10, min(150, data['center_size'])) #Keep size within bounds
            data['above_size'] = max(10, min(150, data['above_size']))
            data['below_size'] = max(10, min(150, data['below_size']))
            # Update user_data with the adjusted sizes


        elif call.data == "generate":
            output_image_path = add_text_to_image(data['image'], data['center_text'], data['above_text'],
                                              data['below_text'], data['center_size'], data['above_size'], data['below_size'])
            if output_image_path.startswith("Error"):
                bot.answer_callback_query(call.id, text=output_image_path, show_alert=True)
            else:
                with open(output_image_path, 'rb') as f:
                    bot.send_photo(chat_id, f)
                os.remove(data['image'])
                os.remove(output_image_path)
                del user_data[chat_id]
                return #Exit after generating the image

        markup = create_keyboard(chat_id)
        bot.edit_message_reply_markup(chat_id=chat_id, message_id=call.message.message_id, reply_markup=markup)
        bot.answer_callback_query(call.id, text=f"Text size adjusted!")

    except Exception as e:
        bot.answer_callback_query(call.id, text=f"An unexpected error occurred: {str(e)}", show_alert=True)


bot.infinity_polling()
        
