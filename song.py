# ===================== PYTHON 3.14 EVENT LOOP FIX =====================
import asyncio
import sys

# Fix for RuntimeError: There is no current event loop in thread 'MainThread'
if sys.version_info >= (3, 14):
    try:
        asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

# Optional speedups
try:
    import uvloop
    uvloop.install()
except ImportError:
    pass
# =======================================================================

# ==========================================================
#   PRO PLAYER ULTIMATE MUSIC BOT
#   Author: @proplayerhuladle
#   Version: 3.1 (VPS Ready)
# ==========================================================

import os
import json
import logging
import time
import math
import re
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from threading import Lock

from pyrogram import Client, filters, enums
from pyrogram.enums import ChatMemberStatus, ChatType, ParseMode
from pyrogram.types import (
    Message, InlineKeyboardMarkup, InlineKeyboardButton, 
    CallbackQuery, ChatMemberUpdated, InputMediaPhoto
)
from pyrogram.errors import ChatAdminRequired, UserNotParticipant

from pytgcalls import PyTgCalls
from pytgcalls.types.input_stream import InputStream
from pytgcalls.types.stream import StreamAudioEnded
from pytgcalls.exceptions import NoActiveGroupCall, AlreadyJoinedError

from yt_dlp import YoutubeDL
import requests
from PIL import Image, ImageDraw, ImageFont
from io import BytesIO

# ... rest of your existing code continues

import os
import json
import asyncio
import logging
import time
import math
import re
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from threading import Lock

from pyrogram import Client, filters, enums
from pyrogram.enums import ChatMemberStatus, ChatType, ParseMode
from pyrogram.types import (
    Message, InlineKeyboardMarkup, InlineKeyboardButton, 
    CallbackQuery, ChatMemberUpdated, InputMediaPhoto
)
from pyrogram.errors import ChatAdminRequired, UserNotParticipant

# 🔥 FIXED IMPORTS FOR VPS (py-tgcalls 2.2.11)
from pytgcalls import PyTgCalls
from pytgcalls.types.input_stream import InputStream
from pytgcalls.types.stream import StreamAudioEnded
from pytgcalls.exceptions import NoActiveGroupCall, AlreadyJoinedError

from yt_dlp import YoutubeDL
import requests
from PIL import Image, ImageDraw, ImageFont
from io import BytesIO

# ===================== CONFIG =====================

# 🔑 Add your credentials here
API_ID = int(os.getenv("API_ID"))            
API_HASH = os.getenv("API_HASH")   # <-- ADD YOUR API HASH
BOT_TOKEN = os.getenv("BOT_TOKEN") # <-- ADD YOUR BOT TOKEN

OWNER_ID = 8598847348         # <-- YOUR USER ID
OWNER_USERNAME = "proplayerhuladle"
BOT_USERNAME = "Muiscbotbyme_bot"  # <-- WITHOUT @

DATA_FILE = "pro_music_data.json"
LOG_FILE = "bot_logs.txt"

# ===================== LOGGING =====================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler()
    ]
)
log = logging.getLogger("ProMusicBot")

# ===================== CLIENT =====================

app = Client(
    "pro_music_bot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN
)

call = PyTgCalls(app)

# ===================== DATABASE =====================

DEFAULT_DB = {
    "approved_groups": {},      # gid: {"approved": true, "active": true, "name": "..."}
    "userplay": {},             # gid: true/false (user play permission)
    "queues": {},               # gid: [{"url": "", "title": "", "by": "", "duration": "", "thumbnail": ""}]
    "active_vc": {},            # gid: true/false
    "groups": [],               # list of approved group ids
    "stats": {
        "total_songs_played": 0,
        "total_commands": 0,
        "start_time": 0
    }
}

if not os.path.exists(DATA_FILE):
    with open(DATA_FILE, "w") as f:
        json.dump(DEFAULT_DB, f, indent=2)

def load_db():
    try:
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    except:
        return DEFAULT_DB.copy()

def save_db(db):
    try:
        with open(DATA_FILE, "w") as f:
            json.dump(db, f, indent=2)
    except Exception as e:
        log.error(f"Save error: {e}")

# Cache for admin status
admin_cache = {}
admin_cache_lock = Lock()
ADMIN_CACHE_TTL = 300  # 5 minutes

# ===================== UTILS =====================

async def is_admin(chat_id: int, user_id: int) -> bool:
    """Check if user is admin with caching"""
    cache_key = f"{chat_id}:{user_id}"
    current_time = time.time()
    
    # Check cache
    with admin_cache_lock:
        if cache_key in admin_cache:
            cached_time, cached_status = admin_cache[cache_key]
            if current_time - cached_time < ADMIN_CACHE_TTL:
                return cached_status
    
    # Check from Telegram
    try:
        member = await app.get_chat_member(chat_id, user_id)
        status = member.status in [ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER]
        
        # Update cache
        with admin_cache_lock:
            admin_cache[cache_key] = (current_time, status)
        
        return status
    except:
        return False

def get_readable_time(seconds: int) -> str:
    """Convert seconds to readable format"""
    if seconds < 60:
        return f"{seconds}s"
    minutes = seconds // 60
    hours = minutes // 60
    days = hours // 24
    
    if days > 0:
        return f"{days}d {hours % 24}h"
    if hours > 0:
        return f"{hours}h {minutes % 60}m"
    return f"{minutes}m {seconds % 60}s"

