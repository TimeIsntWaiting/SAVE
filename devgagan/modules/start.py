# ---------------------------------------------------
# File Name: start.py
# Description: A Pyrogram bot for downloading files from Telegram channels or groups 
#              and uploading them back to Telegram.
# Author: Gagan
# GitHub: https://github.com/devgaganin/
# Telegram: https://t.me/team_spy_pro
# YouTube: https://youtube.com/@dev_gagan
# Version: 2.0.5
# License: MIT License
# ---------------------------------------------------

from pyrogram import filters, Client
from devgagan import app
from config import OWNER_ID
from devgagan.core.func import subscribe
import asyncio
from devgagan.core.func import *
from pyrogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, BotCommand
from pyrogram.raw.functions.bots import SetBotInfo
from pyrogram.raw.types import InputUserSelf

# ---------------------------------------------------
# 🚀 PREMIUM DASHBOARD UI (/start)
# ---------------------------------------------------
@app.on_message(filters.command("start") & filters.private)
async def start_command(client, message):
    join = await subscribe(client, message)
    if join == 1:
        return

    user = message.from_user
    
    # Dashboard Text
    dashboard_text = (
        f"👋 **Hello {user.first_name}! Main hu tumhara Advanced Smart Scraper & Clone Bot 🤖**\n\n"
        "Main kisi bhi Telegram Channel ya Group ka data (Photos, Videos, Documents) bypass karke fast aur organized way me clone kar sakta hu. "
        "Chaahe normal channel ho ya **Forum Topics**, main sab handle kar lunga!\n\n"
        "💡 **Naye ho?** Niche diye gaye '❓ Help' button par click karo commands samajhne ke liye.\n\n"
        "━━━━━━━━━━━━━━━━━━━━━\n"
        "⚡ **Active Tasks:** `0` | **Queue:** `0`\n"
        "🤖 **Worker Bots:** `1` Active\n"
        "⏱ **Uptime:** `Live`\n"
        "━━━━━━━━━━━━━━━━━━━━━\n"
        "📂 **Target:** `Check in Settings`\n"
        "🛠 **Mode:** `Premium Scraper`\n"
        "🛡️ **Status:** `Active`\n"
    )

    # Interactive Dashboard Buttons
    buttons = InlineKeyboardMarkup([
        [InlineKeyboardButton("🎯 Smart Topic Clone", callback_data="dash_clone"),
         InlineKeyboardButton("🔄 Batch / Resume", callback_data="dash_batch")],
        [InlineKeyboardButton("🤖 Manage Session", callback_data="dash_session"),
         InlineKeyboardButton("📂 Target Destination", callback_data="dash_target")],
        [InlineKeyboardButton("⚙️ Advanced Settings", callback_data="dash_settings")],
        [InlineKeyboardButton("❓ Help & Commands", callback_data="open_help_menu")]
    ])

    # Try sending with image, fallback to text if image not found
    try:
        await message.reply_photo(
            photo="settings.jpg",  # Make sure settings.jpg is in your bot's root folder
            caption=dashboard_text,
            reply_markup=buttons
        )
    except Exception:
        await message.reply_text(
            text=dashboard_text,
            reply_markup=buttons
        )

# Dashboard Button Callbacks (Pop-up alerts for quick info)
@app.on_callback_query(filters.regex(r"^dash_"))
async def dashboard_callbacks(client, query: CallbackQuery):
    data = query.data
    if data == "dash_clone":
        await query.answer("🎯 Use Command: /clone <link>\n\nSend any message link from a Group/Channel to start cloning Topics!", show_alert=True)
    elif data == "dash_batch":
        await query.answer("🔄 Use Command: /batch\n\nAllows you to extract multiple links in a specific range.", show_alert=True)
    elif data == "dash_session":
        await query.answer("🤖 Use Command: /login\n\nLog in via string session to bypass restrictions and boost speed.", show_alert=True)
    elif data == "dash_target":
        await query.answer("📂 Use Command: /settings\n\nGo to settings and set your target chat ID using SETCHATID.", show_alert=True)
    elif data == "dash_settings":
        await query.answer("⚙️ Use Command: /settings\n\nCustomize Rename tags, Captions, and upload methods.", show_alert=True)

@app.on_callback_query(filters.regex("open_help_menu"))
async def open_help(client, query: CallbackQuery):
    await send_or_edit_help_page(client, query.message, 0)
    await query.answer()

