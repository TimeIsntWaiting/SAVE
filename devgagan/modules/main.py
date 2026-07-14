# ---------------------------------------------------
# File Name: main.py
# Description: A Pyrogram bot for downloading files from Telegram channels or groups 
#              and uploading them back to Telegram.
# Author: Gagan
# GitHub: https://github.com/devgaganin/
# Telegram: https://t.me/team_spy_pro
# YouTube: https://youtube.com/@dev_gagan
# Created: 2025-01-11
# Last Modified: 2025-01-11
# Version: 2.0.5
# License: MIT License
# More readable 
# ---------------------------------------------------

import time
import random
import string
import asyncio
from pyrogram import filters, Client
from devgagan import app, userrbot
from config import API_ID, API_HASH, FREEMIUM_LIMIT, PREMIUM_LIMIT, OWNER_ID, DEFAULT_SESSION
from devgagan.core.get_func import get_msg
from devgagan.core.func import *
from devgagan.core.mongo import db
from pyrogram.errors import FloodWait
from datetime import datetime, timedelta
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup
import subprocess
from devgagan.modules.shrink import is_user_verified
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

# Function to check if the user can proceed
async def check_interval(user_id, freecheck):
    if freecheck != 1 or await is_user_verified(user_id):  # Premium or owner users can always proceed
        return True, None

    now = datetime.now()

    # Check if the user is on cooldown
    if user_id in interval_set:
        cooldown_end = interval_set[user_id]
        if now < cooldown_end:
            remaining_time = (cooldown_end - now).seconds
            return False, f"Please wait {remaining_time} seconds(s) before sending another link. Alternatively, purchase premium for instant access.\n\n> Hey 👋 You can use /token to use the bot free for 3 hours without any time limit."
        else:
            del interval_set[user_id]  # Cooldown expired, remove user from interval set

    return True, None

async def set_interval(user_id, interval_minutes=45):
    now = datetime.now()
    # Set the cooldown interval for the user
    interval_set[user_id] = now + timedelta(seconds=interval_minutes)
    

@app.on_message(
    filters.regex(r'https?://(?:www\.)?t\.me/[^\s]+|tg://openmessage\?user_id=\w+&message_id=\d+')
    & filters.private
)
async def single_link(_, message):
    user_id = message.chat.id

    # Check subscription and batch mode
    if await subscribe(_, message) == 1 or user_id in batch_mode:
        return

    # Check if user is already in a loop
    if users_loop.get(user_id, False):
        await message.reply(
            "You already have an ongoing process. Please wait for it to finish or cancel it with /cancel."
        )
        return

    # Check freemium limits
    if await chk_user(message, user_id) == 1 and FREEMIUM_LIMIT == 0 and user_id not in OWNER_ID and not await is_user_verified(user_id):
        await message.reply("Freemium service is currently not available. Upgrade to premium for access.")
        return

    # Check cooldown
    can_proceed, response_message = await check_interval(user_id, await chk_user(message, user_id))
    if not can_proceed:
        await message.reply(response_message)
        return

    # Add user to the loop
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
        await msg.edit_text(f'Try again after {fw.x} seconds due to floodwait from Telegram.')
    except Exception as e:
        await msg.edit_text(f"Link: `{link}`\n\n**Error:** {str(e)}")
    finally:
        users_loop[user_id] = False
        try:
            await msg.delete()
        except Exception:
            pass


async def initialize_userbot(user_id): # this ensure the single startup .. even if logged in or not
    data = await db.get_data(user_id)
    if data and data.get("session"):
        try:
            device = 'iPhone 16 Pro' # added gareebi text
            userbot = Client(
                "userbot",
                api_id=API_ID,
                api_hash=API_HASH,
                device_model=device,
                session_string=data.get("session")
            )
            await userbot.start()
            return userbot
        except Exception:
            await app.send_message(user_id, "Login Expired re do login")
            return None
    else:
        if DEFAULT_SESSION:
            return userrbot
        else:
            return None


async def is_normal_tg_link(link: str) -> bool:
    """Check if the link is a standard Telegram link."""
    special_identifiers = ['t.me/+', 't.me/c/', 't.me/b/', 'tg://openmessage']
    return 't.me/' in link and not any(x in link for x in special_identifiers)
    