def format_duration(seconds: int) -> str:
    """Format duration for display"""
    minutes = seconds // 60
    seconds = seconds % 60
    return f"{minutes:02d}:{seconds:02d}"

def now():
    return int(time.time())

# ===================== YOUTUBE =====================

YDL_OPTS = {
    "format": "bestaudio/best",
    "quiet": True,
    "no_warnings": True,
    "nocheckcertificate": True,
    "extract_flat": False,
    "ignoreerrors": True,
    "logtostderr": False
}

def fetch_audio(query: str) -> Dict:
    """Fetch audio info from YouTube"""
    try:
        with YoutubeDL(YDL_OPTS) as ydl:
            # Check if it's a URL or search query
            if not query.startswith(('http://', 'https://', 'www.')):
                query = f"ytsearch1:{query}"
            
            info = ydl.extract_info(query, download=False)
            
            if "entries" in info:
                info = info["entries"][0]
            
            # Get thumbnail
            thumbnail = info.get("thumbnail", "")
            
            # Get duration
            duration = info.get("duration", 0)
            
            return {
                "url": info["url"],
                "title": info["title"],
                "duration": duration,
                "thumbnail": thumbnail,
                "webpage_url": info.get("webpage_url", f"https://youtube.com/watch?v={info.get('id', '')}")
            }
    except Exception as e:
        log.error(f"YoutubeDL error: {e}")
        return None

def fetch_playlist(query: str) -> List[Dict]:
    """Fetch all songs from a playlist"""
    try:
        with YoutubeDL(YDL_OPTS) as ydl:
            info = ydl.extract_info(query, download=False)
            
            if "entries" in info:
                songs = []
                for entry in info["entries"]:
                    if entry:
                        songs.append({
                            "url": entry["url"],
                            "title": entry["title"],
                            "duration": entry.get("duration", 0),
                            "thumbnail": entry.get("thumbnail", ""),
                            "webpage_url": entry.get("webpage_url", "")
                        })
                return songs
            else:
                return [{
                    "url": info["url"],
                    "title": info["title"],
                    "duration": info.get("duration", 0),
                    "thumbnail": info.get("thumbnail", ""),
                    "webpage_url": info.get("webpage_url", "")
                }]
    except Exception as e:
        log.error(f"Playlist fetch error: {e}")
        return []

def get_lyrics(song_name: str) -> Optional[str]:
    """Fetch lyrics for a song"""
    try:
        # Using a simple API
        url = f"https://some-lyrics-api.com/search?q={song_name}"
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            data = response.json()
            return data.get("lyrics", "Lyrics not found")
        return None
    except:
        return None

def generate_thumbnail(title: str, duration: str) -> str:
    """Generate a thumbnail image"""
    try:
        img = Image.new('RGB', (800, 400), color=(40, 40, 40))
        draw = ImageDraw.Draw(img)
        
        # Try to use a font, fallback to default
        try:
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 40)
            small_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 20)
        except:
            try:
                font = ImageFont.truetype("arial.ttf", 40)
                small_font = ImageFont.truetype("arial.ttf", 20)
            except:
                font = ImageFont.load_default()
                small_font = ImageFont.load_default()
        
        # Draw text
        draw.text((50, 150), title[:50], fill=(255, 255, 255), font=font)
        draw.text((50, 220), f"Duration: {duration}", fill=(200, 200, 200), font=small_font)
        draw.text((50, 260), "Now Playing on Pro Player Music Bot", fill=(100, 200, 255), font=small_font)
        
        # Save to bytes
        img_bytes = BytesIO()
        img.save(img_bytes, format='PNG')
        img_bytes.seek(0)
        
        return img_bytes
    except Exception as e:
        log.error(f"Thumbnail error: {e}")
        return None

# ===================== HELP =====================

HELP_TEXT = """
🎧 **PRO PLAYER MUSIC BOT - HELP** 🎧

**🎵 MUSIC COMMANDS**
• `/play <song name/URL>` - Play a song
• `/playlist <URL>` - Play a YouTube playlist
• `/skip` - Skip current song
• `/pause` - Pause current song
• `/resume` - Resume paused song
• `/stop` - Stop playing and clear queue
• `/queue` - Show current queue
• `/current` - Show current playing song
• `/lyrics <song name>` - Get song lyrics
• `/download <song name>` - Download song

**👑 ADMIN COMMANDS**
• `/userplay on/off` - Allow users to play songs
• `/clean` - Clear the queue
• `/leave` - Leave voice chat
• `/ping` - Check bot status
• `/uptime` - Bot uptime

**⚙️ OWNER COMMANDS (Only YOU)**
• `/stop_group 123456789` - Stop bot in specific group
• `/on_group 123456789` - Start bot in specific group
• `/stop_all` - Stop bot in all groups
• `/on_all` - Start bot in all groups
• `/admin` - Open admin panel
• `/broadcast <message>` - Send message to all groups
• `/stats` - Bot statistics

**📌 FEATURES**
✅ Auto VC join/leave
✅ Queue management
✅ Playlist support
✅ Lyrics & download
✅ Beautiful UI
✅ Admin approval system

**👑 Owner:** @proplayerhuladle
"""

# ===================== BOT ADDED =====================

