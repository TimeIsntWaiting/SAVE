# ---------------------------------------------------
# File Name: main.py
# Description: A Pyrogram bot for downloading files from Telegram channels or groups 
#              and uploading them back to Telegram.
# Author: Gagan
# GitHub: https://github.com/devgaganin/
# Telegram: https://t.me/team_spy_pro
# License: MIT License
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

async def generate_random_name(length=8):
    return ''.join(random.choices(string.ascii_lowercase, k=length))

users_loop = {}
interval_set = {}
batch_mode = {}

async def process_and_upload_link(userbot, user_id, msg_id, link, retry_count, message):
    try:
        await get_msg(userbot, user_id, msg_id, link, retry_count, message)
        try: await app.delete_messages(user_id, msg_id)
        except: pass
        await asyncio.sleep(15)
    finally: pass

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

@app.on_message(filters.regex(r'https?://(?:www\.)?t\.me/[^\s]+|tg://openmessage\?user_id=\w+&message_id=\d+') & filters.private & ~filters.command(["clone", "batch", "cancel"]))
async def single_link(_, message):
    user_id = message.chat.id
    if await subscribe(_, message) == 1 or user_id in batch_mode: return
    if users_loop.get(user_id, False): return await message.reply("You already have an ongoing process.")
    if await chk_user(message, user_id) == 1 and FREEMIUM_LIMIT == 0 and user_id not in OWNER_ID and not await is_user_verified(user_id):
        return await message.reply("Freemium service is currently not available.")
        
    can_proceed, response_message = await check_interval(user_id, await chk_user(message, user_id))
    if not can_proceed: return await message.reply(response_message)

    users_loop[user_id] = True
    link = message.text if "tg://openmessage" in message.text else get_link(message.text)
    msg = await message.reply("Processing...")
    userbot = await initialize_userbot(user_id)
    try:
        if await is_normal_tg_link(link):
            await process_and_upload_link(userbot, user_id, msg.id, link, 0, message)
            await set_interval(user_id, interval_minutes=45)
        else: await process_special_links(userbot, user_id, msg, link)
    except FloodWait as fw: await msg.edit_text(f'Try again after {fw.value} seconds.')
    except Exception as e: await msg.edit_text(f"Link: `{link}`\n\n**Error:** {str(e)}")
    finally:
        users_loop[user_id] = False
        try: await msg.delete()
        except: pass

async def initialize_userbot(user_id):
    data = await db.get_data(user_id)
    if data and data.get("session"):
        try:
            userbot = Client("userbot", api_id=API_ID, api_hash=API_HASH, device_model='iPhone 16 Pro', session_string=data.get("session"))
            await userbot.start()
            return userbot
        except: return None
    return userrbot if DEFAULT_SESSION else None

async def is_normal_tg_link(link: str) -> bool:
    return 't.me/' in link and not any(x in link for x in ['t.me/+', 't.me/c/', 't.me/b/', 'tg://openmessage'])
    
async def process_special_links(userbot, user_id, msg, link):
    if not userbot: return await msg.edit_text("Try logging in to the bot and try again.")
    if 't.me/+' in link: return await msg.edit_text(await userbot_join(userbot, link))
    if any(sub in link for sub in ['t.me/c/', 't.me/b/', '/s/', 'tg://openmessage']):
        await process_and_upload_link(userbot, user_id, msg.id, link, 0, msg)
        return await set_interval(user_id, interval_minutes=45)
    await msg.edit_text("Invalid link...")