async def process_special_links(userbot, user_id, msg, link):
    if userbot is None:
        return await msg.edit_text("Try logging in to the bot and try again.")
    if 't.me/+' in link:
        result = await userbot_join(userbot, link)
        await msg.edit_text(result)
        return
    special_patterns = ['t.me/c/', 't.me/b/', '/s/', 'tg://openmessage']
    if any(sub in link for sub in special_patterns):
        await process_and_upload_link(userbot, user_id, msg.id, link, 0, msg)
        await set_interval(user_id, interval_minutes=45)
        return
    await msg.edit_text("Invalid link...")


@app.on_message(filters.command("batch") & filters.private)
async def batch_link(_, message):
    join = await subscribe(_, message)
    if join == 1:
        return
    user_id = message.chat.id
    # Check if a batch process is already running
    if users_loop.get(user_id, False):
        await app.send_message(
            message.chat.id,
            "You already have a batch process running. Please wait for it to complete."
        )
        return

    freecheck = await chk_user(message, user_id)
    if freecheck == 1 and FREEMIUM_LIMIT == 0 and user_id not in OWNER_ID and not await is_user_verified(user_id):
        await message.reply("Freemium service is currently not available. Upgrade to premium for access.")
        return

    max_batch_size = FREEMIUM_LIMIT if freecheck == 1 else PREMIUM_LIMIT

    # Start link input
    for attempt in range(3):
        start = await app.ask(message.chat.id, "Please send the start link.\n\n> Maximum tries 3")
        start_id = start.text.strip()
        s = start_id.split("/")[-1]
        if s.isdigit():
            cs = int(s)
            break
        await app.send_message(message.chat.id, "Invalid link. Please send again ...")
    else:
        await app.send_message(message.chat.id, "Maximum attempts exceeded. Try later.")
        return

    # Number of messages input
    for attempt in range(3):
        num_messages = await app.ask(message.chat.id, f"How many messages do you want to process?\n> Max limit {max_batch_size}")
        try:
            cl = int(num_messages.text.strip())
            if 1 <= cl <= max_batch_size:
                break
            raise ValueError()
        except ValueError:
            await app.send_message(
                message.chat.id, 
                f"Invalid number. Please enter a number between 1 and {max_batch_size}."
            )
    else:
        await app.send_message(message.chat.id, "Maximum attempts exceeded. Try later.")
        return

    # Validate and interval check
    can_proceed, response_message = await check_interval(user_id, freecheck)
    if not can_proceed:
        await message.reply(response_message)
        return
        
    join_button = InlineKeyboardButton("Join Channel", url="https://t.me/team_spy_pro")
    keyboard = InlineKeyboardMarkup([[join_button]])
    pin_msg = await app.send_message(
        user_id,
        f"Batch process started ⚡\nProcessing: 0/{cl}\n\n**Powered by Team SPY**",
        reply_markup=keyboard
    )
    await pin_msg.pin(both_sides=True)

    users_loop[user_id] = True
    try:
        normal_links_handled = False
        userbot = await initialize_userbot(user_id)
        # Handle normal links first
        for i in range(cs, cs + cl):
            if user_id in users_loop and users_loop[user_id]:
                url = f"{'/'.join(start_id.split('/')[:-1])}/{i}"
                link = get_link(url)
                # Process t.me links (normal) without userbot
                if 't.me/' in link and not any(x in link for x in ['t.me/b/', 't.me/c/', 'tg://openmessage']):
                    msg = await app.send_message(message.chat.id, f"Processing...")
                    await process_and_upload_link(userbot, user_id, msg.id, link, 0, message)
                    await pin_msg.edit_text(
                        f"Batch process started ⚡\nProcessing: {i - cs + 1}/{cl}\n\n**__Powered by Team SPY__**",
                        reply_markup=keyboard
                    )
                    normal_links_handled = True
        if normal_links_handled:
            await set_interval(user_id, interval_minutes=300)
            await pin_msg.edit_text(
                f"Batch completed successfully for {cl} messages 🎉\n\n**__Powered by Team SPY__**",
                reply_markup=keyboard
            )
            await app.send_message(message.chat.id, "Batch completed successfully! 🎉")
            return
            
        # Handle special links with userbot
        for i in range(cs, cs + cl):
            if not userbot:
                await app.send_message(message.chat.id, "Login in bot first ...")
                users_loop[user_id] = False
                return
            if user_id in users_loop and users_loop[user_id]:
                url = f"{'/'.join(start_id.split('/')[:-1])}/{i}"
                link = get_link(url)
                if any(x in link for x in ['t.me/b/', 't.me/c/']):
                    msg = await app.send_message(message.chat.id, f"Processing...")
                    await process_and_upload_link(userbot, user_id, msg.id, link, 0, message)
                    await pin_msg.edit_text(
                        f"Batch process started ⚡\nProcessing: {i - cs + 1}/{cl}\n\n**__Powered by Team SPY__**",
                        reply_markup=keyboard
                    )

        await set_interval(user_id, interval_minutes=300)
        await pin_msg.edit_text(
            f"Batch completed successfully for {cl} messages 🎉\n\n**__Powered by Team SPY__**",
            reply_markup=keyboard
        )
        await app.send_message(message.chat.id, "Batch completed successfully! 🎉")

    except Exception as e:
        await app.send_message(message.chat.id, f"Error: {e}")
    finally:
        users_loop.pop(user_id, None)

