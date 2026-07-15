# ---------------------------------------------------
# File Name: main.py
# Description: A Pyrogram bot for downloading files from Telegram channels or groups 
#              and uploading them back to Telegram.
# Author: Gagan
# GitHub: https://github.com/devgaganin/
# Telegram: https://t.me/team_spy_pro
# YouTube: https://youtube.com/@dev_gagan
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

# For Clone functionality imports
from devgagan.core.mongo.db import set_clone_state, get_clone_state, remove_clone_state

async def generate_random_name(length=8):
    return ''.join(random.choices(string.ascii_lowercase, k=length))

users_loop = {}
interval_set = {}
batch_mode = {}

async def process_and_upload_link(userbot, user_id, msg_id, link, retry_count, message):
    try:
        await get_msg(userbot, user_id, msg_id, link, retry_count, message)
        try:
            await app.delete_messages(user_id, msg_id)
        except Exception:
            pass
        await asyncio.sleep(15)
    finally:
        pass

async def check_interval(user_id, freecheck):
    if freecheck != 1 or await is_user_verified(user_id):
        return True, None

    now = datetime.now()
    if user_id in interval_set:
        cooldown_end = interval_set[user_id]
        if now < cooldown_end:
            remaining_time = (cooldown_end - now).seconds
            return False, f"Please wait {remaining_time} seconds before sending another link."
        else:
            del interval_set[user_id]
    return True, None

async def set_interval(user_id, interval_minutes=45):
    now = datetime.now()
    interval_set[user_id] = now + timedelta(seconds=interval_minutes)

# 🔥 FIX 1: Added ~filters.command to prevent it from hijacking /clone or /batch commands
@app.on_message(filters.regex(r'https?://(?:www\.)?t\.me/[^\s]+|tg://openmessage\?user_id=\w+&message_id=\d+') & filters.private & ~filters.command(["clone", "batch", "cancel"]))
async def single_link(_, message):
    user_id = message.chat.id
    if await subscribe(_, message) == 1 or user_id in batch_mode: return
    if users_loop.get(user_id, False):
        return await message.reply("You already have an ongoing process.")
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
        else:
            await process_special_links(userbot, user_id, msg, link)
    except FloodWait as fw:
        await msg.edit_text(f'Try again after {fw.value} seconds.')
    except Exception as e:
        await msg.edit_text(f"Link: `{link}`\n\n**Error:** {str(e)}")
    finally:
        users_loop[user_id] = False
        try: await msg.delete()
        except: pass

async def initialize_userbot(user_id):
    data = await db.get_data(user_id)
    if data and data.get("session"):
        try:
            device = 'iPhone 16 Pro'
            userbot = Client("userbot", api_id=API_ID, api_hash=API_HASH, device_model=device, session_string=data.get("session"))
            await userbot.start()
            return userbot
        except Exception:
            await app.send_message(user_id, "Login Expired re do login")
            return None
    else:
        return userrbot if DEFAULT_SESSION else None

async def is_normal_tg_link(link: str) -> bool:
    special_identifiers = ['t.me/+', 't.me/c/', 't.me/b/', 'tg://openmessage']
    return 't.me/' in link and not any(x in link for x in special_identifiers)
    
async def process_special_links(userbot, user_id, msg, link):
    if userbot is None:
        return await msg.edit_text("Try logging in to the bot and try again.")
    if 't.me/+' in link:
        result = await userbot_join(userbot, link)
        return await msg.edit_text(result)
    special_patterns = ['t.me/c/', 't.me/b/', '/s/', 'tg://openmessage']
    if any(sub in link for sub in special_patterns):
        await process_and_upload_link(userbot, user_id, msg.id, link, 0, msg)
        await set_interval(user_id, interval_minutes=45)
        return
    await msg.edit_text("Invalid link...")

