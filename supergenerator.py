import requests
import asyncio
import shelve
import random
import time
import json
import os
import re

from logs import *
from openai import AsyncOpenAI
from dotenv import load_dotenv
from ollama import AsyncClient
from config import *

load_dotenv()

last_command_time = {}
user_contexts = {}




# EBLANGPT & ONLYSQ СЕКРЕТ КОНФИГ!! --------
EBLAN_URL = "https://gpt.twgood.serv00.net"
EBLAN_KEY = os.getenv("EBLAN_KEY")
ONLYSQ_KEY = os.getenv("ONLYSQ_KEY")
UZBEKIUM_KEY = os.getenv("UZBEKIUM_KEY")
# ------------------------------------------

EBLAN_HEADERS = {
    "Content-Type": "application/json",
    "X-API-Key": EBLAN_KEY
}

UZBEKIUM_HEADERS = {
    "Authorization": UZBEKIUM_KEY
}

onlysq = AsyncOpenAI(
    base_url="https://api.onlysq.ru/ai/openai",
    api_key=ONLYSQ_KEY,
)

ollama_client = AsyncClient()

def galockinator(text):
    for _ in range(random.randint(1,3)):
        if random.random() < 0.3:
            text += "☝️"
        else:
            text += "✅"
    
    return text

def remove_think_tags(text):
    result = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL)
    return result

def set_user_model(user_id, model_name):
    with shelve.open('models_db') as db:
        db[str(user_id)] = model_name

def get_user_model(user_id):
    with shelve.open('models_db') as db:
        return db.get(str(user_id), DEFAULT_MODEL)

async def generate_without_memory(prompt, user_id):
    messages = [{"role": "system", "content": SYSTEM_PROMPT}] + [{"role": "user", "content": prompt}]

    model = DEFAULT_MODEL

    if model in OLLAMA_MODELS:
        model_provider = "ollama"
    elif model in ONLYSQ_MODELS:
        model_provider = "onlysq"
    elif model in UZBEKIUM_MODELS:
        model_provider = "uzbekium"
    elif model in EBLAN_MODELS:
        model_provider = "eblan"
    else:
        return f"модель `{model}` теперь не достурна"
    
    try:
        if model_provider == "ollama":
            try:
                response = await ollama_client.chat(
                    model=model,
                    messages=messages,
                    think=False
                )
    
            except Exception as e:
                task.cancel()
                error(e)
                user_contexts[user_id] = []
                return f"⚠️ {e}"
    
            text = response['message']['content']
    
        elif model_provider == "eblan":
            loop = asyncio.get_event_loop()
            try:
                response = await loop.run_in_executor(
                    None,
                    lambda: requests.post(
                        f"{EBLAN_URL}/v1/chat",
                        headers=EBLAN_HEADERS,
                        json={"message": prompt},
                        timeout=10
                    )
                )
    
                result = response.json()
                text = galockinator(result["answer"])
            except Exception as e:
                user_contexts[user_id] = []
                error(e)
                return f"⚠️ {e}"
    
        elif model_provider == "onlysq":
            loop = asyncio.get_event_loop()
            try:
                completion = await onlysq.chat.completions.create(
                    model=model,
                    messages=messages
                )
    
                text = completion.choices[0].message.content
            except Exception as e:
                user_contexts[user_id] = []
                error(e)
                return f"⚠️ {e}"
    
        elif model_provider == "uzbekium":
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: requests.post(
                    'https://caliumuzbekium.ddosxd.ru/chat/completions',
                    headers=UZBEKIUM_HEADERS,
                    json = {
                        'model': model,
                        'messages': messages
                    }
                )
            )
    
            text = remove_think_tags(response.json()['reply'])
            
    except Exception as e:
        return f"{e}" 
    return text

async def generate(prompt, user_id):
    if user_id not in user_contexts:
        user_contexts[user_id] = []
    
    current_time = time.time()
    
    if user_id in last_command_time:
        time_diff = current_time - last_command_time[user_id]
        if time_diff < 3:
            return f"☝️☝️брат не нада так быстро тебе осталось {round(3 - time_diff, 2)} сек"

    last_command_time[user_id] = current_time

    model = get_user_model(user_id)

    if model in OLLAMA_MODELS:
        model_provider = "ollama"
    elif model in ONLYSQ_MODELS:
        model_provider = "onlysq"
    elif model in UZBEKIUM_MODELS:
        model_provider = "uzbekium"
    elif model in EBLAN_MODELS:
        model_provider = "eblan"
    else:
        return f"модель `{get_user_model(user_id)}` теперь не доступна. посмотри доступные модели командой /model"
        
    user_contexts[user_id].append({"role": "user", "content": prompt})
    user_contexts[user_id] = user_contexts[user_id][-MAX_CONTEXT:]

    messages = [{"role": "system", "content": SYSTEM_PROMPT}] + user_contexts[user_id]

    if model_provider == "ollama":
        try:
            response = await ollama_client.chat(
                model=model,
                messages=messages,
                think=False
            )

        except Exception as e:
            task.cancel()
            error(e)
            user_contexts[user_id] = []
            return f"⚠️ {e}"
            
        text = response['message']['content']

    elif model_provider == "eblan":
        loop = asyncio.get_event_loop()
        try:
            response = await loop.run_in_executor(
                None,
                lambda: requests.post(
                    f"{EBLAN_URL}/v1/chat",
                    headers=EBLAN_HEADERS,
                    json={"message": prompt},
                    timeout=10
                )
            )
            
            result = response.json()
            text = galockinator(result["answer"])
        except Exception as e:
            user_contexts[user_id] = []
            error(e)
            return f"⚠️ {e}"

    elif model_provider == "onlysq":
        loop = asyncio.get_event_loop()
        try:   
            completion = await onlysq.chat.completions.create(
                model=model,
                messages=messages
            )
            
            text = completion.choices[0].message.content
        except Exception as e:
            user_contexts[user_id] = []
            error(e)
            return f"⚠️ {e}"
            
    elif model_provider == "uzbekium":
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None,
            lambda: requests.post(
                'https://caliumuzbekium.ddosxd.ru/chat/completions', 
                headers=UZBEKIUM_HEADERS,
                json = {
                    'model': model,
                    'messages': messages
                }
            )
        )

        text = remove_think_tags(response.json()['reply'])
        

    user_contexts[user_id].append({"role": "assistant", "content": text})
    user_contexts[user_id] = user_contexts[user_id][-MAX_CONTEXT:]

    return text