@app.on_chat_member_updated()
async def bot_added(_, upd: ChatMemberUpdated):
    """When bot is added to a group"""
    if upd.new_chat_member and upd.new_chat_member.user.is_bot:
        gid = str(upd.chat.id)
        group_name = upd.chat.title
        
        # Send approval request to owner
        await app.send_message(
            OWNER_ID,
            f"🚨 **Bot Added to New Group**\n\n"
            f"🏷 **Name:** {group_name}\n"
            f"🆔 **ID:** `{gid}`\n"
            f"👥 **Members:** {upd.chat.members_count}\n\n"
            f"Approve or reject this group?",
            reply_markup=InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("✅ Approve", callback_data=f"approve_{gid}"),
                    InlineKeyboardButton("❌ Reject", callback_data=f"reject_{gid}")
                ],
                [InlineKeyboardButton("📋 Group Info", callback_data=f"info_{gid}")]
            ]),
            parse_mode=enums.ParseMode.MARKDOWN
        )
        
        log.info(f"Bot added to group: {group_name} ({gid})")

# ===================== CALLBACKS =====================

@app.on_callback_query()
async def handle_callbacks(_, q: CallbackQuery):
    """Handle all callback queries"""
    db = load_db()
    
    # Only owner can use callbacks
    if q.from_user.id != OWNER_ID:
        await q.answer("❌ Only owner can use this!", show_alert=True)
        return
    
    data = q.data
    
    # Group approval
    if data.startswith("approve_"):
        gid = data.split("_")[1]
        db["approved_groups"][gid] = {
            "approved": True,
            "active": True,
            "name": q.message.text.split("Name:")[1].split("\n")[0].strip() if "Name:" in q.message.text else "Unknown"
        }
        if gid not in db["groups"]:
            db["groups"].append(gid)
        save_db(db)
        
        await q.message.edit("✅ **Group Approved Successfully!**\n\nBot will now work in this group.")
        await q.answer("✅ Group approved!", show_alert=True)
        
        # Send welcome message to group
        try:
            await app.send_message(
                int(gid),
                f"🎵 **Bot Activated!**\n\n"
                f"Thanks for adding me! I'm now ready to play music.\n"
                f"Use /help to see all commands.\n\n"
                f"**Owner:** @{OWNER_USERNAME}"
            )
        except:
            pass
    
    # Group rejection
    elif data.startswith("reject_"):
        gid = data.split("_")[1]
        
        await q.message.edit("❌ **Group Rejected**\n\nBot will leave this group.")
        await q.answer("❌ Group rejected!", show_alert=True)
        
        # Leave group
        try:
            await call.leave_group_call(int(gid))
        except:
            pass
        
        try:
            await app.leave_chat(int(gid))
        except:
            pass
        
        # Send rejection message
        try:
            await app.send_message(
                int(gid),
                f"❌ **Bot Rejected**\n\n"
                f"This group is not authorized to use this bot.\n"
                f"Please contact @{OWNER_USERNAME} for approval."
            )
        except:
            pass
    
    # Group info
    elif data.startswith("info_"):
        gid = data.split("_")[1]
        try:
            chat = await app.get_chat(int(gid))
            text = f"📋 **Group Info**\n\n"
            text += f"**Name:** {chat.title}\n"
            text += f"**ID:** `{chat.id}`\n"
            text += f"**Members:** {chat.members_count}\n"
            text += f"**Type:** {chat.type}\n"
            text += f"**Username:** @{chat.username}" if chat.username else "**Username:** None"
            
            await q.message.edit(text)
        except:
            await q.answer("Failed to get group info", show_alert=True)
    
    # Admin panel buttons
    elif data == "admin_refresh":
        await show_admin_panel(q.message, db)
        await q.answer("Refreshed!")
    
    elif data == "admin_stop_all":
        for gid in db["groups"]:
            if gid in db["approved_groups"]:
                db["approved_groups"][gid]["active"] = False
        save_db(db)
        await q.message.edit("⏹️ **All groups stopped!**\n\nUse /on_all to start again.")
        await q.answer("All groups stopped!")
    
    elif data == "admin_start_all":
        for gid in db["groups"]:
            if gid in db["approved_groups"]:
                db["approved_groups"][gid]["active"] = True
        save_db(db)
        await q.message.edit("▶️ **All groups started!**")
        await q.answer("All groups started!")
    
    elif data == "admin_stats":
        stats = db.get("stats", {})
        uptime = get_readable_time(now() - stats.get("start_time", now()))
        text = f"📊 **Bot Statistics**\n\n"
        text += f"**Total Groups:** {len(db['groups'])}\n"
        text += f"**Active Groups:** {sum(1 for g in db['approved_groups'].values() if g.get('active', False))}\n"
        text += f"**Songs Played:** {stats.get('total_songs_played', 0)}\n"
        text += f"**Commands Used:** {stats.get('total_commands', 0)}\n"
        text += f"**Uptime:** {uptime}\n"
        text += f"**Start Time:** {datetime.fromtimestamp(stats.get('start_time', now())).strftime('%Y-%m-%d %H:%M:%S')}"
        
        await q.message.edit(text, reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 Back", callback_data="admin_back")]
        ]))
    
    elif data == "admin_back":
        await show_admin_panel(q.message, db)
    
    elif data.startswith("stop_group_"):
        gid = data.split("_")[2]
        if gid in db["approved_groups"]:
            db["approved_groups"][gid]["active"] = False
            save_db(db)
            await q.answer(f"Group {gid} stopped!")
            await show_admin_panel(q.message, db)
    
    elif data.startswith("start_group_"):
        gid = data.split("_")[2]
        if gid in db["approved_groups"]:
            db["approved_groups"][gid]["active"] = True
            save_db(db)
            await q.answer(f"Group {gid} started!")
            await show_admin_panel(q.message, db)

