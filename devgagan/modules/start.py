# ---------------------------------------------------
# File Name: start.py
# Description: A Pyrogram bot for downloading files from Telegram channels or groups 
#              and uploading them back to Telegram.
# Author: Gagan
# GitHub: https://github.com/devgaganin/
# Telegram: https://t.me/team_spy_pro
# License: MIT License
# ---------------------------------------------------

from pyrogram import filters
from devgagan import app
from config import OWNER_ID
from devgagan.core.func import subscribe
import asyncio
from devgagan.core.func import *
from devgagan.core.mongo.db import db as mongodb
from pyrogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, BotCommand
from pyrogram.raw.functions.bots import SetBotInfo
from pyrogram.raw.types import InputUserSelf
 
@app.on_message(filters.command("set"))
async def set(_, message):
    if message.from_user.id not in OWNER_ID:
        await message.reply("You are not authorized to use this command.")
        return
     
    await app.set_bot_commands([
        BotCommand("start", "🚀 Start the bot"),
        BotCommand("batch", "🫠 Extract in bulk"),
        BotCommand("clone", "🎯 Smart clone chat/forum"),
        BotCommand("login", "🔑 Get into the bot"),
        BotCommand("logout", "🚪 Get out of the bot"),
        BotCommand("token", "🎲 Get 3 hours free access"),
        BotCommand("adl", "👻 Download audio from 30+ sites"),
        BotCommand("dl", "💀 Download videos from 30+ sites"),
        BotCommand("freez", "🧊 Remove all expired user"),
        BotCommand("pay", "₹ Pay now to get subscription"),
        BotCommand("status", "⟳ Refresh Payment status"),
        BotCommand("transfer", "💘 Gift premium to others"),
        BotCommand("myplan", "⌛ Get your plan details"),
        BotCommand("add", "➕ Add user to premium"),
        BotCommand("rem", "➖ Remove from premium"),
        BotCommand("session", "🧵 Generate Pyrogramv2 session"),
        BotCommand("settings", "⚙️ Personalize things"),
        BotCommand("stats", "📊 Get stats of the bot"),
        BotCommand("plan", "🗓️ Check our premium plans"),
        BotCommand("terms", "🥺 Terms and conditions"),
        BotCommand("speedtest", "🚅 Speed of server"),
        BotCommand("lock", "🔒 Protect channel from extraction"),
        BotCommand("gcast", "⚡ Broadcast message to bot users"),
        BotCommand("help", "❓ If you're a noob, still!"),
        BotCommand("cancel", "🚫 Cancel batch/clone process")
    ])
    await message.reply("✅ Commands configured successfully!")
 
# ----------------- HELP MENU -----------------
help_pages = [
    (
        "📝 **Bot Commands Overview (1/2)**:\n\n"
        "1. **/add userID**\n> Add user to premium (Owner only)\n\n"
        "2. **/rem userID**\n> Remove user from premium (Owner only)\n\n"
        "3. **/transfer userID**\n> Transfer premium (Premium members only)\n\n"
        "4. **/get**\n> Get all user IDs (Owner only)\n\n"
        "5. **/lock**\n> Lock channel from extraction (Owner only)\n\n"
        "6. **/dl link**\n> Download videos\n\n"
        "7. **/adl link**\n> Download audio\n\n"
        "8. **/login**\n> Log into the bot for private channel access\n\n"
        "9. **/batch**\n> Bulk extraction for posts\n\n"
        "10. **/clone**\n> Extract Forum / Topics smartly\n\n"
    ),
    (
        "📝 **Bot Commands Overview (2/2)**:\n\n"
        "11. **/logout**\n> Logout from the bot\n\n"
        "12. **/stats**\n> Get bot stats\n\n"
        "13. **/plan**\n> Check premium plans\n\n"
        "14. **/speedtest**\n> Test the server speed\n\n"
        "15. **/terms**\n> Terms and conditions\n\n"
        "16. **/cancel**\n> Cancel ongoing batch process\n\n"
        "17. **/myplan**\n> Get details about your plans\n\n"
        "18. **/session**\n> Generate Pyrogram V2 session\n\n"
        "19. **/settings**\n> 🔥 Access the Advanced Settings Menu to toggle Filters, Custom Buttons, Custom Captions, and File Size limits!\n\n"
        "**__Powered by Team SPY__**"
    )
]
 