@app.on_message(filters.command("batch") & filters.private)
async def batch_link(_, message):
    join = await subscribe(_, message)
    if join == 1: return
    user_id = message.chat.id
    if users_loop.get(user_id, False):
        return await app.send_message(message.chat.id, "You already have a batch process running.")

    freecheck = await chk_user(message, user_id)
    if freecheck == 1 and FREEMIUM_LIMIT == 0 and user_id not in OWNER_ID and not await is_user_verified(user_id):
        return await message.reply("Freemium service is currently not available.")

    max_batch_size = FREEMIUM_LIMIT if freecheck == 1 else PREMIUM_LIMIT

    for attempt in range(3):
        start = await app.ask(message.chat.id, "Please send the start link.\n\n> Maximum tries 3")
        start_id = start.text.strip()
        s = start_id.split("/")[-1]
        if s.isdigit():
            cs = int(s)
            break
        await app.send_message(message.chat.id, "Invalid link. Please send again ...")
    else:
        return await app.send_message(message.chat.id, "Maximum attempts exceeded.")

    for attempt in range(3):
        num_messages = await app.ask(message.chat.id, f"How many messages do you want to process?\n> Max limit {max_batch_size}")
        try:
            cl = int(num_messages.text.strip())
            if 1 <= cl <= max_batch_size: break
            raise ValueError()
        except ValueError:
            await app.send_message(message.chat.id, f"Invalid number.")
    else:
        return await app.send_message(message.chat.id, "Maximum attempts exceeded.")

    can_proceed, response_message = await check_interval(user_id, freecheck)
    if not can_proceed: return await message.reply(response_message)
        
    join_button = InlineKeyboardButton("Join Channel", url="https://t.me/team_spy_pro")
    keyboard = InlineKeyboardMarkup([[join_button]])
    pin_msg = await app.send_message(user_id, f"Batch process started ⚡\nProcessing: 0/{cl}", reply_markup=keyboard)
    await pin_msg.pin(both_sides=True)

    users_loop[user_id] = True
    try:
        normal_links_handled = False
        userbot = await initialize_userbot(user_id)
        for i in range(cs, cs + cl):
            if user_id in users_loop and users_loop[user_id]:
                url = f"{'/'.join(start_id.split('/')[:-1])}/{i}"
                link = get_link(url)
                if 't.me/' in link and not any(x in link for x in ['t.me/b/', 't.me/c/', 'tg://openmessage']):
                    msg = await app.send_message(message.chat.id, f"Processing...")
                    await process_and_upload_link(userbot, user_id, msg.id, link, 0, message)
                    await pin_msg.edit_text(f"Batch process started ⚡\nProcessing: {i - cs + 1}/{cl}", reply_markup=keyboard)
                    normal_links_handled = True
        if normal_links_handled:
            await set_interval(user_id, interval_minutes=300)
            await pin_msg.edit_text(f"Batch completed successfully for {cl} messages 🎉", reply_markup=keyboard)
            return await app.send_message(message.chat.id, "Batch completed successfully! 🎉")
            
        for i in range(cs, cs + cl):
            if not userbot:
                users_loop[user_id] = False
                return await app.send_message(message.chat.id, "Login in bot first ...")
            if user_id in users_loop and users_loop[user_id]:
                url = f"{'/'.join(start_id.split('/')[:-1])}/{i}"
                link = get_link(url)
                if any(x in link for x in ['t.me/b/', 't.me/c/']):
                    msg = await app.send_message(message.chat.id, f"Processing...")
                    await process_and_upload_link(userbot, user_id, msg.id, link, 0, message)
                    await pin_msg.edit_text(f"Batch process started ⚡\nProcessing: {i - cs + 1}/{cl}", reply_markup=keyboard)

        await set_interval(user_id, interval_minutes=300)
        await pin_msg.edit_text(f"Batch completed successfully for {cl} messages 🎉", reply_markup=keyboard)
        await app.send_message(message.chat.id, "Batch completed successfully! 🎉")
    except Exception as e:
        await app.send_message(message.chat.id, f"Error: {e}")
    finally:
        users_loop.pop(user_id, None)

@app.on_message(filters.command("cancel"))
async def stop_batch(_, message):
    user_id = message.chat.id
    if user_id in users_loop and users_loop[user_id]:
        users_loop[user_id] = False  
        active_clones[user_id] = False 
        await app.send_message(message.chat.id, "Task has been stopped successfully.")
    else:
        await app.send_message(message.chat.id, "No active task is running to cancel.")