async def show_admin_panel(message, db):
    """Show admin panel with buttons"""
    total = len(db["groups"])
    active = sum(1 for g in db["approved_groups"].values() if g.get("active", False))
    stopped = total - active
    
    # Create group buttons (max 5 per row)
    group_buttons = []
    for i, gid in enumerate(db["groups"][:10]):  # Show first 10 groups
        group = db["approved_groups"].get(gid, {})
        name = group.get("name", "Unknown")[:15]
        status = "✅" if group.get("active", False) else "❌"
        
        group_buttons.append([
            InlineKeyboardButton(
                f"{status} {name}",
                callback_data=f"stop_group_{gid}" if group.get("active") else f"start_group_{gid}"
            )
        ])
    
    # Main panel buttons
    buttons = [
        [
            InlineKeyboardButton("⏹️ Stop All", callback_data="admin_stop_all"),
            InlineKeyboardButton("▶️ Start All", callback_data="admin_start_all")
        ],
        [
            InlineKeyboardButton("📊 Stats", callback_data="admin_stats"),
            InlineKeyboardButton("🔄 Refresh", callback_data="admin_refresh")
        ]
    ]
    
    # Add group buttons if any
    if group_buttons:
        buttons.extend(group_buttons)
    
    text = f"👑 **ADMIN PANEL** 👑\n\n"
    text += f"**Total Groups:** {total}\n"
    text += f"**✅ Active:** {active}\n"
    text += f"**❌ Stopped:** {stopped}\n\n"
    text += f"Click on group buttons to toggle status:\n"
    text += f"• ✅ = Active\n"
    text += f"• ❌ = Stopped\n\n"
    text += f"**Owner:** @{OWNER_USERNAME}"
    
    await message.edit(text, reply_markup=InlineKeyboardMarkup(buttons))

# ===================== DM HANDLER =====================

@app.on_message(filters.private & ~filters.user(OWNER_ID))
async def dm_block(_, m: Message):
    """Block non-owner DMs"""
    await m.reply(
        f"🚫 **This bot works only in groups!**\n\n"
        f"To use this bot, add it to your group and ask for approval.\n\n"
        f"**Contact owner:** @{OWNER_USERNAME}"
    )

# ===================== START/HELP =====================

@app.on_message(filters.command("start"))
async def start_cmd(_, m: Message):
    """Start command"""
    if m.chat.type == ChatType.PRIVATE and m.from_user.id != OWNER_ID:
        return
    
    await m.reply(
        f"🎵 **Pro Player Music Bot** 🎵\n\n"
        f"Hi {m.from_user.mention}! I'm a powerful music bot with advanced features.\n\n"
        f"**Features:**\n"
        f"• Play songs from YouTube\n"
        f"• Playlist support\n"
        f"• Queue management\n"
        f"• Lyrics & download\n"
        f"• Admin controls\n\n"
        f"Use /help to see all commands.\n\n"
        f"**Owner:** @{OWNER_USERNAME}",
        parse_mode=enums.ParseMode.MARKDOWN
    )

@app.on_message(filters.command("help"))
async def help_cmd(_, m: Message):
    """Help command"""
    if m.chat.type == ChatType.PRIVATE and m.from_user.id != OWNER_ID:
        return
    
    await m.reply(HELP_TEXT, parse_mode=enums.ParseMode.MARKDOWN)

# ===================== ADMIN PANEL =====================

@app.on_message(filters.command("admin") & filters.user(OWNER_ID))
async def admin_panel(_, m: Message):
    """Admin panel command"""
    db = load_db()
    
    # Update start time if not set
    if "stats" not in db:
        db["stats"] = {"start_time": now(), "total_songs_played": 0, "total_commands": 0}
    if db["stats"].get("start_time", 0) == 0:
        db["stats"]["start_time"] = now()
    save_db(db)
    
    await show_admin_panel(m, db)

# ===================== GROUP CONTROL =====================

@app.on_message(filters.command("stop_group") & filters.user(OWNER_ID))
async def stop_group(_, m: Message):
    """Stop bot in specific group"""
    if len(m.command) < 2:
        await m.reply("❌ Usage: /stop_group <group_id>")
        return
    
    try:
        gid = m.command[1]
        db = load_db()
        
        if gid in db["approved_groups"]:
            db["approved_groups"][gid]["active"] = False
            save_db(db)
            
            # Leave VC if active
            try:
                await call.leave_group_call(int(gid))
            except:
                pass
            
            await m.reply(f"✅ **Bot stopped in group:** `{gid}`")
            
            # Notify group
            try:
                await app.send_message(
                    int(gid),
                    f"⏹️ **Bot Stopped**\n\n"
                    f"This bot has been stopped by owner.\n"
                    f"Contact @{OWNER_USERNAME} for more info."
                )
            except:
                pass
        else:
            await m.reply("❌ Group not found in database")
    except Exception as e:
        await m.reply(f"❌ Error: {e}")

