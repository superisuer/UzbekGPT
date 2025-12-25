import requests
import asyncio
import shelve
import time
import logs
import os

from dotenv import load_dotenv
from ollama import AsyncClient
from config import *

load_dotenv()

ollama_client = AsyncClient(host=OLLAMA_HOST)
last_command_time = {}
user_contexts = {}

# EBLANGPT СЕКРЕТ КОНФИГ!! -----------------
EBLAN_URL = "https://gpt.twgood.serv00.net"
API_KEY = os.getenv("EBLAN_KEY")
# ------------------------------------------

headers = {
    "Content-Type": "application/json",
    "X-API-Key": API_KEY
}

import random

def galockinator(text):
    for _ in range(random.randint(1,3)):
        if random.random() < 0.3:
            text += "☝️"
        else:
            text += "✅"
    
    return text

def set_user_model(user_id, model_name):
    with shelve.open('models_db') as db:
        db[str(user_id)] = model_name

def get_user_model(user_id):
    with shelve.open('models_db') as db:
        return db.get(str(user_id), DEFAULT_MODEL)

async def generate_without_memory(prompt, user_id):
    messages = [{"role": "system", "content": SYSTEM_PROMPT}] + [{"role": "user", "content": prompt}]

    task = asyncio.create_task(
        ollama_client.chat(
            model=DEFAULT_MODEL,
            messages=messages,
            think=False
        )
    )

    try:
        response = await asyncio.wait_for(task, timeout=30)
    except asyncio.TimeoutError:
        task.cancel()
        warn("ЛЛМка не смогла ответить больше 30 секунд!!1!1")
        return "⚠️узбекгпт не придумал ответ за 30 секунд :("
    except Exception as e:
        task.cancel()
        error(e)
        return "⚠️отказ! произошла ошибка при выполнении! контекст очищен"
	    
    text = response['message']['content']
    
    try:
	    return text
    except Exception as e:
	    return "⚠️ узбекгпт не смог ответить вам. мы сбросили ваш контекст."
	    error(e)

async def generate(prompt, user_id):
    if user_id not in user_contexts:
        user_contexts[user_id] = []
    
    current_time = time.time()
    
    if user_id in last_command_time:
        time_diff = current_time - last_command_time[user_id]
        if time_diff < 3:
            return f"☝️☝️брат не нада так быстро тебе осталось {round(3 - time_diff, 2)} сек"

    last_command_time[user_id] = current_time

    if get_user_model(user_id) in MODELS:
        model = get_user_model(user_id)
    else:
        return f"модель `{get_user_model(user_id)}` теперь не доступна. посмотри доступные модели командой /model"
        
    user_contexts[user_id].append({"role": "user", "content": prompt})
    user_contexts[user_id] = user_contexts[user_id][-MAX_CONTEXT:]

    messages = [{"role": "system", "content": SYSTEM_PROMPT}] + user_contexts[user_id]

    if model != "eblangpt":
        # через ollama запуск ага

        task = asyncio.create_task(
            ollama_client.chat(
                model=model,
                messages=messages,
                think=False
            )
        )

        try:
            response = await asyncio.wait_for(task, timeout=15)
        except Exception as e:
            task.cancel()
            error(e)
            user_contexts[user_id] = []
            return "⚠️произошла ошибка. извините. ты можешь создать новый чат: /clear"
            
        text = response['message']['content']
    else:
        # через специальный секрет апи еблангпт

        loop = asyncio.get_event_loop()

        try:
            response = await loop.run_in_executor(
                None,
                lambda: requests.post(
                    f"{EBLAN_URL}/v1/chat",
                    headers=headers,
                    json={"message": prompt},
                    timeout=5
                )
            )
            
            result = response.json()
            text = galockinator(result["answer"])
        except Exception as e:
            user_contexts[user_id] = []
            return "⚠️ произошла ошибка. извините. ты можешь создать новый чат: /clear"
        
    user_contexts[user_id].append({"role": "assistant", "content": text})
    user_contexts[user_id] = user_contexts[user_id][-MAX_CONTEXT:]
    
    return text