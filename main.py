from pyrogram.enums import ChatAction, ChatType
from pyrogram.errors import Forbidden
from pyrogram import Client, filters
from pyrogram.types import (
    ChosenInlineResult,
    InlineQueryResultArticle,
    InlineQueryResultPhoto,
    InputTextMessageContent,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    Message
)

from ollama import AsyncClient

from config import SYSTEM_PROMPT, MAX_CONTEXT, MAX_PROMPT, OLLAMA_HOST, OLLAMA_MODEL, OLLAMA_MODELS
from logs import info, warn, error
from dotenv import load_dotenv

import asyncio
import shelve
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

def set_user_model(user_id, model_name):
    with shelve.open('models_db') as db:
        db[str(user_id)] = model_name

def get_user_model(user_id):
    with shelve.open('models_db') as db:
        return db.get(str(user_id), OLLAMA_MODEL)

async def generate(prompt, user_id):
    if user_id not in user_contexts:
        user_contexts[user_id] = []
    
    if get_user_model(user_id) in OLLAMA_MODELS:
        model = get_user_model(user_id)
    else:
        return f"модель `{get_user_model(user_id)}` теперь не доступна. посмотри доступные модели командой /model"
        
    # print(user_id)
    
    user_contexts[user_id].append({"role": "user", "content": prompt})
    user_contexts[user_id] = user_contexts[user_id][-MAX_CONTEXT:]

    messages = [{"role": "system", "content": SYSTEM_PROMPT}] + user_contexts[user_id]

    task = asyncio.create_task(
        ollama_client.chat(
            model=model,
            messages=messages
        )
    )

    try:
        response = await asyncio.wait_for(task, timeout=50)
    except asyncio.TimeoutError:
        task.cancel()
        warn("ЛЛМка не смогла ответить больше 50 секунд!!1!1")
        return "⚠️к сожалению узбекгпт не придумал ответ за 50 секунд. отправьте сообщение ещё раз или очистите контекст командой /clear"
    except Exception as e:
        task.cancel()
        error(e)
        user_contexts[user_id] = []
        return "⚠️отказ! произошла ошибка при выполнении! контекст очищен"
	    
	    
    
    text = response['message']['content']
	
    user_contexts[user_id].append({"role": "assistant", "content": text})
    user_contexts[user_id] = user_contexts[user_id][-MAX_CONTEXT:]
    
    try:
	    return text
    except Forbidden as e:
	    error(e)
	    user_contexts[user_id] = []
    except Exception as e:
	    return "⚠️ узбекгпт не смог ответить вам. мы сбросили ваш контекст."
	    error(e)
	    user_contexts[user_id] = []
 
@app.on_message(filters.command("start"))
async def start_handler(client: Client, message: Message):
    if message.chat.type in [ChatType.GROUP, ChatType.SUPERGROUP]:
        return
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


@app.on_message(filters.command("model"))
async def model_handler(client: Client, message: Message):
    if message.sender_chat:
        user_id = message.sender_chat.id
    else:
        user_id = message.from_user.id
    
    user_contexts[user_id] = []
    
    model = get_user_model(user_id)
    args = message.text.split()
    
    if len(args) == 1:
        result = "⚡доступные модели:"
        if len(OLLAMA_MODELS) > 0:
            for i in OLLAMA_MODELS:
                if model == i:
                    result += f"\n✅ `{i}`"
                else:
                    result += f"\n– `{i}`"
        else:
            result += "_хуй тебе_"
    else:
        if args[1] in OLLAMA_MODELS:
            set_user_model(user_id, args[1])
            result = f"✅сменили тебе модель на `{args[1]}`"
        else:
            result = f"🚫`{args[1]}` даже нет в доступных: /model"
            
    try:
        await message.reply(result)
    except Forbidden as e:
        error(e)
        user_contexts[user_id] = []
    except Exception as e:
        await message.reply("⚠️какая-та ошибка случилась")
        error(e)
        user_contexts[user_id] = []

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
        chat_type = message.sender_chat.type
        user_id = message.sender_chat.id
    else:
        chat_type = "gandon"
        user_id = message.from_user.id
    
    if message.chat.type in [ChatType.GROUP, ChatType.SUPERGROUP, ChatType.CHANNEL]:        
        me = await client.get_me()
        is_reply_to_bot = (
            message.reply_to_message 
            and message.reply_to_message.from_user 
            and message.reply_to_message.from_user.is_bot
            and message.reply_to_message.from_user.username == me.username
        )
        mentions_bot = me.username in message.text
        has_uzbek = "узбек" in message.text.lower()
        is_channel = ChatType.CHANNEL == chat_type and message.views
        if not (is_reply_to_bot or mentions_bot or has_uzbek or is_channel):
            return

    replied = message.reply_to_message
    
    prompt = ""
    
    if replied and replied.document:
        file_bytes = await replied.download(in_memory=True)
        file_content = file_bytes.getvalue().decode('utf-8', errors='ignore')
        prompt = f"<файл>{file_content}</файл>{message.text}"
    elif replied and replied.text:
        replied_text = message.reply_to_message.text
        prompt = f"<ответ на>{replied_text}</ответ на>{message.text}"
    else:
        prompt = message.text
        
    prompt = prompt[:MAX_PROMPT]
    
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
        await message.reply("⚠️ узбекгпт не смог ответить вам. он сбросил ваш контекст.")
        error(e)
        user_contexts[user_id] = []
        return
    
    result = await generate(prompt, user_id)
    
    await message.reply(result)
        

@app.on_inline_query()
async def inline_handler(client, inline_query):
    user_id = inline_query.from_user.id
    
    button = InlineKeyboardButton(text="жди", callback_data="pasholnaxxuy")
    
    result = [
        InlineQueryResultArticle(
            title="генерация",
            description="нажми сюда чтоб узбэкгпт начал думат✅",
            input_message_content=InputTextMessageContent(message_text="узбэкгпт думат✅✅"),
            reply_markup=InlineKeyboardMarkup([[button]]),
            id="1"
        )
    ]
    
    await inline_query.answer(
        results=result, cache_time=0
    )

@app.on_chosen_inline_result()
async def chosen_inline_result(client, chosen_result: ChosenInlineResult):
    inline_message_id = chosen_result.inline_message_id
    if inline_message_id:
        result = await generate(chosen_result.query[:MAX_PROMPT], chosen_result.from_user.id)
        await app.edit_inline_text(inline_message_id, result)

@app.on_message(filters.document)
async def handle_content(client, message):
    if message.sender_chat:
        user_id = message.sender_chat.id
    else:
        user_id = message.from_user.id
        
    if message.chat.type in [ChatType.GROUP, ChatType.SUPERGROUP]:        
        me = await client.get_me()
        is_reply_to_bot = (message.reply_to_message and message.reply_to_message.from_user and message.reply_to_message.from_user.is_bot)
        mentions_bot = me.username in message.caption
        has_uzbek = "узбек" in message.caption.lower()
        if not (is_reply_to_bot or mentions_bot or has_uzbek):
            return
        
    prompt = ""
    
    if message.document:
        file_bytes = await message.download(in_memory=True)
        file_content = file_bytes.getvalue().decode('utf-8', errors='ignore')
        prompt = f"<файл>{file_content}</файл>"
            
    if message.caption:        
        prompt = prompt + "\n" + message.caption
    
    result = await generate(prompt, user_id)
    
    await message.reply(result)
    
app.run()