@app.on_message(filters.command("on_group") & filters.user(OWNER_ID))
async def on_group(_, m: Message):
    """Start bot in specific group"""
    if len(m.command) < 2:
        await m.reply("❌ Usage: /on_group <group_id>")
        return
    
    try:
        gid = m.command[1]
        db = load_db()
        
        if gid in db["approved_groups"]:
            db["approved_groups"][gid]["active"] = True
            save_db(db)
            
            await m.reply(f"✅ **Bot started in group:** `{gid}`")
            
            # Notify group
            try:
                await app.send_message(
                    int(gid),
                    f"▶️ **Bot Activated**\n\n"
                    f"Bot is now active again! Use /help to see commands."
                )
            except:
                pass
        else:
            await m.reply("❌ Group not found in database")
    except Exception as e:
        await m.reply(f"❌ Error: {e}")

@app.on_message(filters.command("stop_all") & filters.user(OWNER_ID))
async def stop_all(_, m: Message):
    """Stop bot in all groups"""
    db = load_db()
    
    for gid in db["approved_groups"]:
        db["approved_groups"][gid]["active"] = False
        try:
            await call.leave_group_call(int(gid))
        except:
            pass
    
    save_db(db)
    await m.reply("⏹️ **Bot stopped in ALL groups**")

@app.on_message(filters.command("on_all") & filters.user(OWNER_ID))
async def on_all(_, m: Message):
    """Start bot in all groups"""
    db = load_db()
    
    for gid in db["approved_groups"]:
        db["approved_groups"][gid]["active"] = True
    
    save_db(db)
    await m.reply("▶️ **Bot started in ALL groups**")

@app.on_message(filters.command("broadcast") & filters.user(OWNER_ID))
async def broadcast(_, m: Message):
    """Broadcast message to all groups"""
    if len(m.command) < 2:
        await m.reply("❌ Usage: /broadcast <message>")
        return
    
    msg = " ".join(m.command[1:])
    db = load_db()
    
    success = 0
    failed = 0
    
    status_msg = await m.reply("📤 **Broadcasting...**")
    
    for gid in db["groups"]:
        try:
            await app.send_message(int(gid), msg)
            success += 1
        except:
            failed += 1
        await asyncio.sleep(0.5)  # Avoid flood
    
    await status_msg.edit(
        f"📊 **Broadcast Complete**\n\n"
        f"✅ Success: {success}\n"
        f"❌ Failed: {failed}\n"
        f"📝 Message: {msg[:50]}..."
    )

@app.on_message(filters.command("stats") & filters.user(OWNER_ID))
async def stats_cmd(_, m: Message):
    """Show bot statistics"""
    db = load_db()
    stats = db.get("stats", {})
    
    uptime = get_readable_time(now() - stats.get("start_time", now()))
    
    text = f"📊 **BOT STATISTICS** 📊\n\n"
    text += f"**Total Groups:** {len(db['groups'])}\n"
    text += f"**Approved Groups:** {len(db['approved_groups'])}\n"
    text += f"**Active Groups:** {sum(1 for g in db['approved_groups'].values() if g.get('active', False))}\n"
    text += f"**VC Active:** {sum(1 for gid, active in db.get('active_vc', {}).items() if active)}\n"
    text += f"\n"
    text += f"**Songs Played:** {stats.get('total_songs_played', 0)}\n"
    text += f"**Commands Used:** {stats.get('total_commands', 0)}\n"
    text += f"**Uptime:** {uptime}\n"
    text += f"\n"
    text += f"**Start Time:** {datetime.fromtimestamp(stats.get('start_time', now())).strftime('%Y-%m-%d %H:%M:%S')}\n"
    
    await m.reply(text, parse_mode=enums.ParseMode.MARKDOWN)

# ===================== PLAY COMMAND =====================