@app.on_message(filters.command("batch") & filters.private)
async def batch_link(_, message):
    join = await subscribe(_, message)
    if join == 1: return
    user_id = message.chat.id
    if users_loop.get(user_id, False): return await app.send_message(user_id, "You already have a batch process running.")

    freecheck = await chk_user(message, user_id)
    if freecheck == 1 and FREEMIUM_LIMIT == 0 and user_id not in OWNER_ID and not await is_user_verified(user_id):
        return await message.reply("Freemium service is currently not available.")

    max_batch_size = FREEMIUM_LIMIT if freecheck == 1 else PREMIUM_LIMIT

    for attempt in range(3):
        start = await app.ask(user_id, "Please send the start link.\n\n> Maximum tries 3")
        s = start.text.strip().split("/")[-1]
        if s.isdigit():
            cs = int(s)
            start_id = start.text.strip()
            break
        await app.send_message(user_id, "Invalid link. Please send again ...")
    else: return await app.send_message(user_id, "Maximum attempts exceeded.")

    for attempt in range(3):
        num_messages = await app.ask(user_id, f"How many messages do you want to process?\n> Max limit {max_batch_size}")
        try:
            cl = int(num_messages.text.strip())
            if 1 <= cl <= max_batch_size: break
            raise ValueError()
        except: await app.send_message(user_id, f"Invalid number.")
    else: return await app.send_message(user_id, "Maximum attempts exceeded.")

    can_proceed, response_message = await check_interval(user_id, freecheck)
    if not can_proceed: return await message.reply(response_message)
        
    keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("Join Channel", url="https://t.me/team_spy_pro")]])
    pin_msg = await app.send_message(user_id, f"Batch process started ⚡\nProcessing: 0/{cl}", reply_markup=keyboard)
    await pin_msg.pin(both_sides=True)

    users_loop[user_id] = True
    try:
        userbot = await initialize_userbot(user_id)
        for i in range(cs, cs + cl):
            if not users_loop.get(user_id): break
            url = f"{'/'.join(start_id.split('/')[:-1])}/{i}"
            link = get_link(url)
            msg = await app.send_message(user_id, f"Processing...")
            await process_and_upload_link(userbot, user_id, msg.id, link, 0, message)
            await pin_msg.edit_text(f"Batch process started ⚡\nProcessing: {i - cs + 1}/{cl}", reply_markup=keyboard)
        
        await set_interval(user_id, interval_minutes=300)
        await pin_msg.edit_text(f"Batch completed successfully for {cl} messages 🎉", reply_markup=keyboard)
        await app.send_message(user_id, "Batch completed successfully! 🎉")
    except Exception as e: await app.send_message(user_id, f"Error: {e}")
    finally: users_loop.pop(user_id, None)

@app.on_message(filters.command("cancel"))
async def stop_batch(_, message):
    user_id = message.chat.id
    if users_loop.get(user_id) or active_clones.get(user_id):
        users_loop[user_id] = False  
        active_clones[user_id] = False 
        await app.send_message(user_id, "Task has been stopped successfully.")
    else: await app.send_message(user_id, "No active task is running to cancel.")

# -------------------------------------------------------------------------------------------
# 🚀 ADVANCED CLONER (SMART TOPIC EXTRACTOR + CRASH SHIELD)
# -------------------------------------------------------------------------------------------
active_clones = {}

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

# 🔥 FIX: Link parser ab Topic ID directly capture karega
def parse_tg_link(link: str) -> tuple:
    link = link.split("?")[0].rstrip("/")
    parts = link.split("/")
    try:
        if "t.me/c/" in link:
            chat_id = int("-100" + parts[4])
            if len(parts) >= 7: return chat_id, int(parts[-2]), int(parts[-1])
            return chat_id, None, int(parts[-1])
        elif "t.me/" in link:
            chat_username = parts[3]
            if len(parts) >= 6 and parts[-2].isdigit(): return chat_username, int(parts[-2]), int(parts[-1])
            return chat_username, None, int(parts[-1])
    except: pass
    raise ValueError("Invalid format")

def generate_msg_link(chat_id, chat_username, msg_id):
    return f"https://t.me/{chat_username}/{msg_id}" if chat_username else f"https://t.me/c/{str(chat_id).replace('-100', '')}/{msg_id}"