async def send_or_edit_help_page(_, message, page_number):
    if page_number < 0 or page_number >= len(help_pages): return
    prev_button = InlineKeyboardButton("◀️ Previous", callback_data=f"help_prev_{page_number}")
    next_button = InlineKeyboardButton("Next ▶️", callback_data=f"help_next_{page_number}")
    buttons = []
    if page_number > 0: buttons.append(prev_button)
    if page_number < len(help_pages) - 1: buttons.append(next_button)
    keyboard = InlineKeyboardMarkup([buttons])
    await message.delete()
    await message.reply(help_pages[page_number], reply_markup=keyboard)
 
@app.on_message(filters.command("help"))
async def help(client, message):
    if await subscribe(client, message) == 1: return
    await send_or_edit_help_page(client, message, 0)
 
@app.on_callback_query(filters.regex(r"help_(prev|next)_(\d+)"))
async def on_help_navigation(client, callback_query):
    action, page_number = callback_query.data.split("_")[1], int(callback_query.data.split("_")[2])
    if action == "prev": page_number -= 1
    elif action == "next": page_number += 1
    await send_or_edit_help_page(client, callback_query.message, page_number)
    await callback_query.answer()
 
# ----------------- TERMS & PLANS -----------------
@app.on_message(filters.command("terms") & filters.private)
async def terms(client, message):
    terms_text = (
        "> 📜 **Terms and Conditions** 📜\n\n"
        "✨ We are not responsible for user deeds, and we do not promote copyrighted content.\n"
        "✨ Upon purchase, we do not guarantee the uptime, downtime, or the validity of the plan.\n"
        "✨ Payment to us **__does not guarantee__** authorization for the /batch command. All decisions are at our discretion.\n"
    )
    buttons = InlineKeyboardMarkup([[InlineKeyboardButton("📋 See Plans", callback_data="see_plan")], [InlineKeyboardButton("💬 Contact Now", url="https://t.me/kingofpatal")]])
    await message.reply_text(terms_text, reply_markup=buttons)
 
@app.on_message(filters.command("plan") & filters.private)
async def plan(client, message):
    plan_text = (
        "> 💰 **Premium Price**:\n\n Starting from $2 or 200 INR accepted via **__Amazon Gift Card__**.\n"
        "📥 **Download Limit**: Users can download up to 100,000 files in a single batch command.\n"
        "🛑 **Batch**: You will get two modes /bulk and /batch.\n"
        "📜 **Terms and Conditions**: For further details, please send /terms.\n"
    )
    buttons = InlineKeyboardMarkup([[InlineKeyboardButton("📜 See Terms", callback_data="see_terms")], [InlineKeyboardButton("💬 Contact Now", url="https://t.me/kingofpatal")]])
    await message.reply_text(plan_text, reply_markup=buttons)
 
@app.on_callback_query(filters.regex("see_plan"))
async def see_plan(client, callback_query):
    plan_text = "> 💰 **Premium Price**: Starting from $2 or 200 INR accepted via **__Amazon Gift Card__**.\n📥 **Download Limit**: Users can download up to 100,000 files in a single batch.\n📜 For further details, please send /terms."
    buttons = InlineKeyboardMarkup([[InlineKeyboardButton("📜 See Terms", callback_data="see_terms")], [InlineKeyboardButton("💬 Contact Now", url="https://t.me/kingofpatal")]])
    await callback_query.message.edit_text(plan_text, reply_markup=buttons)
 
