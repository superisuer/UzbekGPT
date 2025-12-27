import asyncio
import sys
import os
import re
import io

from typing import Optional, Union
from io import BytesIO

from aiogram import Bot, Dispatcher, F, Router
from aiogram.enums import ChatType, ChatAction
from aiogram.types import (
    Message, CallbackQuery, InlineQuery, 
    ChosenInlineResult, InlineQueryResultArticle,
    InputTextMessageContent, InlineKeyboardMarkup,
    InlineKeyboardButton, User, BufferedInputFile
)
from aiogram.filters import Command
from aiogram.exceptions import TelegramForbiddenError
from aiogram.client.default import DefaultBotProperties

from uzbekimg import unpacker, generate_image

from config import *
from logs import *
from dotenv import load_dotenv

from supergenerator import *

load_dotenv()

unpacker()

API_TOKEN = os.getenv("API_TOKEN")

if not API_TOKEN:
    error("API_TOKEN не установлен. Создайте бота в @BotFather и установите токен бота.")
    sys.exit(1)

bot = Bot(token=API_TOKEN, default=DefaultBotProperties(parse_mode="MarkdownV2"))
dp = Dispatcher()
router = Router()
dp.include_router(router)

me = None

async def get_me() -> User:
    global me
    if me is None:
        me = await bot.get_me()
    return me

@router.message(Command("start"))
async def start_handler(message: Message):
    if message.chat.type in [ChatType.GROUP, ChatType.SUPERGROUP]:
        return
    
    if message.sender_chat:
        user_id = message.sender_chat.id
    else:
        user_id = message.from_user.id
    
    user_contexts[user_id] = []

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="Начать", callback_data="start")]]
    )

    try:
        await message.reply(
            "Привет, я УЗБекГПТ✅ готов помочь. Напиши любае сообщение или отправь файл чтоб я быстра ответил!1!1 Или нажми кнопку ниже чтоба посмотрет мои команды..",
            reply_markup=keyboard
        )
    except TelegramForbiddenError as e:
        error(e)
        user_contexts[user_id] = []
    except Exception as e:
        await message.reply("⚠️ узбекгпт не смог ответить вам. ")
        error(e)
        user_contexts[user_id] = []

@router.callback_query(F.data == "start")
async def start_callback(callback_query: CallbackQuery): 
    await callback_query.message.edit_text(
        "✅я рад что вас заинтересовать✅✅ а теперь напише любое сообщение и свободный узбек вам ответит✅\n\n"
        "`/start` - ага старт\n"
        "`/clear` - новы чат✅\n"
        "`/model` - сменит модэль ллм✅\n"
        "`/image` - генерация хуйни✅✅"
    )
    await callback_query.answer() 

@router.message(Command("model"))
async def model_handler(message: Message):
    if message.sender_chat:
        user_id = message.sender_chat.id
    else:
        user_id = message.from_user.id
    
    user_contexts[user_id] = []
    
    model = get_user_model(user_id)
    args = message.text.split()
    
    MODELS = UZBEKIUM_MODELS + OLLAMA_MODELS + ONLYSQ_MODELS + EBLAN_MODELS

    if len(args) == 1:
        result = "⚡доступные модели:"
        if len(MODELS) > 0:
            result += "\nсекрет:"
            for i in UZBEKIUM_MODELS:
                result += f"\n• `{i}`"
            result += "\nоляма:"
            for i in OLLAMA_MODELS:
                result += f"\n• `{i}`"
            result += "\nтолькоSQ:"
            for i in ONLYSQ_MODELS:
                result += f"\n• `{i}`"
            result += "\nебланГПТ:"
            for i in EBLAN_MODELS:
                result += f"\n• `{i}`"
            result += f"\n\nвыбрано: `{model}`\nчтобы сменить модель отправь боту `/model название модели`"
        else:
            result += "_хуй тебе_"
    else:
        if args[1] in MODELS:
            set_user_model(user_id, args[1])
            result = f"✅сменили тебе модель на `{args[1]}`"
        else:
            result = f"🚫`{args[1]}` даже нет в доступных: /model"
            
    try:
        await message.reply(result, parse_mode="Markdown")
    except TelegramForbiddenError as e:
        error(e)
        user_contexts[user_id] = []
    except Exception as e:
        await message.reply("⚠️какая-та ошибка случилась")
        error(e)
        user_contexts[user_id] = []

@router.message(Command("image"))
async def image_handler(message: Message):
    user_id = message.sender_chat.id if message.sender_chat else message.from_user.id

    current_time = time.time()
    
    if user_id in last_command_time:
        time_diff = current_time - last_command_time[user_id]
        if time_diff < 1:
            await message.answer("☝️☝️брат не так часта")
            return
    
    last_command_time[user_id] = current_time
    img = generate_image("pasholnaxxuy")
    
    if img:
        img_bytes = BytesIO()
        img.save(img_bytes, format='JPEG')
        img_bytes = img_bytes.getvalue()
        photo = BufferedInputFile(img_bytes, filename="image.jpg")
        await message.answer_photo(photo)

@router.message(Command("clear"))
async def clear_handler(message: Message):
    user_id = message.sender_chat.id if message.sender_chat else message.from_user.id
    
    user_contexts[user_id] = []
    try:
        await message.reply("контекст очичен✅")
    except TelegramForbiddenError as e:
        error(e)
        user_contexts[user_id] = []
    except Exception as e:
        await message.reply("⚠️ узбекгпт не смог ответить вам. ")
        error(e)
        user_contexts[user_id] = []

