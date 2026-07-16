# ---------------------------------------------------
# File Name: main.py
# Description: Advanced Pyrogram bot with Smart Cloner & Batch
# ---------------------------------------------------

import time
import random
import string
import asyncio
from pyrogram import filters, Client, raw
from devgagan import app, userrbot
from config import API_ID, API_HASH, FREEMIUM_LIMIT, PREMIUM_LIMIT, OWNER_ID, DEFAULT_SESSION
from devgagan.core.get_func import get_msg
from devgagan.core.func import *
from devgagan.core.mongo import db
from pyrogram.errors import FloodWait, MessageIdInvalid
from datetime import datetime, timedelta
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from devgagan.modules.shrink import is_user_verified

from devgagan.core.mongo.db import set_clone_state, get_clone_state, remove_clone_state

users_loop = {}
interval_set = {}
batch_mode = {}
active_clones = {}

async def check_interval(user_id, freecheck):
    if freecheck != 1 or await is_user_verified(user_id): return True, None
    now = datetime.now()
    if user_id in interval_set:
        cooldown_end = interval_set[user_id]
        if now < cooldown_end:
            return False, f"Please wait {(cooldown_end - now).seconds} seconds before sending another link."
        else: del interval_set[user_id]
    return True, None

async def set_interval(user_id, interval_minutes=45):
    interval_set[user_id] = datetime.now() + timedelta(seconds=interval_minutes)

async def initialize_userbot(user_id):
    data = await db.get_data(user_id)
    if data and data.get("session"):
        try:
            userbot = Client("userbot", api_id=API_ID, api_hash=API_HASH, device_model='iPhone 16 Pro', session_string=data.get("session"))
            await userbot.start()
            return userbot
        except: return None
    return userrbot if DEFAULT_SESSION else None

# ----------------- SMART LINK PARSER -----------------
def parse_global_link(link: str) -> tuple:
    link = link.split("?")[0].rstrip("/")
    parts = link.split("/")
    try:
        if "t.me/c/" in link:
            chat_id = int("-100" + parts[4])
            msg_id = int(parts[-1]) # Hamesha aakhri number lega (Topic ID bypass)
            return chat_id, msg_id
        elif "t.me/" in link:
            chat_username = parts[3]
            msg_id = int(parts[-1]) # Hamesha aakhri number lega
            return chat_username, msg_id
    except: pass
    raise ValueError("Invalid format")

def generate_msg_link(chat_id, chat_username, msg_id):
    return f"https://t.me/{chat_username}/{msg_id}" if chat_username else f"https://t.me/c/{str(chat_id).replace('-100', '')}/{msg_id}"

async def process_and_upload_link(userbot, user_id, msg_id, link, retry_count, message):
    try:
        await get_msg(userbot, user_id, msg_id, link, retry_count, message)
        try: await app.delete_messages(user_id, msg_id)
        except: pass
        await asyncio.sleep(2.5) # Anti-flood delay
    finally: pass

# ----------------- SINGLE LINK HANDLER -----------------
@app.on_message(filters.regex(r'https?://(?:www\.)?t\.me/[^\s]+|tg://openmessage\?user_id=\w+&message_id=\d+') & filters.private & ~filters.command(["clone", "batch", "cancel", "settings"]))
async def single_link(_, message):
    user_id = message.chat.id
    if await subscribe(_, message) == 1 or user_id in batch_mode: return
    if users_loop.get(user_id, False): return await message.reply("⚠️ You already have an ongoing process.")
    
    can_proceed, response_message = await check_interval(user_id, await chk_user(message, user_id))
    if not can_proceed: return await message.reply(response_message)

    users_loop[user_id] = True
    link = message.text if "tg://openmessage" in message.text else get_link(message.text)
    msg = await message.reply("🔄 **Processing Single Link...**")
    userbot = await initialize_userbot(user_id)
    
    try:
        await process_and_upload_link(userbot, user_id, msg.id, link, 0, message)
        await set_interval(user_id, interval_minutes=45)
    except FloodWait as fw: await msg.edit_text(f'Try again after {fw.value} seconds.')
    except Exception as e: await msg.edit_text(f"Link: `{link}`\n\n**Error:** {str(e)}")
    finally:
        users_loop[user_id] = False
        try: await msg.delete()
        except: pass