@app.on_callback_query(filters.regex("see_terms"))
async def see_terms(client, callback_query):
    terms_text = "> 📜 **Terms and Conditions** 📜\n\n✨ We are not responsible for user deeds, and we do not promote copyrighted content. \n✨ Authorization and banning of users are at our discretion."
    buttons = InlineKeyboardMarkup([[InlineKeyboardButton("📋 See Plans", callback_data="see_plan")], [InlineKeyboardButton("💬 Contact Now", url="https://t.me/kingofpatal")]])
    await callback_query.message.edit_text(terms_text, reply_markup=buttons)


# -------------------------------------------------------------------------------------
# 🚀 ADVANCED SETTINGS MENU (FILTERS, CAPTIONS, BUTTONS)
# -------------------------------------------------------------------------------------
async def get_settings_menu(user_id):
    buttons = [
        [InlineKeyboardButton("📁 Media Filters", callback_data="set_filters"), InlineKeyboardButton("🔒 Security & Limits", callback_data="set_security")],
        [InlineKeyboardButton("📝 Captions & Tags", callback_data="set_captions"), InlineKeyboardButton("🔘 Custom Buttons", callback_data="set_buttons")],
        [InlineKeyboardButton("✖️ Close Settings", callback_data="close_settings")]
    ]
    return "⚙️ **Advanced Settings Menu**\n\nCustomize your extraction and forward behavior:", InlineKeyboardMarkup(buttons)

async def get_filters_menu(user_id):
    data = await mongodb.find_one({"_id": user_id}) or {}
    def state(key, default=True): return "✅" if data.get(key, default) else "❌"
    
    buttons = [
        [InlineKeyboardButton(f"Text {state('f_text', True)}", callback_data="tgl_f_text"), InlineKeyboardButton(f"Doc {state('f_doc', True)}", callback_data="tgl_f_doc"), InlineKeyboardButton(f"Video {state('f_video', True)}", callback_data="tgl_f_video")],
        [InlineKeyboardButton(f"Photo {state('f_photo', True)}", callback_data="tgl_f_photo"), InlineKeyboardButton(f"Audio {state('f_audio', True)}", callback_data="tgl_f_audio"), InlineKeyboardButton(f"Voice {state('f_voice', True)}", callback_data="tgl_f_voice")],
        [InlineKeyboardButton(f"Anim {state('f_anim', True)}", callback_data="tgl_f_anim"), InlineKeyboardButton(f"Sticker {state('f_sticker', True)}", callback_data="tgl_f_sticker"), InlineKeyboardButton(f"Poll {state('f_poll', True)}", callback_data="tgl_f_poll")],
        [InlineKeyboardButton(f"Forward Tag {state('f_fwtag', False)}", callback_data="tgl_f_fwtag")],
        [InlineKeyboardButton("◀️ Back to Main", callback_data="main_settings")]
    ]
    return "📁 **Media Filters**\n\nChoose what type of messages should be extracted:", InlineKeyboardMarkup(buttons)

async def get_security_menu(user_id):
    data = await mongodb.find_one({"_id": user_id}) or {}
    def state(key, default=False): return "✅" if data.get(key, default) else "❌"
    
    buttons = [
        [InlineKeyboardButton(f"Skip Duplicate {state('f_skip_dup')}", callback_data="tgl_f_skip_dup")],
        [InlineKeyboardButton(f"Secure Message (Protect) {state('f_secure')}", callback_data="tgl_f_secure")],
        [InlineKeyboardButton("✂️ Size Limit", callback_data="input_size_limit"), InlineKeyboardButton("🔑 Keywords", callback_data="input_keywords")],
        [InlineKeyboardButton("📝 Allowed Exts", callback_data="input_ext")],
        [InlineKeyboardButton("◀️ Back to Main", callback_data="main_settings")]
    ]
    return "🔒 **Security & Limits**\n\nConfigure extraction limits and protection:", InlineKeyboardMarkup(buttons)

@app.on_message(filters.command("settings") & filters.private)
async def settings_command(client, message):
    text, markup = await get_settings_menu(message.chat.id)
    await message.reply(text, reply_markup=markup)

