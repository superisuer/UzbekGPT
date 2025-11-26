from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.enums import ChatAction, ChatType
from pyrogram.errors import Forbidden
from pyrogram import Client, filters

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

ollama_client = AsyncClient(host=OLLAMA_HOST)

API_TOKEN = os.getenv("API_TOKEN")
if not API_TOKEN:
    error("API_TOKEN is not set")
    sys.exit(1)

API_ID = os.getenv("API_ID")
if not API_ID:
    error("API_ID is not set")
    sys.exit(1)

API_HASH = os.getenv("API_HASH")
if not API_HASH:
    error("API_HASH is not set")
    sys.exit(1)


app = Client(
    "uzbekgpt",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=API_TOKEN
)

user_contexts = {}

@app.on_message(filters.command("start") & filters.private)
async def start_handler(client: Client, message: Message):
    user_id = message.from_user.id
    user_contexts[user_id] = []

    keyboard = InlineKeyboardMarkup(
        [[InlineKeyboardButton("Начать", callback_data="start")]]
    )

    try:
        await message.reply(
            "Привет, я УЗБекГПТ✅ готов помочь. Что ты хочешь сделать?✅",
            reply_markup=keyboard
        )
    except Forbidden as e:
        print(f"Error in sending message: {e}")
        user_contexts[user_id] = []
    except Exception as e:
        await message.reply("⚠️ узбекгпт не смог ответить вам. мы сбросили ваш контекст.")
        print(f"Error in sending message: {e}")
        user_contexts[user_id] = []

@app.on_callback_query(filters.regex("^start$"))
async def start_callback(client, callback_query): 
    await callback_query.message.edit_text(
        "✅я рад что вас заинтересовать✅✅ а теперь напише любое сообщение и свободный узбек вам ответит✅"
    )
    await callback_query.answer() 


@app.on_message(filters.command("clear") & filters.incoming)
async def clear_handler(client: Client, message: Message):
    user_id = message.from_user.id
    user_contexts[user_id] = []
    try:
        await message.reply("контекст очичен✅")
    except Forbidden as e:
        error(f"Error in sending message: {e}")
        user_contexts[user_id] = []
    except Exception as e:
        await message.reply("⚠️ узбекгпт не смог ответить вам. мы сбросили ваш контекст.")
        error(f"Error in sending message: {e}")
        user_contexts[user_id] = []

@app.on_message(filters.text)
async def text_handler(client, message):
    user_id = message.from_user.id
    if message.chat.type in [ChatType.GROUP, ChatType.SUPERGROUP]:        
        text_lower = (message.text or "").lower()
        is_reply_to_bot = (message.reply_to_message and message.reply_to_message.from_user and message.reply_to_message.from_user.is_bot)
        
        mentions_bot = any(e.type == "mention" for e in (message.entities or []))
        has_uzbek = "узбек" in text_lower
        # print(is_reply_to_bot, mentions_bot, has_uzbek)
        if not (is_reply_to_bot or mentions_bot or has_uzbek):
            return

    prompt = ""

    if message.text:
        prompt = message.text
    elif message.caption:
        prompt = message.caption

    if message.photo:
        photo = message.photo[-1]
    
        path = f"{message.id}.jpg"
        await client.download_media(photo.file_id, file_name=path)
    
        img = Image.open(path)
        img = img.convert("L")
        img = img.point(lambda x: 0 if x < 140 else 255, "1")
    
        config = r"--oem 3 --psm 6"
        text_img = pytesseract.image_to_string(img, lang="rus+eng", config=config)
    
        os.remove(path)
    
        if prompt and text_img:
            prompt = f"{prompt}\n<фото {path}>{text_img}</image>"
        elif text_img:
            prompt = f"<фото {path}>{text_img}/>"
    
    if message.reply_to_message and message.reply_to_message.text:
        replied_text = message.reply_to_message.text
        prompt = f"<цитата>{replied_text}</цитата>{prompt}"
    
    prompt = prompt[:1000]
    
    if user_id not in user_contexts:
        user_contexts[user_id] = []

    user_contexts[user_id].append({"role": "user", "content": prompt})
    user_contexts[user_id] = user_contexts[user_id][-MAX_CONTEXT:]

    try:
        await client.send_chat_action(
            chat_id=message.chat.id,
            action=ChatAction.TYPING
        )
    except Forbidden as e:
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
        ollama_client.chat(
            model=OLLAMA_MODEL,
            messages=messages,
            think=False
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

    user_contexts[user_id].append({"role": "assistant", "content": text})
    user_contexts[user_id] = user_contexts[user_id][-MAX_CONTEXT:]

    try:
        await message.reply(text)
    except Forbidden as e:
        error(f"Error in sending message: {e}")
        user_contexts[user_id] = []
    except Exception as e:
        await message.reply("⚠️ узбекгпт не смог ответить вам. мы сбросили ваш контекст.")
        error(f"Error in sending message: {e}")
        user_contexts[user_id] = []

app.run()