@router.message(F.content_type.in_({'text', 'photo', 'video'}))
async def text_handler(message: Message):
    chat_type = message.sender_chat.type if message.sender_chat else ""
    user_id = message.sender_chat.id if message.sender_chat else message.from_user.id
    # print(message)
    is_channel = ChatType.CHANNEL == chat_type and message.from_user and message.from_user.id == 777000
    user_text = message.text or message.caption or ""

    if message.chat.type in [ChatType.GROUP, ChatType.SUPERGROUP, ChatType.CHANNEL]:        
        if not is_channel:
            me_user = await get_me()
            is_reply_to_bot = (
                message.reply_to_message 
                and message.reply_to_message.from_user 
                and message.reply_to_message.from_user.is_bot
                and message.reply_to_message.from_user.username == me_user.username
            )
            mentions_bot = me_user.username and (me_user.username in (message.text or ""))
            has_uzbek = "узбек" in (message.text or "").lower()
            if not (is_reply_to_bot or mentions_bot or has_uzbek):
                return

    replied = message.reply_to_message
    prompt = ""
    
    if replied and replied.document:
        if replied.document.file_size > 4096:
            await message.reply("слишком много данных не хочу отвечать☝️☝️")
            return

        file_bytes = io.BytesIO()
    
        try:
            await bot.download(
                replied.document,
                destination=file_bytes
            )
            file_bytes.seek(0)
            file_content = file_bytes.read().decode('utf-8', errors='ignore')
                
            prompt = f"<файл>{file_content}</файл>{user_text}"
            
        except UnicodeDecodeError:
            await message.reply("брат что это за каловый файл ты приложил☝️☝️")
            return
            
        except Exception as e:
            error(e)
            await message.reply("ошибка произошла брат братик братишка☝️☝️")
            return
    elif replied and replied.text:
        replied_text = message.reply_to_message.text
        prompt = f"ответ на сообщение: '{replied_text}'\n{user_text}"
    else:
        prompt = user_text
    
    prompt = prompt[:MAX_PROMPT]
    
    try:
        await bot.send_chat_action(chat_id=message.chat.id, action="typing")
    except TelegramForbiddenError as e:
        error(e)
        return

    if is_channel:
        result = await generate_without_memory(prompt, user_id)
    else:
        result = await generate(prompt, user_id)

    def escape_markdown(text: str) -> str:
        escape_chars = r'\[]()>#+-=|{}.!'
        return re.sub(f'([{re.escape(escape_chars)}])', r'\\\1', text)

    try:
        await message.reply(escape_markdown(result), parse_mode="MarkdownV2")
    except Exception as e:
        warn(e)
        await message.reply(result, parse_mode=None)

@router.inline_query()
async def inline_handler(inline_query: InlineQuery):
    user_id = inline_query.from_user.id
    
    button = InlineKeyboardButton(text="жди", callback_data="pasholnaxxuy")
    
    if inline_query.query != "clear":
        result = [
            InlineQueryResultArticle(
                id="1",
                title="генерация",
                description="нажми сюда чтоб узбэкгпт начал думат✅",
                input_message_content=InputTextMessageContent(
                    message_text="узбэкгпт думат✅✅"
                ),
                reply_markup=InlineKeyboardMarkup(
                    inline_keyboard=[[button]]
                )
            )
        ]
    else:
        result = [
            InlineQueryResultArticle(
                id="1",
                title="очистить контекст",
                description="нажми сюда чтоб узбэкгпт прочистил свои мозги✅",
                input_message_content=InputTextMessageContent(
                    message_text="память успех очистка✅✅✅"
                )
            )
        ]
    
    await inline_query.answer(
        results=result, cache_time=0
    )

@router.chosen_inline_result()
async def chosen_inline_result_handler(chosen_result: ChosenInlineResult):
    inline_message_id = chosen_result.inline_message_id
    user_id = chosen_result.from_user.id

    if chosen_result.query != "clear":
        if inline_message_id:
            result = await generate(chosen_result.query[:MAX_PROMPT], chosen_result.from_user.id)
            await bot.edit_message_text(
                text=result,
                inline_message_id=inline_message_id, 
                parse_mode="MarkdownV2"
            )
    else:
        user_contexts[user_id] = []

@router.message(F.content_type == 'document')
async def handle_content(message: Message):
    if message.sender_chat:
        user_id = message.sender_chat.id
    else:
        user_id = message.from_user.id

    if message.chat.type in [ChatType.GROUP, ChatType.SUPERGROUP]:        
        me_user = await bot.get_me()
        is_reply_to_bot = (
            message.reply_to_message 
            and message.reply_to_message.from_user 
            and message.reply_to_message.from_user.is_bot
        )
        mentions_bot = me_user.username and (me_user.username in (message.caption or ""))
        has_uzbek = "узбек" in (message.caption or "").lower()
        if not (is_reply_to_bot or mentions_bot or has_uzbek):
            return
        
    prompt = ""
    
    if message.document:
        if message.document.file_size > 4096:
            await message.reply("слишком много данных не хочу отвечать☝️☝️")
            return
        
        file_bytes = io.BytesIO()
        
        try:
            await bot.download(
                message.document,
                destination=file_bytes
            )

            file_bytes.seek(0)
            file_content = file_bytes.read().decode('utf-8', errors='ignore')
            file_bytes.close()
            
            prompt = f"<файл>{file_content}</файл>"
            
        except UnicodeDecodeError:
            await message.reply("брат что это за каловый файл ты приложил☝️☝️")
            return
            
        except Exception as e:
            error(e)
            await message.reply("ошибка произошла брат братик братишка☝️☝️")
            return
            
    if message.caption:        
        prompt = prompt + "\n" + message.caption
    
    result = await generate(prompt, user_id)
    
    await message.reply(result, parse_mode="Markdown")

async def main():
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