@app.on_callback_query(filters.regex(r"^tgl_(.*)"))
async def toggle_setting(client, query):
    user_id = query.from_user.id
    key = query.data.replace("tgl_", "")
    default_state = False if key in ['f_fwtag', 'f_skip_dup', 'f_secure'] else True
    
    data = await mongodb.find_one({"_id": user_id}) or {}
    current_state = data.get(key, default_state)
    await mongodb.update_one({"_id": user_id}, {"$set": {key: not current_state}}, upsert=True)
    
    if key in ['f_skip_dup', 'f_secure']: text, markup = await get_security_menu(user_id)
    else: text, markup = await get_filters_menu(user_id)
    await query.message.edit_text(text, reply_markup=markup)

@app.on_callback_query(filters.regex(r"^set_filters$"))
async def cb_set_filters(client, query):
    text, markup = await get_filters_menu(query.from_user.id)
    await query.message.edit_text(text, reply_markup=markup)

@app.on_callback_query(filters.regex(r"^set_security$"))
async def cb_set_security(client, query):
    text, markup = await get_security_menu(query.from_user.id)
    await query.message.edit_text(text, reply_markup=markup)

@app.on_callback_query(filters.regex(r"^main_settings$"))
async def cb_main_settings(client, query):
    text, markup = await get_settings_menu(query.from_user.id)
    await query.message.edit_text(text, reply_markup=markup)

@app.on_callback_query(filters.regex(r"^close_settings$"))
async def cb_close_settings(client, query):
    await query.message.delete()

# --- INPUT HANDLERS (CAPTION, BUTTONS, LIMITS) ---
@app.on_callback_query(filters.regex(r"^set_captions$"))
async def cb_set_captions(client, query):
    await query.message.delete()
    try:
        cap_msg = await app.ask(query.from_user.id, "📝 **Dynamic Custom Caption**\n\nUse these placeholders:\n`{filename}` - Original File Name\n`{size}` - File Size\n`{caption}` - Original Caption\n\nSend your custom caption layout or type `/cancel`:", timeout=120)
        if cap_msg.text and cap_msg.text != '/cancel':
            await mongodb.update_one({"_id": query.from_user.id}, {"$set": {"custom_caption": cap_msg.text}}, upsert=True)
            await app.send_message(query.from_user.id, "✅ **Custom Caption Saved Successfully!**")
    except: pass

@app.on_callback_query(filters.regex(r"^set_buttons$"))
async def cb_set_buttons(client, query):
    await query.message.delete()
    try:
        btn_msg = await app.ask(query.from_user.id, "🔘 **Custom Inline Buttons**\n\n**Format Single Button:**\n`[Button Name][buttonurl:https://t.me/link]`\n\n**Format Same Row:**\n`[Btn 1][buttonurl:link] [Btn 2][buttonurl:link(:same)]`\n\nSend your button format or type `/cancel`:", timeout=120)
        if btn_msg.text and btn_msg.text != '/cancel':
            await mongodb.update_one({"_id": query.from_user.id}, {"$set": {"custom_buttons": btn_msg.text}}, upsert=True)
            await app.send_message(query.from_user.id, "✅ **Custom Buttons Saved Successfully!**")
    except: pass

@app.on_callback_query(filters.regex(r"^input_size_limit$"))
async def cb_size_limit(client, query):
    await query.message.delete()
    try:
        size_msg = await app.ask(query.from_user.id, "✂️ **Set Max Size Limit**\n\nType the size in MB (e.g., `500` for 500MB). Type `0` to disable limit. \n\nSend size or `/cancel`:", timeout=120)
        if size_msg.text and size_msg.text.isdigit():
            await mongodb.update_one({"_id": query.from_user.id}, {"$set": {"f_size_limit": int(size_msg.text)}}, upsert=True)
            await app.send_message(query.from_user.id, f"✅ **Size Limit set to {size_msg.text} MB!**")
    except: pass