@app.on_message(filters.command("cancel"))
async def stop_batch(_, message):
    user_id = message.chat.id

    # Check if there is an active batch process for the user
    if user_id in users_loop and users_loop[user_id]:
        users_loop[user_id] = False  # Set the loop status to False
        await app.send_message(
            message.chat.id, 
            "Batch processing has been stopped successfully. You can start a new batch now if you want."
        )
    elif user_id in users_loop and not users_loop[user_id]:
        await app.send_message(
            message.chat.id, 
            "The batch process was already stopped. No active batch to cancel."
        )
    else:
        await app.send_message(
            message.chat.id, 
            "No active batch processing is running to cancel."
        )
# -------------------------------------------------------------------------------------------
# 🚀 SMART CLONE & FORUM SCRAPER LOGIC (MERGED)
# -------------------------------------------------------------------------------------------
import random
import asyncio
from pyrogram import raw
from pyrogram.errors import FloodWait, MessageIdInvalid
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from devgagan.core.mongo.db import set_clone_state, get_clone_state, remove_clone_state, get_data as get_db_data
from devgagan.core.get_func import get_msg

active_clones = {}

async def safe_edit(msg_obj, text, **kwargs):
    """Safely edits a message. If deleted, ignores and prevents crashes."""
    if not msg_obj: return None
    try:
        await msg_obj.edit_text(text, **kwargs)
        return msg_obj
    except MessageIdInvalid:
        return None
    except FloodWait as fw:
        await asyncio.sleep(fw.value + random.randint(2, 5))
        return await safe_edit(msg_obj, text, **kwargs)
    except Exception:
        return msg_obj

async def initialize_userbot(user_id):
    data = await get_db_data(user_id)
    if data and data.get("session"):
        try:
            from pyrogram import Client
            userbot = Client("userbot_clone", api_id=app.api_id, api_hash=app.api_hash, session_string=data.get("session"))
            await userbot.start()
            return userbot
        except Exception:
            await app.send_message(user_id, "❌ Login Expired! Kripya fir se /login karein.")
    return None

def parse_tg_link(link: str) -> tuple:
    link = link.split("?")[0].rstrip("/")
    parts = link.split("/")
    try:
        if "t.me/c/" in link:
            return int("-100" + parts[4]), int(parts[-1])
        elif "t.me/" in link:
            return parts[3], int(parts[-1])
    except Exception: pass
    raise ValueError("Invalid Telegram link format")

def generate_msg_link(chat_id, chat_username, msg_id):
    return f"https://t.me/{chat_username}/{msg_id}" if chat_username else f"https://t.me/c/{str(chat_id).replace('-100', '')}/{msg_id}"

