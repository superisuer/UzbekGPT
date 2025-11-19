from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.exceptions import TelegramForbiddenError
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from PIL import Image, ImageFilter, ImageOps
from ollama import AsyncClient

from config import SYSTEM_PROMPT, MAX_CONTEXT, OLLAMA_HOST, OLLAMA_MODEL
from logs import info, warn, error
from dotenv import load_dotenv

import pytesseract
import asyncio
import sys
import os
import re

load_dotenv()

client = AsyncClient(host=OLLAMA_HOST)

API_TOKEN = os.getenv("API_TOKEN")
if not API_TOKEN:
    error("API_TOKEN is not set")
    sys.exit(1)

bot = Bot(token=API_TOKEN)
dp = Dispatcher()

user_contexts = {}

def escape_markdown_v2(text):
    return re.sub(r'([_\[\]()~>#+\-=|{}.!])', r'\\\1', text)

@dp.message(Command("/start"))
async def start_handler(message: types.Message):
    user_id = message.from_user.id
    user_contexts[user_id] = []
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="Начать", callback_data="start")]]
    )
    try:
        await message.answer("Привет, я УЗБекГПТ✅ готов помочь. Что ты хочешь сделать?✅", reply_markup=keyboard)
    except TelegramForbiddenError as e:
        error(f"Error in sending message: {e}")
        user_contexts[user_id] = []
    except Exception as e:
        await message.reply("⚠️ узбекгпт не смог ответить вам. мы сбросили ваш контекст.")
        error(f"Error in sending message: {e}")
        user_contexts[user_id] = []

@dp.message(Command("/clear"))
async def start_handler(message: types.Message):
    user_id = message.from_user.id
    user_contexts[user_id] = []
    try:
        await message.reply("контекст очичен✅")
    except TelegramForbiddenError as e:
        error(f"Error in sending message: {e}")
        user_contexts[user_id] = []
    except Exception as e:
        await message.reply("⚠️ узбекгпт не смог ответить вам. мы сбросили ваш контекст.")
        error(f"Error in sending message: {e}")
        user_contexts[user_id] = []

@dp.message()
async def start_handler(message: types.Message):
    user_id = message.from_user.id
    prompt = ""

    if message.text:
        prompt = message.text
    elif message.caption:
        prompt = message.caption

    if message.photo:
        photo = message.photo[-1]
        file = await message.bot.get_file(photo.file_id)
        path = f"{message.message_id}.jpg"
        await message.bot.download_file(file.file_path, path)

        img = Image.open(path)

        img = img.convert("L")
        img = img.point(lambda x: 0 if x < 140 else 255, "1")
        config = r"--oem 3 --psm 6"
        text_img = pytesseract.image_to_string(img, lang="rus+eng", config=config)

        os.remove(path)


        if prompt and text_img:
            prompt = f"{prompt}\n<фото {path}>{text_img}</image>"
        elif text_img:
            prompt = f"<фото{path}>{text_img}/>"

    prompt = prompt[:1000]
    
    if user_id not in user_contexts:
        user_contexts[user_id] = []

    user_contexts[user_id].append({"role": "user", "content": prompt})
    user_contexts[user_id] = user_contexts[user_id][-MAX_CONTEXT:]

    try:
        await message.bot.send_chat_action(message.chat.id, "typing")
    except TelegramForbiddenError as e:
        error(f"Error in sending chat action: {e}")
        user_contexts[user_id] = []
        return
    except Exception as e:
        await message.reply("⚠️ узбекгпт не смог ответить вам. мы сбросили ваш контекст.")
        error(f"Error in sending chat action: {e}")
        user_contexts[user_id] = []
        return

    messages = [{"role": "system", "content": SYSTEM_PROMPT}] + user_contexts[user_id]

    task = asyncio.create_task(
        client.chat(
            model=OLLAMA_MODEL,
            messages=messages
        )
    )

    try:
        response = await asyncio.wait_for(task, timeout=50)

    except asyncio.TimeoutError:
        task.cancel()
        warn("The AI was unable to respond for more than 50 seconds")
        await message.reply("⚠️отказ! наш узбек заснул на клавиатуре и не отвечал вам более 50 сек! чтобы очистить контекст и сменить узбека напиши /clear ✅")
        return

    except Exception as e:
        task.cancel()
        error(f"Ollama Error: {e}")
        await message.reply("⚠️отказ! произошла ошибка при выполнении! контекст очищен ✅")
        user_contexts[user_id] = []
        return


    text = getattr(response.message, "content", None) or getattr(response, "content", "")

    result = escape_markdown_v2(text)

    user_contexts[user_id].append({"role": "assistant", "content": text})
    user_contexts[user_id] = user_contexts[user_id][-MAX_CONTEXT:]

    try:
        await message.reply(result, parse_mode="MarkdownV2")
    except TelegramForbiddenError as e:
        error(f"Error in sending message: {e}")
        user_contexts[user_id] = []
    except Exception as e:
        await message.reply("⚠️ узбекгпт не смог ответить вам. мы сбросили ваш контекст.")
        error(f"Error in sending message: {e}")
        user_contexts[user_id] = []

@dp.callback_query(lambda c: c.data == "start")
async def start_msg(call: types.CallbackQuery):    
    await call.reply()
    await call.message.reply("я рад чтоб ваш заинтересовать✅ теперь напишите мне любое сообщение и я отвечу очень быстро!!✅✅✅")
    await call.message.delete()  

async def main():
    info("Starting bot...")
    await dp.start_polling(bot)

asyncio.run(main())
