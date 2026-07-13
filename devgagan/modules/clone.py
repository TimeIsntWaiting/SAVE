# ---------------------------------------------------
# File Name: clone.py
# Description: Advanced Smart Scraper & Organizer for 
#              cloning Channels and Forum Groups (Topic-wise).
# Author: Gagan & Team SPY
# License: MIT License
# ---------------------------------------------------

import asyncio
import re
from pyrogram import filters, Client, raw
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message, CallbackQuery
from pyrogram.enums import ChatType
from pyrogram.errors import FloodWait
from devgagan import app
from config import OWNER_ID, FREEMIUM_LIMIT, PREMIUM_LIMIT
from devgagan.core.get_func import get_msg
from devgagan.core.func import chk_user, get_link
from devgagan.modules.shrink import is_user_verified
from devgagan.core.mongo.db import (
    get_data, 
    set_clone_state, 
    get_clone_state, 
    remove_clone_state,
    get_data as get_db_data
)

# Active loops tracker to prevent overlapping tasks
active_clones = {}

async def initialize_userbot(user_id):
    """Initialize user session safely"""
    data = await get_db_data(user_id)
    if data and data.get("session"):
        try:
            userbot = Client(
                "userbot_clone",
                api_id=app.api_id,
                api_hash=app.api_hash,
                session_string=data.get("session")
            )
            await userbot.start()
            return userbot
        except Exception:
            await app.send_message(user_id, "❌ Login Expired! Kripya fir se login karein.")
            return None
    return None

def parse_tg_link(link: str) -> tuple:
    """Extract Chat username/ID and Message ID from link"""
    link = link.split("?")[0].rstrip("/")
    if "t.me/c/" in link:
        parts = link.split("/")
        # Private chat link format: t.me/c/chat_id/msg_id
        return int("-100" + parts[-2]), int(parts[-1])
    elif "t.me/" in link:
        parts = link.split("/")
        # Public chat link format: t.me/username/msg_id
        return parts[-2], int(parts[-1])
    raise ValueError("Invalid Telegram link format")

