from pyrogram.enums import ChatAction, ChatType
from pyrogram.errors import Forbidden
from pyrogram import Client, filters
from pyrogram.types import (
    InlineQueryResultArticle,
    InputTextMessageContent,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    Message
)

from ollama import AsyncClient

from config import SYSTEM_PROMPT, MAX_CONTEXT, MAX_PROMPT, OLLAMA_HOST, OLLAMA_MODEL
from logs import info, warn, error
from dotenv import load_dotenv

import asyncio
import sys
import os
import re

load_dotenv()

ollama_client = AsyncClient(host=OLLAMA_HOST)

API_TOKEN = os.getenv("API_TOKEN")
API_ID = os.getenv("API_ID")
API_HASH = os.getenv("API_HASH")

if not API_TOKEN:
    error("API_TOKEN не установлен. Создайте бота в @BotFather и установите токен бота.")
    sys.exit(1)

if not API_ID:
    error("API_ID не установлен. Посети https://my.telegram.org/, чтобы получить его.")
    sys.exit(1)
    
if not API_HASH:
    error("API_HASH не установлен. Посети https://my.telegram.org/, чтобы получить его.")
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
    if message.sender_chat:
        user_id = message.sender_chat.id
    else:
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
        error(e)
        user_contexts[user_id] = []
    except Exception as e:
        await message.reply("⚠️ узбекгпт не смог ответить вам. ")
        error(e)
        user_contexts[user_id] = []

@app.on_callback_query(filters.regex("^start$"))
async def start_callback(client, callback_query): 
    await callback_query.message.edit_text(
        "✅я рад что вас заинтересовать✅✅ а теперь напише любое сообщение и свободный узбек вам ответит✅"
    )
    await callback_query.answer() 


@app.on_message(filters.command("clear") & filters.incoming)
async def clear_handler(client: Client, message: Message):
    if message.sender_chat:
        user_id = message.sender_chat.id
    else:
        user_id = message.from_user.id    
    user_contexts[user_id] = []
    try:
        await message.reply("контекст очичен✅")
    except Forbidden as e:
        error(e)
        user_contexts[user_id] = []
    except Exception as e:
        await message.reply("⚠️ узбекгпт не смог ответить вам. ")
        error(e)
        user_contexts[user_id] = []

@app.on_message(filters.text)
async def text_handler(client, message):
    if message.sender_chat:
        user_id = message.sender_chat.id
    else:
        user_id = message.from_user.id
    if message.chat.type in [ChatType.GROUP, ChatType.SUPERGROUP]:        
        me = await client.get_me()
        is_reply_to_bot = (message.reply_to_message and message.reply_to_message.from_user and message.reply_to_message.from_user.is_bot)
        mentions_bot = me.username in message.text
        has_uzbek = "узбек" in message.text.lower()
        if not (is_reply_to_bot or mentions_bot or has_uzbek):
            return

    prompt = message.text

    if message.reply_to_message and message.reply_to_message.text:
        replied_text = message.reply_to_message.text
        prompt = f"<цитата>{replied_text}</цитата>{prompt}"
    
    prompt = prompt[:MAX_PROMPT]
    
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
        error(e)
        user_contexts[user_id] = []
        return
    except Exception as e:
        await message.reply("⚠️ узбекгпт не смог ответить вам. мы сбросили ваш контекст.")
        error(e)
        user_contexts[user_id] = []
        return

    messages = [{"role": "system", "content": SYSTEM_PROMPT}] + user_contexts[user_id]

    task = asyncio.create_task(
        ollama_client.chat(
            model=OLLAMA_MODEL,
            messages=messages
        )
    )

    try:
	    response = await asyncio.wait_for(task, timeout=50)
    except asyncio.TimeoutError:
	    task.cancel()
	    warn("ЛЛМка не смогла ответить больше 50 секунд!!1!1")
	    await message.reply("⚠️к сожалению узбекгпт не придумал ответ за 50 секунд. отправьте сообщение ещё раз или очистите контекст командой /clear")
	    return
    except Exception as e:
	    task.cancel()
	    error(e)
	    await message.reply("⚠️отказ! произошла ошибка при выполнении! контекст очищен")
	    user_contexts[user_id] = []
	    return
    
    text=response['message']['content']
	
    user_contexts[user_id].append({"role": "assistant", "content": text})
    user_contexts[user_id] = user_contexts[user_id][-MAX_CONTEXT:]
    
    try:
	    await message.reply(text)
    except Forbidden as e:
	    error(e)
	    user_contexts[user_id] = []
    except Exception as e:
	    await message.reply("⚠️ узбекгпт не смог ответить вам. мы сбросили ваш контекст.")
	    error(e)
	    user_contexts[user_id] = []

@app.on_inline_query()
async def inline_handler(client, inline_query):
    user_id = inline_query.from_user.id
    prompt = inline_query.query
    
    if user_id not in user_contexts:
        user_contexts[user_id] = []

    user_contexts[user_id].append({"role": "user", "content": prompt})
    user_contexts[user_id] = user_contexts[user_id][-MAX_CONTEXT:]
    messages = [{"role": "system", "content": SYSTEM_PROMPT}] + user_contexts[user_id]

    task = asyncio.create_task(
        ollama_client.chat(
            model=OLLAMA_MODEL,
            messages=messages
        )
    )

    try:
	    response = await asyncio.wait_for(task, timeout=50)
    except asyncio.TimeoutError:
	    task.cancel()
	    warn("ЛЛМка не смогла ответить больше 50 секунд!!1!1")
	    
	    return
    except Exception as e:
	    task.cancel()
	    error(e)
	    user_contexts[user_id] = []
	    return
    
    text=response['message']['content']
    
    result = InlineQueryResultArticle(
        id="1",  
        title="ответ узбекгпт",
        description=text,
        input_message_content=InputTextMessageContent(
            message_text=text
        ),
        
    )
    
    await inline_query.answer(
        results=[result],
        cache_time=300,
        is_personal=True
    )

app.run()
	