@app.on_message(filters.command("play") & filters.group)
async def play(_, m: Message):
    """Play a song"""
    db = load_db()
    gid = str(m.chat.id)
    
    # Update stats
    db["stats"]["total_commands"] = db["stats"].get("total_commands", 0) + 1
    save_db(db)
    
    # Check if group is approved and active
    if gid not in db["approved_groups"] or not db["approved_groups"][gid].get("approved", False):
        await m.reply(
            f"❌ **This group is not authorized!**\n\n"
            f"Please contact @{OWNER_USERNAME} for approval."
        )
        return
    
    if not db["approved_groups"][gid].get("active", True):
        await m.reply(
            f"⏹️ **Bot is currently stopped in this group**\n\n"
            f"Contact @{OWNER_USERNAME} to activate."
        )
        return
    
    # Check user play permission
    allowed = db["userplay"].get(gid, True)
    if not allowed and not await is_admin(m.chat.id, m.from_user.id):
        await m.reply("🔒 **Only admins can play songs**")
        return
    
    if len(m.command) < 2:
        await m.reply("🎵 **Usage:** `/play <song name or URL>`")
        return
    
    query = " ".join(m.command[1:])
    
    # Send typing status
    await m.chat.send_action(enums.ChatAction.TYPING)
    
    # Fetch audio
    status_msg = await m.reply("🔍 **Searching...**")
    audio = fetch_audio(query)
    
    if not audio:
        await status_msg.edit("❌ **Song not found!**")
        return
    
    # Create queue entry
    queue_item = {
        "url": audio["url"],
        "title": audio["title"],
        "duration": audio["duration"],
        "thumbnail": audio["thumbnail"],
        "webpage_url": audio["webpage_url"],
        "by": m.from_user.first_name,
        "by_id": m.from_user.id,
        "requested_at": now()
    }
    
    # Add to queue
    queue = db["queues"].setdefault(gid, [])
    queue.append(queue_item)
    save_db(db)
    
    # Generate thumbnail
    duration_str = format_duration(audio["duration"])
    thumb_bytes = generate_thumbnail(audio["title"], duration_str)
    
    # Create buttons
    buttons = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("⏸️ Pause", callback_data=f"pause_{gid}"),
            InlineKeyboardButton("▶️ Resume", callback_data=f"resume_{gid}"),
            InlineKeyboardButton("⏭️ Skip", callback_data=f"skip_{gid}")
        ],
        [
            InlineKeyboardButton("📋 Queue", callback_data=f"queue_{gid}"),
            InlineKeyboardButton("⏹️ Stop", callback_data=f"stopvc_{gid}")
        ],
        [
            InlineKeyboardButton("📥 Download", callback_data=f"download_{len(queue)-1}_{gid}"),
            InlineKeyboardButton("📝 Lyrics", callback_data=f"lyrics_{audio['title']}")
        ]
    ])
    
    # If this is the first song in queue, start playing
    if len(queue) == 1:
        try:
            await call.join_group_call(
                m.chat.id,
                InputStream(audio["url"])
            )
            db["active_vc"][gid] = True
            db["stats"]["total_songs_played"] = db["stats"].get("total_songs_played", 0) + 1
            save_db(db)
            
            # Send playing message with thumbnail
            caption = (
                f"▶️ **Now Playing**\n\n"
                f"**🎵 Title:** {audio['title']}\n"
                f"**⏱️ Duration:** {duration_str}\n"
                f"**👤 Requested by:** {m.from_user.mention}\n"
                f"**📊 Position:** 1 in queue"
            )
            
            if thumb_bytes:
                await status_msg.delete()
                await m.reply_photo(
                    photo=thumb_bytes,
                    caption=caption,
                    reply_markup=buttons,
                    parse_mode=enums.ParseMode.MARKDOWN
                )
            else:
                await status_msg.edit(caption, reply_markup=buttons)
                
        except NoActiveGroupCall:
            await status_msg.edit("❌ **No active voice chat found!**\n\nPlease start a voice chat first.")
            queue.pop()
            save_db(db)
        except AlreadyJoinedError:
            # Already in VC, just change stream
            await call.change_stream(
                m.chat.id,
                InputStream(audio["url"])
            )
            await status_msg.edit(f"▶️ **Playing:** {audio['title']}")
        except Exception as e:
            await status_msg.edit(f"❌ **Error:** {str(e)}")
            queue.pop()
            save_db(db)
    else:
        # Added to queue
        await status_msg.edit(
            f"➕ **Added to Queue**\n\n"
            f"**🎵 Title:** {audio['title']}\n"
            f"**⏱️ Duration:** {duration_str}\n"
            f"**👤 Requested by:** {m.from_user.mention}\n"
            f"**📊 Position:** {len(queue)} in queue"
        )

# ===================== PLAYLIST COMMAND =====================

@app.on_message(filters.command("playlist") & filters.group)
async def playlist(_, m: Message):
    """Play a YouTube playlist"""
    db = load_db()
    gid = str(m.chat.id)
    
    # Check permissions (same as play command)
    if gid not in db["approved_groups"] or not db["approved_groups"][gid].get("approved", False):
        return
    
    if not db["approved_groups"][gid].get("active", True):
        return
    
    allowed = db["userplay"].get(gid, True)
    if not allowed and not await is_admin(m.chat.id, m.from_user.id):
        await m.reply("🔒 **Only admins can add playlists**")
        return
    
    if len(m.command) < 2:
        await m.reply("🎵 **Usage:** `/playlist <YouTube playlist URL>`")
        return
    
    url = m.command[1]
    
    status_msg = await m.reply("🔄 **Fetching playlist...**")
    
    # Fetch playlist
    songs = fetch_playlist(url)
    
    if not songs:
        await status_msg.edit("❌ **No songs found in playlist!**")
        return
    
    # Add all songs to queue
    queue = db["queues"].setdefault(gid, [])
    
    added = 0
    for song in songs:
        queue.append({
            "url": song["url"],
            "title": song["title"],
            "duration": song["duration"],
            "thumbnail": song["thumbnail"],
            "webpage_url": song["webpage_url"],
            "by": m.from_user.first_name,
            "by_id": m.from_user.id,
            "requested_at": now()
        })
        added += 1
    
    save_db(db)
    
    # If this was the first song, start playing
    if len(queue) == added:  # Queue was empty before
        try:
            await call.join_group_call(
                m.chat.id,
                InputStream(songs[0]["url"])
            )
            db["active_vc"][gid] = True
            save_db(db)
            
            await status_msg.edit(
                f"✅ **Playlist Added**\n\n"
                f"**📊 Added:** {added} songs\n"
                f"**▶️ Now Playing:** {songs[0]['title']}\n"
                f"**📋 Total Queue:** {len(queue)}"
            )
        except Exception as e:
            await status_msg.edit(f"❌ **Error:** {str(e)}")
    else:
        await status_msg.edit(
            f"✅ **Playlist Added**\n\n"
            f"**📊 Added:** {added} songs to queue\n"
            f"**📋 Total Queue:** {len(queue)}"
        )