@app.on_message(filters.command("clone") & filters.private)
async def clone_command_handler(_, message: Message):
    user_id = message.chat.id

    if active_clones.get(user_id, False):
        await message.reply("⚠️ Aapka ek clone task pehle se chal raha hai. Kripya uske khatam hone ka wait karein ya /cancel dabayein.")
        return

    # Check for existing interrupted state (Auto-Resume check)
    saved_state = await get_clone_state(user_id)
    if saved_state:
        buttons = InlineKeyboardMarkup([
            [InlineKeyboardButton("▶️ Resume Clone", callback_data="resume_clone")],
            [InlineKeyboardButton("🔄 Start New", callback_data="clear_and_new_clone")],
            [InlineKeyboardButton("✖️ Cancel Task", callback_data="cancel_clone_task")]
        ])
        await message.reply(
            f"⚠️ **Interrupted Task Mila!**\n\n"
            f"• Source: `{saved_state.get('chat_title')}`\n"
            f"• Last Processed ID: `{saved_state.get('last_id')}`\n\n"
            f"Kya aap isey resume karna chahte hain?", reply_markup=buttons
        )
        return

    if len(message.command) < 2:
        await message.reply(
            "📝 **Usage:**\n"
            "• `/clone <message_link>`\n\n"
            "💡 Channel ya Group (Forum) ke kisi bhi ek message ka link bhejin, bot automatically scan kar lega."
        )
        return

    url = message.command[1]
    status_msg = await message.reply("🔍 **Source details verify ho rahi hain...**")
    
    try:
        chat_peer, start_msg_id = parse_tg_link(url)
    except Exception:
        await status_msg.edit_text("❌ Galat link format! Kripya ek valid Telegram message link bhejein.")
        return

    userbot = await initialize_userbot(user_id)
    if not userbot:
        await status_msg.edit_text("❌ Kripya pehle bot me login karein (/login).")
        return

    try:
        source_chat = await userbot.get_chat(chat_peer)
        chat_id = source_chat.id
        chat_title = source_chat.title or "Telegram Chat"
        
        # Check if the source is a Forum Group (Topics enabled)
        if source_chat.is_forum:
            await status_msg.edit_text("👾 **Forum Group detected! Topics fetch ho rahe hain...**")
            
            # Fetch topics via raw API (Pyrogram native backup method)
            peer = await userbot.resolve_peer(chat_id)
            input_channel = raw.types.InputChannel(channel_id=peer.channel_id, access_hash=peer.access_hash)
            
            result = await userbot.invoke(
                raw.functions.channels.GetForumTopics(
                    channel=input_channel,
                    offset_date=0,
                    offset_id=0,
                    offset_topic=0,
                    limit=40
                )
            )
            
            if not result.topics:
                await status_msg.edit_text("❌ Is group me koi active topics nahi mile.")
                await userbot.stop()
                return

            buttons = []
            for topic in result.topics:
                # topic.id is the message_thread_id
                title = topic.title[:20] + "..." if len(topic.title) > 20 else topic.title
                buttons.append([InlineKeyboardButton(f"📁 {title}", callback_data=f"clone_topic_{chat_id}_{topic.id}_{start_msg_id}")])
            
            buttons.append([InlineKeyboardButton("🌟 Clone ALL Topics", callback_data=f"clone_all_topics_{chat_id}_{start_msg_id}")])
            buttons.append([InlineKeyboardButton("✖️ Cancel", callback_data="cancel_clone_task")])
            
            # Save basic metadata to db state temporarily
            await set_clone_state(user_id, {"chat_title": chat_title, "chat_id": chat_id, "type": "forum"})
            
            await status_msg.edit_text(
                f"📋 **Group:** {chat_title}\n\n"
                f"Kripya niche diye gaye list me se select karein ki kis topic ka backup lena hai:",
                reply_markup=InlineKeyboardMarkup(buttons)
            )
            await userbot.stop()
            
        else:
            # Standard Channel or Normal Group Cloning Logic
            await status_msg.edit_text("📢 **Channel/Normal Chat detected! Scanning history...**")
            
            end_id = start_msg_id
            async for last_msg in userbot.get_chat_history(chat_id, limit=1):
                end_id = last_msg.id
                break
                
            await status_msg.delete()
            active_clones[user_id] = True
            
            # Trigger the standard execution loop
            asyncio.create_task(run_standard_clone(user_id, userbot, chat_id, chat_title, start_msg_id, end_id, message))

    except Exception as e:
        await status_msg.edit_text(f"❌ Error: {str(e)}")
        try: await userbot.stop()
        except: pass

@app.on_callback_query(filters.regex(r"^clone_topic_|^clone_all_topics_|^resume_clone|^clear_and_new_clone|^cancel_clone_task"))
async def handle_clone_callbacks(_, query: CallbackQuery):
    user_id = query.from_user.id
    data = query.data

    if data == "cancel_clone_task":
        active_clones[user_id] = False
        await remove_clone_state(user_id)
        await query.message.delete()
        await query.answer("❌ Task Cancelled.")
        return

    if data == "clear_and_new_clone":
        await remove_clone_state(user_id)
        await query.message.edit_text("✅ Purana state saaf ho gaya hai. Ab aap naye sire se `/clone` command use kar sakte hain.")
        return

    userbot = await initialize_userbot(user_id)
    if not userbot:
        await query.answer("❌ Userbot inactive. Login again.", show_alert=True)
        return

    active_clones[user_id] = True

    if data == "resume_clone":
        state = await get_clone_state(user_id)
        await query.message.delete()
        if state.get("type") == "forum":
            asyncio.create_task(run_forum_clone(user_id, userbot, state["chat_id"], state["chat_title"], state["topic_ids"], message_obj=query.message, resume_id=state["last_id"]))
        else:
            asyncio.create_task(run_standard_clone(user_id, userbot, state["chat_id"], state["chat_title"], state["last_id"], state["end_id"], message_obj=query.message))
        return

    # Parsing parameters for fresh topic selections
    params = data.split("_")
    if data.startswith("clone_topic_"):
        chat_id = int(params[2])
        topic_id = int(params[3])
        start_id = int(params[4])
        await query.message.delete()
        
        asyncio.create_task(run_forum_clone(user_id, userbot, chat_id, "Forum Topic", [topic_id], message_obj=query.message, fresh_start_id=start_id))

    elif data.startswith("clone_all_topics_"):
        chat_id = int(params[3])
        start_id = int(params[4])
        await query.message.delete()
        
        # Re-fetch all topic IDs to loop through them
        peer = await userbot.resolve_peer(chat_id)
        input_channel = raw.types.InputChannel(channel_id=peer.channel_id, access_hash=peer.access_hash)
        result = await userbot.invoke(raw.functions.channels.GetForumTopics(channel=input_channel, offset_date=0, offset_id=0, offset_topic=0, limit=100))
        topic_ids = [t.id for t in result.topics]
        
        asyncio.create_task(run_forum_clone(user_id, userbot, chat_id, "All Topics Backup", topic_ids, message_obj=query.message, fresh_start_id=start_id))