@app.on_message(filters.command("clone") & filters.private)
async def clone_command_handler(_, message):
    user_id = message.chat.id
    if active_clones.get(user_id, False) or users_loop.get(user_id, False):
        return await message.reply("⚠️ Aapka ek task pehle se chal raha hai.")

    saved_state = await get_clone_state(user_id)
    if saved_state:
        buttons = InlineKeyboardMarkup([[InlineKeyboardButton("▶️ Resume Clone", callback_data="resume_clone")], [InlineKeyboardButton("🔄 Start New", callback_data="clear_and_new_clone")], [InlineKeyboardButton("✖️ Cancel Task", callback_data="cancel_clone_task")]])
        return await message.reply(f"⚠️ **Interrupted Task Mila!**\nSource: `{saved_state.get('chat_title')}`\nResume karna hai?", reply_markup=buttons)

    if len(message.command) < 2: return await message.reply("📝 **Usage:** `/clone <message_link>`")

    url = message.command[1]
    status_msg = await message.reply("🔍 **Verify ho raha hai...**")
    
    try: chat_peer, topic_id, start_msg_id = parse_tg_link(url)
    except: return await status_msg.edit_text("❌ Galat link format!")

    userbot = await initialize_userbot(user_id)
    if not userbot: return await status_msg.edit_text("❌ Pehle /login karein.")

    try:
        source_chat = await userbot.get_chat(chat_peer)
        chat_id, chat_title = source_chat.id, source_chat.title or "Chat"
        chat_username = getattr(source_chat, "username", None)
        
        active_clones[user_id] = True
        
        # Agar link me topic ID hai, toh sidha clone start!
        if topic_id:
            await status_msg.edit_text(f"👾 **Forum Topic ID `{topic_id}` detected! Cloning...**")
            asyncio.create_task(run_forum_clone(user_id, userbot, chat_id, chat_username, chat_title, topic_id, message, fresh_start_id=start_msg_id))
        else:
            await status_msg.edit_text("📢 **Normal Chat detected! Scanning...**")
            end_id = start_msg_id
            async for last_msg in userbot.get_chat_history(chat_id, limit=1):
                end_id = last_msg.id
                break
            asyncio.create_task(run_standard_clone(user_id, userbot, chat_id, chat_username, chat_title, start_msg_id, end_id, message))
    except Exception as e:
        await status_msg.edit_text(f"❌ Error: {str(e)}")
        try: await userbot.stop()
        except: pass

@app.on_callback_query(filters.regex(r"^resume_clone|^clear_and_new_clone|^cancel_clone_task"))
async def handle_misc_callbacks(_, query):
    user_id, data = query.from_user.id, query.data
    if data == "cancel_clone_task":
        active_clones[user_id] = False
        await remove_clone_state(user_id)
        return await query.message.edit_text("❌ Task Cancelled.")
    if data == "clear_and_new_clone":
        await remove_clone_state(user_id)
        return await query.message.edit_text("✅ State cleared. Use /clone again.")

    userbot = await initialize_userbot(user_id)
    active_clones[user_id] = True

    if data == "resume_clone":
        state = await get_clone_state(user_id)
        await query.message.delete()
        if state.get("type") == "forum":
            asyncio.create_task(run_forum_clone(user_id, userbot, state["chat_id"], state.get("username"), state["chat_title"], state["topic_id"], query.message, resume_id=state["last_id"]))
        else:
            asyncio.create_task(run_standard_clone(user_id, userbot, state["chat_id"], state.get("username"), state["chat_title"], state["last_id"], state["end_id"], query.message))

