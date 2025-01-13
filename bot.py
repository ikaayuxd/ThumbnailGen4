import telebot
from telebot import types
from moviepy.editor import *
import os

# Configure logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(filename)s - %(lineno)d - %(message)s')

BOT_TOKEN = '7011113724:AAG3-EDmqfhArRgy4OcgFRAfTOX7pPkRPww'  # Replace with your bot token
bot = telebot.TeleBot(BOT_TOKEN)

user_states = {}  # Properly initialized global dictionary


def add_text_to_video(video_path, text):
    # Load the video clip
    video = VideoFileClip(video_path)

    # Define the text clip with desired parameters
    txt_clip = TextClip(text, fontsize=70, color='white', font='Arial', method='caption', align='center')

    # Set the duration of the text clip to match the duration of the video
    txt_clip = txt_clip.set_duration(video.duration)

    # Set the position of the text clip at the bottom center of the video
    txt_clip = txt_clip.set_position(('center', 'bottom'))

    # Overlay the text clip on top of the video
    final_video = CompositeVideoClip([video, txt_clip])

    # Export and save the final video with added text
    output_path = 'output.mp4'
    final_video.write_videofile(output_path, codec='libx264')

    return output_path


@bot.message_handler(commands=['start'])
def start(message):
    bot.reply_to(message, "Send me a video.")
    

@bot.message_handler(content_types=['video'])
def process_video(message):
    file_info = bot.get_file(message.video.file_id)
    downloaded_file = bot.download_file(file_info.file_path)
    
    video_filename = f"temp_video_{message.chat.id}.mp4"
    with open(video_filename, 'wb') as new_file:
        new_file.write(downloaded_file)

    user_states[message.chat.id] = video_filename
    bot.reply_to(message, "Enter the text to add at the bottom of the video:")


@bot.message_handler(func=lambda message: message.chat.id in user_states and message.text)
def generate_video(message):
    chat_id = message.chat.id
    video_path = user_states[chat_id]
    text = message.text

    output_video_path = add_text_to_video(video_path, text)

    if output_video_path.startswith("Error"):
        bot.reply_to(message, output_video_path)
    else:
        try:
            with open(output_video_path, 'rb') as f:
                bot.send_video(chat_id, f)
            os.remove(output_video_path)
            os.remove(video_path)
        except Exception as e:
            bot.reply_to(message, f"Error sending video: {str(e)}")
            logging.exception(f"Error sending video: {e}")


bot.infinity_polling()