# -------------------------------------------------------------------------------------------
# CORE EXECUTION ENGINES (Standard Channels & Forum Topics)
# -------------------------------------------------------------------------------------------

async def run_standard_clone(user_id, userbot, chat_id, chat_title, start_id, end_id, message_obj):
    """Execution engine for standard channel cloning"""
    try:
        # Pinned initial tracking log message
        pin_log = await app.send_message(user_id, f"📌 **Clone Task Started**\n📢 Chat: `{chat_title}`\n🔄 Range: `{start_id} - {end_id}`\n\n⚡ Processing starts now...")
        try: await pin_log.pin(both_sides=True)
        except: pass

        count = 0
        CHUNK = 50  # Stable processing intervals to mitigate severe FloodWaits

        for current in range(start_id, end_id + 1, CHUNK):
            if not active_clones.get(user_id, False):
                await pin_log.edit_text("🛑 **Task Stopped/Cancelled manually.**")
                return

            # Save state progress dynamically for auto-resume support
            await set_clone_state(user_id, {"chat_id": chat_id, "chat_title": chat_title, "last_id": current, "end_id": end_id, "type": "standard"})
            
            limit_end = min(current + CHUNK, end_id + 1)
            ids_to_fetch = list(range(current, limit_end))
            
            try:
                messages = await userbot.get_messages(chat_id, ids_to_fetch)
                for msg in messages:
                    if not active_clones.get(user_id, False): return
                    if not msg or msg.empty or not msg.media: continue
                    
                    # Generate temporary visual link
                    temp_link = f"https://t.me/c/{str(chat_id).replace('-100', '')}/{msg.id}"
                    
                    # Push file directly into your optimized get_msg transfer pipeline
                    await get_msg(userbot, user_id, pin_log.id, temp_link, 0, message_obj)
                    count += 1
                    
                await pin_log.edit_text(f"🚀 **Cloning Progress**\n📢 Chat: `{chat_title}`\n📦 Total Processed: `{count}` items\n📍 Current ID: `{limit_end - 1}`")
                await asyncio.sleep(5)  # Flood prevention sleep padding
                
            except FloodWait as fw:
                await pin_log.edit_text(f"⏳ Telegram FloodWait Hit! Sleeping for `{fw.value}` seconds...")
                await asyncio.sleep(fw.value + 5)
            except Exception as e:
                print(f"Chunk processing error: {e}")

        await pin_log.edit_text(f"✅ **Cloning Complete!**\n🎉 Total `{count}` items securely transferred from `{chat_title}`.")
        await remove_clone_state(user_id)

    except Exception as e:
        await app.send_message(user_id, f"❌ Critical Clone Error: {str(e)}")
    finally:
        active_clones[user_id] = False
        try: await userbot.stop()
        except: pass