# ---------------------------------------------------
# ⚙️ SET COMMANDS
# ---------------------------------------------------
@app.on_message(filters.command("set"))
async def set(_, message):
    if message.from_user.id not in OWNER_ID:
        await message.reply("You are not authorized to use this command.")
        return
     
    await app.set_bot_commands([
        BotCommand("start", "🚀 Start the bot"),
        BotCommand("clone", "🎯 Smart Clone & Forum Topics"), # Added Clone here
        BotCommand("batch", "🫠 Extract in bulk"),
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
        BotCommand("cancel", "🚫 Cancel batch process")
    ])
 
    await message.reply("✅ Commands configured successfully!")

# ---------------------------------------------------
# ❓ HELP MENU & PAGINATION
# ---------------------------------------------------
help_pages = [
    (
        "📝 **Bot Commands Overview (1/2)**:\n\n"
        "1. **/clone link** 🌟 (NEW)\n"
        "> Smart Scraper for Channels & Forum Topics\n\n"
        "2. **/add userID**\n"
        "> Add user to premium (Owner only)\n\n"
        "3. **/rem userID**\n"
        "> Remove user from premium (Owner only)\n\n"
        "4. **/transfer userID**\n"
        "> Transfer premium to your beloved (Premium members only)\n\n"
        "5. **/get**\n"
        "> Get all user IDs (Owner only)\n\n"
        "6. **/lock**\n"
        "> Lock channel from extraction (Owner only)\n\n"
        "7. **/dl link**\n"
        "> Download videos (Not available in v3 if you are using)\n\n"
        "8. **/adl link**\n"
        "> Download audio (Not available in v3 if you are using)\n\n"
        "9. **/login**\n"
        "> Log into the bot for private channel access\n\n"
        "10. **/batch**\n"
        "> Bulk extraction for posts (After login)\n\n"
    ),
    (
        "📝 **Bot Commands Overview (2/2)**:\n\n"
        "11. **/logout**\n"
        "> Logout from the bot\n\n"
        "12. **/stats**\n"
        "> Get bot stats\n\n"
        "13. **/plan**\n"
        "> Check premium plans\n\n"
        "14. **/speedtest**\n"
        "> Test the server speed\n\n"
        "15. **/terms**\n"
        "> Terms and conditions\n\n"
        "16. **/cancel**\n"
        "> Cancel ongoing batch/clone process\n\n"
        "17. **/myplan**\n"
        "> Get details about your plans\n\n"
        "18. **/session**\n"
        "> Generate Pyrogram V2 session\n\n"
        "19. **/settings**\n"
        "> 1. SETCHATID : To directly upload in channel/group\n"
        "> 2. SETRENAME : To add custom rename tag\n"
        "> 3. CAPTION : To add custom caption\n"
        "> 4. REPLACEWORDS : Can be used for words replacement\n"
        "> 5. RESET : To set the things back to default\n\n"
        "> You can set CUSTOM THUMBNAIL, PDF WATERMARK, VIDEO WATERMARK, SESSION-based login, etc. from settings\n\n"
        "**__Powered by Team SPY__**"
    )
]

async def send_or_edit_help_page(_, message, page_number):
    if page_number < 0 or page_number >= len(help_pages):
        return
     
    prev_button = InlineKeyboardButton("◀️ Previous", callback_data=f"help_prev_{page_number}")
    next_button = InlineKeyboardButton("Next ▶️", callback_data=f"help_next_{page_number}")
     
    buttons = []
    if page_number > 0:
        buttons.append(prev_button)
    if page_number < len(help_pages) - 1:
        buttons.append(next_button)
     
    keyboard = InlineKeyboardMarkup([buttons])
     
    # If it's a callback query message editing, handle it safely
    try:
        if message.photo:
            await message.delete()
            await message.reply(help_pages[page_number], reply_markup=keyboard)
        else:
            await message.edit_text(help_pages[page_number], reply_markup=keyboard)
    except:
        await message.reply(help_pages[page_number], reply_markup=keyboard)

@app.on_message(filters.command("help"))
async def help(client, message):
    join = await subscribe(client, message)
    if join == 1:
        return
    
    # Try to delete original command message if possible
    try: await message.delete() 
    except: pass
    
    msg = await message.reply("Loading Help Menu...")
    await send_or_edit_help_page(client, msg, 0)