async def run_standard_clone(user_id, userbot, chat_id, chat_username, chat_title, start_id, end_id, message_obj):
    try:
        pin_log = await app.send_message(user_id, f"📌 **Task Started**\nChat: `{chat_title}`")
        count, CHUNK = 0, 20
        for current in range(start_id, end_id + 1, CHUNK):
            if not active_clones.get(user_id, False): return
            await set_clone_state(user_id, {"chat_id": chat_id, "username": chat_username, "chat_title": chat_title, "last_id": current, "end_id": end_id, "type": "standard"})
            limit_end = min(current + CHUNK, end_id + 1)
            try:
                for msg in await userbot.get_messages(chat_id, list(range(current, limit_end))):
                    if not active_clones.get(user_id, False): return
                    if not msg or msg.empty or not getattr(msg, 'media', None): continue
                    
                    # 🔥 FIX: Har file ke liye naya dummy message generate ho raha hai
                    temp_msg = await app.send_message(user_id, "⏳ Fetching...")
                    await get_msg(userbot, user_id, temp_msg.id, generate_msg_link(chat_id, chat_username, msg.id), 0, message_obj)
                    
                    count += 1
                    await asyncio.sleep(random.uniform(1.5, 3.2)) 
                    
                pin_log = await safe_edit(pin_log, f"🚀 **Progress:** `{count}` files done.")
                await asyncio.sleep(random.randint(6, 12)) 
            except FloodWait as fw:
                await asyncio.sleep(fw.value + random.randint(5, 10))
            except: pass
            
        await safe_edit(pin_log, f"✅ **Extraction finished!**")
        await app.send_message(user_id, f"✅ **Clone Complete!**\n🎉 Total `{count}` items transferred from `{chat_title}`.")
        await remove_clone_state(user_id)
    finally:
        active_clones[user_id] = False
        try: await userbot.stop()
        except: pass

async def run_forum_clone(user_id, userbot, chat_id, chat_username, chat_title, topic_id, message_obj, fresh_start_id=1, resume_id=None):
    try:
        pin_log = await app.send_message(user_id, f"📌 **Forum Topic Clone Started**\nTopic ID: `{topic_id}`")
        
        target_chat_data = await db.get_data(user_id)
        if target_chat_data and target_chat_data.get("chat_id"):
            try: await app.send_message(target_chat_data["chat_id"], f"━━━━━━━━━━━━━━━━━━━━━\n📁 **TOPIC: {topic_id}**\n━━━━━━━━━━━━━━━━━━━━━")
            except: pass

        current_start = resume_id or fresh_start_id
        topic_count, max_id = 0, current_start
        
        async for thread_msg in userbot.get_chat_history(chat_id, limit=1, message_thread_id=topic_id):
            max_id = thread_msg.id
            break

        CHUNK = 20
        for curr_id in range(current_start, max_id + 1, CHUNK):
            if not active_clones.get(user_id, False): return
            await set_clone_state(user_id, {"chat_id": chat_id, "username": chat_username, "chat_title": chat_title, "topic_id": topic_id, "last_id": curr_id, "type": "forum"})
            try:
                for msg in await userbot.get_messages(chat_id, list(range(curr_id, min(curr_id + CHUNK, max_id + 1)))):
                    if not msg or msg.empty or getattr(msg, 'message_thread_id', None) != topic_id or (not msg.media and not msg.text): continue
                    
                    # 🔥 FIX: Har file ke liye naya dummy message
                    temp_msg = await app.send_message(user_id, "⏳ Fetching...")
                    await get_msg(userbot, user_id, temp_msg.id, generate_msg_link(chat_id, chat_username, msg.id), 0, message_obj)
                    
                    topic_count += 1
                    await asyncio.sleep(random.uniform(1.5, 3.2)) 
                    
                pin_log = await safe_edit(pin_log, f"📁 **Topic Progress**\nThread ID: `{topic_id}`\nItems cloned: `{topic_count}`")
                await asyncio.sleep(random.randint(6, 12)) 
            except FloodWait as fw:
                await asyncio.sleep(fw.value + random.randint(5, 10))
            except: pass

        await safe_edit(pin_log, f"✅ **Topic `{topic_id}` Cloning Finished!**\n🔥 **Total Files:** `{topic_count}`")
        await remove_clone_state(user_id)
    finally:
        active_clones[user_id] = False
        try: await userbot.stop()
        except: pass