# ===================== MUSIC CONTROLS =====================

@app.on_message(filters.command("pause") & filters.group)
async def pause(_, m: Message):
    """Pause current song"""
    if not await is_admin(m.chat.id, m.from_user.id):
        await m.reply("🔒 **Only admins can pause**")
        return
    
    try:
        await call.pause_stream(m.chat.id)
        await m.reply("⏸️ **Paused**")
    except:
        await m.reply("❌ **Nothing is playing**")

@app.on_message(filters.command("resume") & filters.group)
async def resume(_, m: Message):
    """Resume paused song"""
    if not await is_admin(m.chat.id, m.from_user.id):
        await m.reply("🔒 **Only admins can resume**")
        return
    
    try:
        await call.resume_stream(m.chat.id)
        await m.reply("▶️ **Resumed**")
    except:
        await m.reply("❌ **Nothing is paused**")

@app.on_message(filters.command("skip") & filters.group)
async def skip(_, m: Message):
    """Skip current song"""
    if not await is_admin(m.chat.id, m.from_user.id):
        await m.reply("🔒 **Only admins can skip**")
        return
    
    db = load_db()
    gid = str(m.chat.id)
    queue = db["queues"].get(gid, [])
    
    if len(queue) <= 1:
        # No next song
        try:
            await call.leave_group_call(m.chat.id)
            db["active_vc"][gid] = False
            queue.clear()
            save_db(db)
            await m.reply("⏹️ **Stopped and left VC**")
        except:
            await m.reply("❌ **Nothing to skip**")
    else:
        # Skip to next
        queue.pop(0)
        await call.change_stream(
            m.chat.id,
            InputStream(queue[0]["url"])
        )
        save_db(db)
        await m.reply(f"⏭️ **Skipped**\n\n**Now Playing:** {queue[0]['title']}")

@app.on_message(filters.command("stop") & filters.group)
async def stop(_, m: Message):
    """Stop playing and clear queue"""
    if not await is_admin(m.chat.id, m.from_user.id):
        await m.reply("🔒 **Only admins can stop**")
        return
    
    db = load_db()
    gid = str(m.chat.id)
    
    try:
        await call.leave_group_call(m.chat.id)
        db["active_vc"][gid] = False
        db["queues"][gid] = []
        save_db(db)
        await m.reply("⏹️ **Stopped and cleared queue**")
    except:
        await m.reply("❌ **Nothing to stop**")

@app.on_message(filters.command("leave") & filters.group)
async def leave(_, m: Message):
    """Leave voice chat"""
    if not await is_admin(m.chat.id, m.from_user.id):
        await m.reply("🔒 **Only admins can make me leave**")
        return
    
    try:
        await call.leave_group_call(m.chat.id)
        await m.reply("👋 **Left voice chat**")
    except:
        await m.reply("❌ **Not in voice chat**")

@app.on_message(filters.command("queue") & filters.group)
async def show_queue(_, m: Message):
    """Show current queue"""
    db = load_db()
    gid = str(m.chat.id)
    
    queue = db["queues"].get(gid, [])
    
    if not queue:
        await m.reply("📭 **Queue is empty**")
        return
    
    text = f"🎶 **Current Queue** ({len(queue)} songs)\n\n"
    
    total_duration = 0
    for i, song in enumerate(queue, 1):
        duration_str = format_duration(song["duration"])
        total_duration += song["duration"]
        
        if i == 1:
            text += f"**▶️ Now Playing:**\n"
        text += f"{i}. **{song['title']}** ({duration_str})\n"
        text += f"   👤 Requested by: {song['by']}\n\n"
    
    total_duration_str = format_duration(total_duration)
    text += f"**📊 Total Duration:** {total_duration_str}"
    
    await m.reply(text, parse_mode=enums.ParseMode.MARKDOWN)

@app.on_message(filters.command("current") & filters.group)
async def current(_, m: Message):
    """Show current playing song"""
    db = load_db()
    gid = str(m.chat.id)
    
    queue = db["queues"].get(gid, [])
    
    if not queue:
        await m.reply("📭 **Nothing is playing**")
        return
    
    song = queue[0]
    duration_str = format_duration(song["duration"])
    
    text = (
        f"▶️ **Currently Playing**\n\n"
        f"**🎵 Title:** {song['title']}\n"
        f"**⏱️ Duration:** {duration_str}\n"
        f"**👤 Requested by:** {song['by']}\n"
        f"**📊 Queue Position:** 1/{len(queue)}"
    )
    
    await m.reply(text, parse_mode=enums.ParseMode.MARKDOWN)

@app.on_message(filters.command("clean") & filters.group)
async def clean(_, m: Message):
    """Clear queue (admin only)"""
    if not await is_admin(m.chat.id, m.from_user.id):
        await m.reply("🔒 **Only admins can clear queue**")
        return
    
    db = load_db()
    gid = str(m.chat.id)
    db["queues"][gid] = []
    save_db(db)
    await m.reply("🧹 **Queue cleared**")