# ----------------- CANCEL COMMAND -----------------
@app.on_message(filters.command("cancel"))
async def stop_tasks(_, message):
    user_id = message.chat.id
    if users_loop.get(user_id) or active_clones.get(user_id):
        users_loop[user_id] = False  
        active_clones[user_id] = False 
        await app.send_message(user_id, "✅ **Task has been stopped successfully.**")
    else: await app.send_message(user_id, "⚠️ **No active task is running.**")

# ----------------- SMART CLONER ENGINE -----------------
@app.on_message(filters.command("clone") & filters.private)
async def clone_command_handler(_, message):
    user_id = message.chat.id
    if active_clones.get(user_id, False) or users_loop.get(user_id, False):
        return await message.reply("⚠️ Aapka ek task pehle se chal raha hai.")

    if len(message.command) < 2: return await message.reply("📝 **Usage:** `/clone <message_link>`")

    url = message.command[1]
    status_msg = await message.reply("🔍 **Source Analyze ho raha hai...**")
    
    try: chat_peer, start_msg_id = parse_global_link(url)
    except: return await status_msg.edit_text("❌ Galat link format!")

    userbot = await initialize_userbot(user_id)
    if not userbot: return await status_msg.edit_text("❌ Pehle /login karein.")

    try:
        source_chat = await userbot.get_chat(chat_peer)
        chat_id, chat_title = source_chat.id, source_chat.title or "Chat"
        chat_username = getattr(source_chat, "username", None)
        
        active_clones[user_id] = True
        end_id = start_msg_id
        async for last_msg in userbot.get_chat_history(chat_id, limit=1):
            end_id = last_msg.id
            break
            
        await status_msg.delete()
        asyncio.create_task(run_global_clone(user_id, userbot, chat_id, chat_username, chat_title, start_msg_id, end_id, message))
        
    except Exception as e:
        await status_msg.edit_text(f"❌ Error: {str(e)}")
        try: await userbot.stop()
        except: pass

async def safe_edit(msg_obj, text, **kwargs):
    if not msg_obj: return None
    try:
        await msg_obj.edit_text(text, **kwargs)
        return msg_obj
    except MessageIdInvalid: return None  
    except FloodWait as fw:
        await asyncio.sleep(fw.value + random.randint(2, 5))
        return await safe_edit(msg_obj, text, **kwargs)
    except: return msg_obj

async def run_global_clone(user_id, userbot, chat_id, chat_username, chat_title, start_id, end_id, message_obj):
    try:
        pin_log = await app.send_message(user_id, f"📌 **Smart Clone Started**\nChat: `{chat_title}`\n🔄 Range: `{start_id} - {end_id}`")
        count, CHUNK = 0, 20
        
        for current in range(start_id, end_id + 1, CHUNK):
            if not active_clones.get(user_id, False): return
            limit_end = min(current + CHUNK, end_id + 1)
            
            try:
                messages = await userbot.get_messages(chat_id, list(range(current, limit_end)))
                for msg in messages:
                    if not active_clones.get(user_id, False): return
                    if not msg or msg.empty or (not getattr(msg, 'media', None) and not msg.text): continue
                    
                    temp_msg = await app.send_message(user_id, "⏳ Fetching File...")
                    await get_msg(userbot, user_id, temp_msg.id, generate_msg_link(chat_id, chat_username, msg.id), 0, message_obj)
                    
                    count += 1
                    await asyncio.sleep(random.uniform(1.5, 3.2)) 
                    
                pin_log = await safe_edit(pin_log, f"🚀 **Extraction Progress**\n📦 Files Downloaded: `{count}`\n📍 Current ID: `{limit_end - 1}`")
                await asyncio.sleep(random.randint(6, 12)) 
            except FloodWait as fw: await asyncio.sleep(fw.value + 5)
            except: pass
            
        await safe_edit(pin_log, "✅ **All Extraction Finished!**")
        await app.send_message(user_id, f"🏆 **Master Clone Complete!**\n🎉 Total `{count}` items extracted successfully.")
    finally:
        active_clones[user_id] = False
        try: await userbot.stop()
        except: pass