# -------------------------------------------------------------------------------------------
# 🚀 ADVANCED FORUM CLONER (MULTI-SELECT MENU + ANTI-FLOOD)
# -------------------------------------------------------------------------------------------
active_clones = {}
topic_selections = {}

async def safe_edit(msg_obj, text, **kwargs):
    if not msg_obj: return None
    try:
        await msg_obj.edit_text(text, **kwargs)
        return msg_obj
    except MessageIdInvalid: return None  
    except FloodWait as fw:
        await asyncio.sleep(fw.value + random.randint(2, 5))
        return await safe_edit(msg_obj, text, **kwargs)
    except Exception: return msg_obj

def parse_tg_link(link: str) -> tuple:
    link = link.split("?")[0].rstrip("/")
    parts = link.split("/")
    try:
        if "t.me/c/" in link: return int("-100" + parts[4]), int(parts[-1])
        elif "t.me/" in link: return parts[3], int(parts[-1])
    except Exception: pass
    raise ValueError("Invalid format")

def generate_msg_link(chat_id, chat_username, msg_id):
    return f"https://t.me/{chat_username}/{msg_id}" if chat_username else f"https://t.me/c/{str(chat_id).replace('-100', '')}/{msg_id}"

# ----------------- UI: MULTI-SELECT MENU GENERATOR -----------------
async def send_topic_menu(user_id, message_obj):
    data = topic_selections.get(user_id)
    if not data: return
    
    topic_btns = []
    for t_id, t_title in data["topics"].items():
        safe_title = str(t_title or f"T-{t_id}")[:12]
        status = "✅" if t_id in data["selected"] else "❌"
        topic_btns.append(InlineKeyboardButton(f"{status} {safe_title}", callback_data=f"tsel_{t_id}"))
    
    buttons = [topic_btns[i:i + 2] for i in range(0, len(topic_btns), 2)]
    
    buttons.append([
        InlineKeyboardButton("☑️ Select All", callback_data="tsel_all"),
        InlineKeyboardButton("🔳 Deselect All", callback_data="tsel_none")
    ])
    buttons.append([
        InlineKeyboardButton("▶️ Start", callback_data="tsel_start"),
        InlineKeyboardButton("✖️ Cancel", callback_data="cancel_clone_task")
    ])
    
    try:
        await message_obj.edit_text(
            f"📋 **Forum Group:** `{data['chat_title']}`\n\nKripya topics select karein:", 
            reply_markup=InlineKeyboardMarkup(buttons)
        )
    except Exception as e:
        await message_obj.edit_text(f"⚠️ Telegram UI Limit Hit. Error: {e}")

@app.on_callback_query(filters.regex(r"^tsel_"))
async def topic_selection_handler(_, query):
    user_id = query.from_user.id
    action = query.data.replace("tsel_", "")
    
    if user_id not in topic_selections:
        return await query.answer("❌ Session expired. Please run /clone again.", show_alert=True)
        
    data = topic_selections[user_id]
    
    if action == "all": data["selected"] = list(data["topics"].keys())
    elif action == "none": data["selected"] = []
    elif action == "start":
        if not data["selected"]: return await query.answer("⚠️ Kripya kam se kam ek topic select karein!", show_alert=True)
        
        await query.message.edit_text("⏳ **Targets locked. Cloning shuru ho rahi hai...**")
        userbot = await initialize_userbot(user_id)
        active_clones[user_id] = True
        
        asyncio.create_task(run_forum_clone(user_id, userbot, data["chat_id"], data["username"], data["chat_title"], data["selected"], query.message, fresh_start_id=data["start_msg_id"]))
        del topic_selections[user_id]
        return
    else:
        t_id = int(action)
        if t_id in data["selected"]: data["selected"].remove(t_id)
        else: data["selected"].append(t_id)
            
    await send_topic_menu(user_id, query.message)