async def run_forum_clone(user_id, userbot, chat_id, chat_title, topic_ids, message_obj, fresh_start_id=1, resume_id=None):
    """Advanced execution engine for Forum Topic filtering and extraction"""
    try:
        pin_log = await app.send_message(user_id, f"📌 **Forum Topic Clone Started**\n📂 Target Topics: `{len(topic_ids)}` thread(s)\n\n⚡ Indexing history records...")
        try: await pin_log.pin(both_sides=True)
        except: pass

        total_cloned = 0
        summary_records = []

        for idx, t_id in enumerate(topic_ids, 1):
            if not active_clones.get(user_id, False):
                await pin_log.edit_text("🛑 **Forum Task Stopped/Cancelled manually.**")
                return

            await set_clone_state(user_id, {"chat_id": chat_id, "chat_title": chat_title, "topic_ids": topic_ids, "last_id": resume_id or fresh_start_id, "type": "forum"})
            
            current_start = resume_id if (resume_id and idx == 1) else fresh_start_id
            topic_count = 0
            
            # Fetch the max message ID inside this specific forum to determine loop boundaries
            max_id = current_start
            async for thread_msg in userbot.get_chat_history(chat_id, limit=1, message_thread_id=t_id):
                max_id = thread_msg.id
                break

            # Send a dynamic title separator block in the target channel to partition this topic cleanly
            separator_link = None
            target_chat_data = await get_db_data(user_id)
            target_chat_id = target_chat_data.get("chat_id") if target_chat_data else None
            
            if target_chat_id:
                try:
                    sep_msg = await app.send_message(
                        target_chat_id, 
                        f"━━━━━━━━━━━━━━━━━━━━━\n"
                        f"📁 **TOPIC BACKUP: Thread ID {t_id}**\n"
                        f"━━━━━━━━━━━━━━━━━━━━━"
                    )
                    # Create hyperlink layout reference
                    chat_clean_id = str(target_chat_id).replace("-100", "")
                    separator_link = f"https://t.me/c/{chat_clean_id}/{sep_msg.id}"
                except:
                    pass

            # Loop through IDs via targeted chunk blocks
            CHUNK = 100
            for curr_id in range(current_start, max_id + 1, CHUNK):
                if not active_clones.get(user_id, False): return
                await set_clone_state(user_id, {"chat_id": chat_id, "chat_title": chat_title, "topic_ids": topic_ids, "last_id": curr_id, "type": "forum"})
                
                limit_end = min(curr_id + CHUNK, max_id + 1)
                ids_to_fetch = list(range(curr_id, limit_end))
                
                try:
                    messages = await userbot.get_messages(chat_id, ids_to_fetch)
                    for msg in messages:
                        if not msg or msg.empty: continue
                        # Strict validation: Process only if message belongs to the current active Topic thread
                        if msg.message_thread_id != t_id: continue
                        if not msg.media and not msg.text: continue
                        
                        temp_link = f"https://t.me/c/{str(chat_id).replace('-100', '')}/{msg.id}"
                        await get_msg(userbot, user_id, pin_log.id, temp_link, 0, message_obj)
                        topic_count += 1
                        total_cloned += 1

                    await pin_log.edit_text(
                        f"📁 **Topic Progress [{idx}/{len(topic_ids)}]**\n"
                        f"• Current Topic: `Thread {t_id}`\n"
                        f"• Items in this thread: `{topic_count}`\n"
                        f"• Total cloned so far: `{total_cloned}`"
                    )
                except FloodWait as fw:
                    await asyncio.sleep(fw.value + 5)
                except:
                    pass

            # Record metrics for the summary hyperlink dashboard
            summary_records.append({"topic_id": t_id, "count": topic_count, "link": separator_link})
            resume_id = None # Clear resume index for subsequent loop iterations

        # -------------------------------------------------------------------------------------------
        # GENERATING THE HYPERLINK COMPLETED SUMMARY DASHBOARD
        # -------------------------------------------------------------------------------------------
        summary_text = (
            "✅ **All Forum Topics Cloned Successfully!** 🎉\n"
            "━━━━━━━━━━━━━━━━━━━━━\n"
            "📊 **Backup Metrics Report:**\n\n"
        )
        for rec in summary_records:
            if rec["link"]:
                summary_text += f"• [📁 Topic Thread {rec['topic_id']}]({rec['link']}) ➔ `{rec['count']}` files transferred.\n"
            else:
                summary_text += f"• 📁 Topic Thread `{rec['topic_id']}` ➔ `{rec['count']}` files transferred.\n"
        
        summary_text += f"\n🔥 **Total Grand Files Combined:** `{total_cloned}`\n━━━━━━━━━━━━━━━━━━━━━"
        
        await pin_log.edit_text(summary_text, disable_web_page_preview=True)
        await remove_clone_state(user_id)

    except Exception as e:
        await app.send_message(user_id, f"❌ Critical Forum Clone Error: {str(e)}")
    finally:
        active_clones[user_id] = False
        try: await userbot.stop()
        except: pass
  