@app.on_message(filters.command("userplay") & filters.group)
async def userplay(_, m: Message):
    """Toggle user play permission"""
    if not await is_admin(m.chat.id, m.from_user.id):
        await m.reply("🔒 **Only admins can change this**")
        return
    
    db = load_db()
    gid = str(m.chat.id)
    
    if len(m.command) < 2:
        current = "ON" if db["userplay"].get(gid, True) else "OFF"
        await m.reply(f"👥 **User play is currently:** {current}")
        return
    
    mode = m.command[1].lower()
    if mode in ["on", "off"]:
        db["userplay"][gid] = mode == "on"
        save_db(db)
        await m.reply(f"👥 **User play turned {'ON' if mode=='on' else 'OFF'}**")
    else:
        await m.reply("❌ Use `/userplay on` or `/userplay off`")

# ===================== LYRICS COMMAND =====================

@app.on_message(filters.command("lyrics"))
async def lyrics_cmd(_, m: Message):
    """Get song lyrics"""
    if len(m.command) < 2:
        await m.reply("🎵 **Usage:** `/lyrics <song name>`")
        return
    
    query = " ".join(m.command[1:])
    
    status_msg = await m.reply(f"🔍 **Searching lyrics for:** {query}")
    
    lyrics = get_lyrics(query)
    
    if lyrics:
        if len(lyrics) > 4000:
            # Split into multiple messages
            parts = [lyrics[i:i+4000] for i in range(0, len(lyrics), 4000)]
            for i, part in enumerate(parts):
                await m.reply(f"**Lyrics (Part {i+1}):**\n\n{part}")
            await status_msg.delete()
        else:
            await status_msg.edit(f"**🎵 Lyrics for {query}**\n\n{lyrics}")
    else:
        await status_msg.edit("❌ **Lyrics not found**")

# ===================== DOWNLOAD COMMAND =====================

@app.on_message(filters.command("download"))
async def download_cmd(_, m: Message):
    """Download a song"""
    if len(m.command) < 2:
        await m.reply("🎵 **Usage:** `/download <song name or URL>`")
        return
    
    query = " ".join(m.command[1:])
    
    status_msg = await m.reply("🔍 **Searching...**")
    
    audio = fetch_audio(query)
    
    if not audio:
        await status_msg.edit("❌ **Song not found!**")
        return
    
    # Send as audio file
    await status_msg.edit("📥 **Downloading...**")
    
    try:
        # Create a temporary download
        ydl_opts = {
            "format": "bestaudio",
            "outtmpl": "downloads/%(title)s.%(ext)s",
            "quiet": True
        }
        
        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(audio["webpage_url"], download=True)
            filename = ydl.prepare_filename(info)
            
            # Send audio file
            await m.reply_audio(
                audio=filename,
                title=audio["title"],
                performer="Pro Player Music Bot",
                duration=audio["duration"]
            )
            
            # Clean up
            os.remove(filename)
            
        await status_msg.delete()
    except Exception as e:
        await status_msg.edit(f"❌ **Download failed:** {str(e)}")

# ===================== PING COMMAND =====================

@app.on_message(filters.command("ping"))
async def ping(_, m: Message):
    """Check bot response time"""
    start = time.time()
    msg = await m.reply("🏓 **Pong!**")
    end = time.time()
    
    ping_time = round((end - start) * 1000, 2)
    await msg.edit(f"🏓 **Pong!** `{ping_time}ms`")

@app.on_message(filters.command("uptime"))
async def uptime(_, m: Message):
    """Show bot uptime"""
    db = load_db()
    start_time = db.get("stats", {}).get("start_time", now())
    uptime_str = get_readable_time(now() - start_time)
    
    await m.reply(f"⏱️ **Bot Uptime:** `{uptime_str}`")

# ===================== STREAM END HANDLER =====================

@call.on_stream_end()
async def stream_end_handler(_, upd: StreamAudioEnded):
    """Handle when a stream ends"""
    db = load_db()
    gid = str(upd.chat_id)
    
    queue = db["queues"].get(gid, [])
    
    if queue:
        # Remove current song
        queue.pop(0)
    
    if not queue:
        # No more songs
        try:
            await call.leave_group_call(upd.chat_id)
        except:
            pass
        db["active_vc"][gid] = False
        save_db(db)
        
        # Notify group
        try:
            await app.send_message(
                upd.chat_id,
                "✅ **Queue finished! Left voice chat.**\n\nUse /play to start again."
            )
        except:
            pass
    else:
        # Play next song
        try:
            await call.change_stream(
                upd.chat_id,
                InputStream(queue[0]["url"])
            )
            
            # Notify group
            await app.send_message(
                upd.chat_id,
                f"▶️ **Now Playing:** {queue[0]['title']}"
            )
        except Exception as e:
            log.error(f"Stream change error: {e}")
        
        save_db(db)

# ===================== RUN =====================

async def main():
    """Main function"""
    log.info("🎵 Starting Pro Player Music Bot...")
    
    # Initialize database
    db = load_db()
    if "stats" not in db:
        db["stats"] = {"start_time": now(), "total_songs_played": 0, "total_commands": 0}
    save_db(db)
    
    # Start bot
    await app.start()
    log.info("✅ Pyrogram client started")
    
    # Start calls
    await call.start()
    log.info("✅ PyTgCalls started")
    
    log.info("🎧 Bot is running! Press Ctrl+C to stop.")
    
    # Keep running
    try:
        await asyncio.Event().wait()
    except KeyboardInterrupt:
        log.info("🛑 Stopping bot...")
    finally:
        await app.stop()
        await call.stop()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        log.info("Bot stopped by user")
    except Exception as e:
        log.error(f"Fatal error: {e}")