# ----------------- MAIN CLONE COMMAND -----------------
@app.on_message(filters.command("clone") & filters.private)
async def clone_command_handler(_, message):
    user_id = message.chat.id
    if active_clones.get(user_id, False) or users_loop.get(user_id, False):
        return await message.reply("⚠️ Aapka ek task pehle se chal raha hai.")

    saved_state = await get_clone_state(user_id)
    if saved_state:
        buttons = InlineKeyboardMarkup([
            [InlineKeyboardButton("▶️ Resume Clone", callback_data="resume_clone")],
            [InlineKeyboardButton("🔄 Start New", callback_data="clear_and_new_clone")],
            [InlineKeyboardButton("✖️ Cancel Task", callback_data="cancel_clone_task")]
        ])
        return await message.reply(f"⚠️ **Interrupted Task Mila!**\nSource: `{saved_state.get('chat_title')}`\nResume karna hai?", reply_markup=buttons)

    if len(message.command) < 2: return await message.reply("📝 **Usage:** `/clone <message_link>`")

    url = message.command[1]
    status_msg = await message.reply("🔍 **Verify ho raha hai...**")
    
    try: chat_peer, start_msg_id = parse_tg_link(url)
    except: return await status_msg.edit_text("❌ Galat link format!")

    userbot = await initialize_userbot(user_id)
    if not userbot: return await status_msg.edit_text("❌ Pehle /login karein.")

    try:
        source_chat = await userbot.get_chat(chat_peer)
        chat_id, chat_title = source_chat.id, source_chat.title or "Chat"
        chat_username = getattr(source_chat, "username", None)
        
        # 🔥 FIX 2: Smart Forum Detector (Bypasses Pyrogram is_forum Bug)
        is_forum = getattr(source_chat, "is_forum", False)
        url_parts = url.split("?")[0].rstrip("/").split("/")
        
        if "t.me/c/" in url and len(url_parts) >= 7: 
            is_forum = True
        elif "t.me/c/" not in url and "t.me/" in url and len(url_parts) >= 6: 
            is_forum = True
        
        if is_forum:
            await status_msg.edit_text("👾 **Forum Topics fetch ho rahe hain...**")
            peer = await userbot.resolve_peer(chat_id)
            input_channel = raw.types.InputChannel(channel_id=peer.channel_id, access_hash=peer.access_hash)
            result = await userbot.invoke(raw.functions.channels.GetForumTopics(channel=input_channel, offset_date=0, offset_id=0, offset_topic=0, limit=30))
            
            topic_selections[user_id] = {
                "chat_id": chat_id, "chat_title": chat_title, "username": chat_username, 
                "start_msg_id": start_msg_id, "topics": {t.id: getattr(t, 'title', f"Topic {t.id}") for t in result.topics}, "selected": []
            }
            await send_topic_menu(user_id, status_msg)
            await userbot.stop()
        else:
            await status_msg.edit_text("📢 **Normal Chat detected! Scanning...**")
            end_id = start_msg_id
            async for last_msg in userbot.get_chat_history(chat_id, limit=1):
                end_id = last_msg.id
                break
            active_clones[user_id] = True
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
        if user_id in topic_selections: del topic_selections[user_id]
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
            asyncio.create_task(run_forum_clone(user_id, userbot, state["chat_id"], state.get("username"), state["chat_title"], state["topic_ids"], query.message, resume_id=state["last_id"]))
        else:
            asyncio.create_task(run_standard_clone(user_id, userbot, state["chat_id"], state.get("username"), state["chat_title"], state["last_id"], state["end_id"], query.message))
        return

