import telebot
from PIL import Image, ImageDraw, ImageFont # You'll need to install Pillow

# Replace 'YOUR_BOT_TOKEN' with your actual bot token
BOT_TOKEN = 'YOUR_BOT_TOKEN'
bot = telebot.TeleBot(6590125561:AAHbumkUHB5654HOPGGaIzIOn5OyhgiQLV4)

# Placeholder for the image processing function. You'll need to implement this!
def add_text_to_image(image_path, text):
    try:
        img = Image.open(image_path)
        draw = ImageDraw.Draw(img)
        # Add code here to dynamically determine font size and position based on image dimensions
        font = ImageFont.load_default() # Or load a specific font
        draw.text((10, 10), text, font=font, fill="black") # Adjust position as needed
        img.save("output.jpg") # Or save with a more dynamic filename
        return "output.jpg"
    except Exception as e:
        return f"Error processing image: {e}"



@bot.message_handler(commands=['start'])
def start(message):
    bot.reply_to(message, "Hello! Send me the text you want to add to an image.")
    bot.register_next_step_handler(message, get_text)

def get_text(message):
    global user_text
    user_text = message.text
    bot.reply_to(message, "Now send me the image.")
    bot.register_next_step_handler(message, process_image)

def process_image(message):
    if message.photo:
        file_info = bot.get_file(message.photo[-1].file_id) # Get largest photo
        downloaded_file = bot.download_file(file_info.file_path)
        with open("image.jpg", 'wb') as new_file:
            new_file.write(downloaded_file)

        output_image_path = add_text_to_image("image.jpg", user_text)

        if output_image_path.startswith("Error"):
            bot.reply_to(message, output_image_path)
        else:
            try:
                with open(output_image_path, 'rb') as f:
                    bot.send_photo(message.chat.id, f)
            except Exception as e:
                bot.reply_to(message, f"Error sending image: {e}")
    else:
        bot.reply_to(message, "That's not an image!")

bot.infinity_polling()