@app.on_message(filters.command("clone") & filters.private)
async def clone_command_handler(_, message):
    user_id = message.chat.id
    if active_clones.get(user_id, False):
        return await message.reply("⚠️ Aapka ek clone task pehle se chal raha hai. Kripya wait karein.")

    saved_state = await get_clone_state(user_id)
    if saved_state:
        buttons = InlineKeyboardMarkup([
            [InlineKeyboardButton("▶️ Resume Clone", callback_data="resume_clone")],
            [InlineKeyboardButton("🔄 Start New", callback_data="clear_and_new_clone")],
            [InlineKeyboardButton("✖️ Cancel Task", callback_data="cancel_clone_task")]
        ])
        return await message.reply(f"⚠️ **Interrupted Task Mila!**\nSource: `{saved_state.get('chat_title')}`\nResume karna hai?", reply_markup=buttons)

    if len(message.command) < 2:
        return await message.reply("📝 **Usage:** `/clone <message_link>`")

    url = message.command[1]
    status_msg = await message.reply("🔍 **Verify ho raha hai...**")
    
    try:
        chat_peer, start_msg_id = parse_tg_link(url)
    except Exception:
        return await status_msg.edit_text("❌ Galat link format!")

    userbot = await initialize_userbot(user_id)
    if not userbot: return await status_msg.edit_text("❌ Pehle bot me /login karein.")

    try:
        source_chat = await userbot.get_chat(chat_peer)
        chat_id, chat_title = source_chat.id, source_chat.title or "Chat"
        chat_username = getattr(source_chat, "username", None)
        
        if getattr(source_chat, "is_forum", False):
            await status_msg.edit_text("👾 **Forum Group detected! Fetching topics...**")
            peer = await userbot.resolve_peer(chat_id)
            input_channel = raw.types.InputChannel(channel_id=peer.channel_id, access_hash=peer.access_hash)
            result = await userbot.invoke(raw.functions.channels.GetForumTopics(channel=input_channel, offset_date=0, offset_id=0, offset_topic=0, limit=50))
            
            buttons = [[InlineKeyboardButton(f"📁 {t.title[:20]}", callback_data=f"clone_topic_{chat_id}_{t.id}_{start_msg_id}")] for t in result.topics]
            buttons.append([InlineKeyboardButton("🌟 Clone ALL", callback_data=f"clone_all_topics_{chat_id}_{start_msg_id}")])
            await set_clone_state(user_id, {"chat_title": chat_title, "chat_id": chat_id, "username": chat_username, "type": "forum"})
            await status_msg.edit_text(f"📋 **Group:** {chat_title}\nSelect topic:", reply_markup=InlineKeyboardMarkup(buttons))
            await userbot.stop()
        else:
            await status_msg.edit_text("📢 **Normal Chat detected! Scanning...**")
            end_id = start_msg_id
            async for last_msg in userbot.get_chat_history(chat_id, limit=1):
                end_id = last_msg.id
                break
            await status_msg.delete()
            active_clones[user_id] = True
            asyncio.create_task(run_standard_clone(user_id, userbot, chat_id, chat_username, chat_title, start_msg_id, end_id, message))
    except Exception as e:
        await status_msg.edit_text(f"❌ Error: {str(e)}")
        try: await userbot.stop()
        except: pass