@app.on_callback_query(filters.regex(r"help_(prev|next)_(\d+)"))
async def on_help_navigation(client, callback_query):
    action, page_number = callback_query.data.split("_")[1], int(callback_query.data.split("_")[2])
 
    if action == "prev":
        page_number -= 1
    elif action == "next":
        page_number += 1
     
    await send_or_edit_help_page(client, callback_query.message, page_number)
    await callback_query.answer()
 
# ---------------------------------------------------
# 📜 TERMS & PLANS
# ---------------------------------------------------
@app.on_message(filters.command("terms") & filters.private)
async def terms(client, message):
    terms_text = (
        "> 📜 **Terms and Conditions** 📜\n\n"
        "✨ We are not responsible for user deeds, and we do not promote copyrighted content. If any user engages in such activities, it is solely their responsibility.\n"
        "✨ Upon purchase, we do not guarantee the uptime, downtime, or the validity of the plan. __Authorization and banning of users are at our discretion; we reserve the right to ban or authorize users at any time.__\n"
        "✨ Payment to us **__does not guarantee__** authorization for the /batch command. All decisions regarding authorization are made at our discretion and mood.\n"
    )
     
    buttons = InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("📋 See Plans", callback_data="see_plan")],
            [InlineKeyboardButton("💬 Contact Now", url="https://t.me/kingofpatal")],
        ]
    )
    await message.reply_text(terms_text, reply_markup=buttons)
 
@app.on_message(filters.command("plan") & filters.private)
async def plan(client, message):
    plan_text = (
        "> 💰 **Premium Price**:\n\n Starting from $2 or 200 INR accepted via **__Amazon Gift Card__** (terms and conditions apply).\n"
        "📥 **Download Limit**: Users can download up to 100,000 files in a single batch command.\n"
        "🛑 **Batch**: You will get two modes /bulk and /batch.\n"
        "   - Users are advised to wait for the process to automatically cancel before proceeding with any downloads or uploads.\n\n"
        "📜 **Terms and Conditions**: For further details and complete terms and conditions, please send /terms.\n"
    )
     
    buttons = InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("📜 See Terms", callback_data="see_terms")],
            [InlineKeyboardButton("💬 Contact Now", url="https://t.me/kingofpatal")],
        ]
    )
    await message.reply_text(plan_text, reply_markup=buttons)
 
@app.on_callback_query(filters.regex("see_plan"))
async def see_plan(client, callback_query):
    plan_text = (
        "> 💰**Premium Price**\n\n Starting from $2 or 200 INR accepted via **__Amazon Gift Card__** (terms and conditions apply).\n"
        "📥 **Download Limit**: Users can download up to 100,000 files in a single batch command.\n"
        "🛑 **Batch**: You will get two modes /bulk and /batch.\n"
        "   - Users are advised to wait for the process to automatically cancel before proceeding with any downloads or uploads.\n\n"
        "📜 **Terms and Conditions**: For further details and complete terms and conditions, please send /terms or click See Terms👇\n"
    )
     
    buttons = InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("📜 See Terms", callback_data="see_terms")],
            [InlineKeyboardButton("💬 Contact Now", url="https://t.me/kingofpatal")],
        ]
    )
    await callback_query.message.edit_text(plan_text, reply_markup=buttons)
 
@app.on_callback_query(filters.regex("see_terms"))
async def see_terms(client, callback_query):
    terms_text = (
        "> 📜 **Terms and Conditions** 📜\n\n"
        "✨ We are not responsible for user deeds, and we do not promote copyrighted content. If any user engages in such activities, it is solely their responsibility.\n"
        "✨ Upon purchase, we do not guarantee the uptime, downtime, or the validity of the plan. __Authorization and banning of users are at our discretion; we reserve the right to ban or authorize users at any time.__\n"
        "✨ Payment to us **__does not guarantee__** authorization for the /batch command. All decisions regarding authorization are made at our discretion and mood.\n"
    )
     
    buttons = InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("📋 See Plans", callback_data="see_plan")],
            [InlineKeyboardButton("💬 Contact Now", url="https://t.me/kingofpatal")],
        ]
    )
    await callback_query.message.edit_text(terms_text, reply_markup=buttons)