# ----------------- ENGINES -----------------
async def run_standard_clone(user_id, userbot, chat_id, chat_username, chat_title, start_id, end_id, message_obj):
    dummy_msg = None
    try:
        pin_log = await app.send_message(user_id, f"📌 **Task Started**\nChat: `{chat_title}`")
        dummy_msg = await app.send_message(user_id, "🔄 **Extracting Data...**")
        
        count, CHUNK = 0, 20
        for current in range(start_id, end_id + 1, CHUNK):
            if not active_clones.get(user_id, False): return
            await set_clone_state(user_id, {"chat_id": chat_id, "username": chat_username, "chat_title": chat_title, "last_id": current, "end_id": end_id, "type": "standard"})
            limit_end = min(current + CHUNK, end_id + 1)
            try:
                for msg in await userbot.get_messages(chat_id, list(range(current, limit_end))):
                    if not active_clones.get(user_id, False): return
                    if not msg or msg.empty or not getattr(msg, 'media', None): continue
                    
                    await get_msg(userbot, user_id, dummy_msg.id, generate_msg_link(chat_id, chat_username, msg.id), 0, message_obj)
                    count += 1
                    await asyncio.sleep(random.uniform(1.5, 3.2)) 
                    
                pin_log = await safe_edit(pin_log, f"🚀 **Progress:** `{count}` files done.")
                await asyncio.sleep(random.randint(6, 12)) 
            except FloodWait as fw:
                await asyncio.sleep(fw.value + random.randint(5, 10))
            except Exception: pass
            
        await safe_edit(pin_log, f"✅ **Extraction finished!**")
        await app.send_message(user_id, f"✅ **Clone Complete!**\n🎉 Total `{count}` items transferred from `{chat_title}`.")
        await remove_clone_state(user_id)
    finally:
        active_clones[user_id] = False
        try: await dummy_msg.delete()
        except: pass
        try: await userbot.stop()
        except: pass

async def run_forum_clone(user_id, userbot, chat_id, chat_username, chat_title, topic_ids, message_obj, fresh_start_id=1, resume_id=None):
    dummy_msg = None
    try:
        pin_log = await app.send_message(user_id, f"📌 **Forum Clone Started**\nTopics selected: `{len(topic_ids)}`")
        dummy_msg = await app.send_message(user_id, "🔄 **Extracting Topics...**")
        
        total_cloned, summary_records = 0, []
        for idx, t_id in enumerate(topic_ids, 1):
            if not active_clones.get(user_id, False): return
            current_start = resume_id if (resume_id and idx == 1) else fresh_start_id
            topic_count, max_id = 0, current_start
            async for thread_msg in userbot.get_chat_history(chat_id, limit=1, message_thread_id=t_id):
                max_id = thread_msg.id
                break
            
            target_chat_data = await db.get_data(user_id)
            if target_chat_data and target_chat_data.get("chat_id"):
                try: await app.send_message(target_chat_data["chat_id"], f"━━━━━━━━━━━━━━━━━━━━━\n📁 **TOPIC: {t_id}**\n━━━━━━━━━━━━━━━━━━━━━")
                except: pass

            CHUNK = 20
            for curr_id in range(current_start, max_id + 1, CHUNK):
                if not active_clones.get(user_id, False): return
                await set_clone_state(user_id, {"chat_id": chat_id, "username": chat_username, "chat_title": chat_title, "topic_ids": topic_ids, "last_id": curr_id, "type": "forum"})
                try:
                    for msg in await userbot.get_messages(chat_id, list(range(curr_id, min(curr_id + CHUNK, max_id + 1)))):
                        if not msg or msg.empty or getattr(msg, 'message_thread_id', None) != t_id or (not msg.media and not msg.text): continue
                        
                        await get_msg(userbot, user_id, dummy_msg.id, generate_msg_link(chat_id, chat_username, msg.id), 0, message_obj)
                        topic_count += 1
                        total_cloned += 1
                        await asyncio.sleep(random.uniform(1.5, 3.2)) 
                        
                    pin_log = await safe_edit(pin_log, f"📁 **Topic [{idx}/{len(topic_ids)}]**\nThread ID: `{t_id}`\nItems done: `{topic_count}`\nTotal: `{total_cloned}`")
                    await asyncio.sleep(random.randint(6, 12)) 
                except FloodWait as fw:
                    await asyncio.sleep(fw.value + random.randint(5, 10))
                except Exception: pass
            summary_records.append({"topic_id": t_id, "count": topic_count})
            resume_id = None

        final_text = "✅ **Selected Topics Cloned!**\n\n" + "".join([f"• Thread `{r['topic_id']}` ➔ `{r['count']}` files\n" for r in summary_records])
        await safe_edit(pin_log, "✅ **Cloning Finished!** Check the summary below.")
        
        await app.send_message(user_id, final_text + f"\n🔥 **Grand Total:** `{total_cloned}`")
        await remove_clone_state(user_id)
    finally:
        active_clones[user_id] = False
        try: await dummy_msg.delete()
        except: pass
        try: await userbot.stop()
        except: pass