@app.on_callback_query(filters.regex(r"^clone_topic_|^clone_all_topics_|^resume_clone|^clear_and_new_clone|^cancel_clone_task"))
async def handle_clone_callbacks(_, query):
    user_id, data = query.from_user.id, query.data
    if data == "cancel_clone_task":
        active_clones[user_id] = False
        await remove_clone_state(user_id)
        return await query.message.delete()
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

    params = data.split("_")
    if data.startswith("clone_topic_"):
        chat_id, topic_id, start_id = int(params[2]), int(params[3]), int(params[4])
        state = await get_clone_state(user_id)
        await query.message.delete()
        asyncio.create_task(run_forum_clone(user_id, userbot, chat_id, state.get("username") if state else None, "Forum Topic", [topic_id], query.message, fresh_start_id=start_id))

    elif data.startswith("clone_all_topics_"):
        chat_id, start_id = int(params[3]), int(params[4])
        state = await get_clone_state(user_id)
        await query.message.delete()
        peer = await userbot.resolve_peer(chat_id)
        input_channel = raw.types.InputChannel(channel_id=peer.channel_id, access_hash=peer.access_hash)
        result = await userbot.invoke(raw.functions.channels.GetForumTopics(channel=input_channel, offset_date=0, offset_id=0, offset_topic=0, limit=100))
        topic_ids = [t.id for t in result.topics]
        asyncio.create_task(run_forum_clone(user_id, userbot, chat_id, state.get("username") if state else None, "All Topics Backup", topic_ids, query.message, fresh_start_id=start_id))

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
                    await get_msg(userbot, user_id, pin_log.id if pin_log else 0, generate_msg_link(chat_id, chat_username, msg.id), 0, message_obj)
                    count += 1
                    await asyncio.sleep(random.uniform(1.5, 3.2)) # Stealth Micro-delay
                pin_log = await safe_edit(pin_log, f"🚀 **Progress:** `{count}` files done.")
                await asyncio.sleep(random.randint(6, 12)) # Stealth Chunk delay
            except FloodWait as fw:
                await asyncio.sleep(fw.value + random.randint(5, 10))
            except Exception: pass
        await safe_edit(pin_log, f"✅ **Complete!** `{count}` items transferred.")
        await remove_clone_state(user_id)
    finally:
        active_clones[user_id] = False
        try: await userbot.stop()
        except: pass

async def run_forum_clone(user_id, userbot, chat_id, chat_username, chat_title, topic_ids, message_obj, fresh_start_id=1, resume_id=None):
    try:
        pin_log = await app.send_message(user_id, f"📌 **Forum Clone Started**\nTopics: `{len(topic_ids)}`")
        total_cloned, summary_records = 0, []
        for idx, t_id in enumerate(topic_ids, 1):
            if not active_clones.get(user_id, False): return
            current_start = resume_id if (resume_id and idx == 1) else fresh_start_id
            topic_count, max_id = 0, current_start
            async for thread_msg in userbot.get_chat_history(chat_id, limit=1, message_thread_id=t_id):
                max_id = thread_msg.id
                break
            
            target_chat_data = await get_db_data(user_id)
            if target_chat_data and target_chat_data.get("chat_id"):
                try: await app.send_message(target_chat_data["chat_id"], f"━━━━━━━━━━━━━━━━━━━━━\n📁 **TOPIC: {t_id}**\n━━━━━━━━━━━━━━━━━━━━━")
                except: pass

            CHUNK = 20
            for curr_id in range(current_start, max_id + 1, CHUNK):
                if not active_clones.get(user_id, False): return
                await set_clone_state(user_id, {"chat_id": chat_id, "username": chat_username, "chat_title": chat_title, "topic_ids": topic_ids, "last_id": curr_id, "type": "forum"})
                try:
                    for msg in await userbot.get_messages(chat_id, list(range(curr_id, min(curr_id + CHUNK, max_id + 1)))):
                        if not msg or msg.empty or msg.message_thread_id != t_id or (not msg.media and not msg.text): continue
                        await get_msg(userbot, user_id, pin_log.id if pin_log else 0, generate_msg_link(chat_id, chat_username, msg.id), 0, message_obj)
                        topic_count += 1
                        total_cloned += 1
                        await asyncio.sleep(random.uniform(1.5, 3.2)) # Stealth Micro-delay
                    pin_log = await safe_edit(pin_log, f"📁 **Topic [{idx}/{len(topic_ids)}]**\nThread: `{t_id}`\nItems: `{topic_count}`\nTotal: `{total_cloned}`")
                    await asyncio.sleep(random.randint(6, 12)) # Stealth Chunk delay
                except FloodWait as fw:
                    await asyncio.sleep(fw.value + random.randint(5, 10))
                except Exception: pass
            summary_records.append({"topic_id": t_id, "count": topic_count})
            resume_id = None

        final_text = "✅ **Topics Cloned!**\n" + "".join([f"• Thread `{r['topic_id']}` ➔ `{r['count']}` files\n" for r in summary_records])
        await safe_edit(pin_log, final_text + f"🔥 **Grand Total:** `{total_cloned}`")
        await remove_clone_state(user_id)
    finally:
        active_clones[user_id] = False
        try: await userbot.stop()
        except: pass
    
