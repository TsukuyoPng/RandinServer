import json
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters
)

# Configuration
TOKEN = "7907549703:AAEoFBMUDhJ0UVv05vz8TSeHKOeD9XI3ADI"
CHANNEL_ID = "-1002884520007"
ADMIN_IDS = [6579797317]
CORRECT_CODE = "1KSLY-2LLWE-3UUZQ"
DATA_FILE = "data.json"
WEBAPP_URL = "https://tsukuyopng.github.io/RandinServer/"  # Заменить на реальный URL

# Logging setup
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", 
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Load or initialize data
def load_data():
    try:
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {"users": {}, "attempts": {}}

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=4)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[InlineKeyboardButton("🎮 Открыть игру", web_app={"url": WEBAPP_URL})]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "🎉 *Добро пожаловать в игру \"Угадай код\"!* 🎉\n"
        "Нажмите кнопку ниже, чтобы открыть игровое приложение:",
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )

async def webapp_data(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    web_app_data = update.message.web_app_data.data
    
    try:
        data = json.loads(web_app_data)
        nickname = data.get("nickname", "").strip()
        code = data.get("code", "").strip()
    except json.JSONDecodeError:
        await update.message.reply_text("❌ Ошибка при обработке данных")
        return

    # Сохраняем данные
    user_data = load_data()
    
    if nickname:
        user_data["users"][user_id] = nickname
        save_data(user_data)
    
    if not nickname:
        await update.message.reply_text("⚠️ Укажите ваш ник в Discord")
        return
        
    if not code:
        await update.message.reply_text("❌ Пожалуйста, укажите код")
        return

    # Обновляем статистику
    if user_id not in user_data["attempts"]:
        user_data["attempts"][user_id] = 0
    user_data["attempts"][user_id] += 1
    save_data(user_data)

    # Проверяем код
    if code == CORRECT_CODE:
        message = (
            f"🏆 *Правильный код угадан!*\n"
            f"👤 Пользователь: *{nickname}* (ID: {user_id})\n"
            f"🔑 Код: *{code}*"
        )
        
        # Отправляем в канал
        try:
            await context.bot.send_message(
                chat_id=CHANNEL_ID,
                text=message,
                parse_mode="Markdown"
            )
        except Exception as e:
            logger.error(f"Ошибка отправки в канал: {e}")
        
        # Уведомляем админов
        for admin_id in ADMIN_IDS:
            try:
                await context.bot.send_message(
                    chat_id=admin_id,
                    text=f"🔔 *Угадан правильный код!*\n{message}",
                    parse_mode="Markdown"
                )
            except Exception as e:
                logger.error(f"Ошибка отправки админу: {e}")
        
        await update.message.reply_text(
            "🎉 *Поздравляем! Вы угадали правильный код!* 🏆",
            parse_mode="Markdown"
        )
    else:
        reply = await update.message.reply_text(
            "❌ *Неверный код!* Попробуйте снова 😊",
            parse_mode="Markdown"
        )
        # Удаляем сообщения через 60 секунд
        context.job_queue.run_once(
            delete_messages,
            60,
            data={
                "chat_id": update.message.chat_id,
                "user_message_id": update.message.message_id,
                "bot_message_id": reply.message_id
            }
        )

async def delete_messages(context: ContextTypes.DEFAULT_TYPE):
    job = context.job
    data = job.data
    try:
        await context.bot.delete_message(
            chat_id=data["chat_id"],
            message_id=data["user_message_id"]
        )
        await context.bot.delete_message(
            chat_id=data["chat_id"],
            message_id=data["bot_message_id"]
        )
    except Exception as e:
        logger.error(f"Ошибка удаления сообщений: {e}")

async def send_stats(context: ContextTypes.DEFAULT_TYPE):
    data = load_data()
    
    if not data["attempts"]:
        message = "📊 *Статистика за час*\nПока попыток не было 😔"
    else:
        message = "📊 *Статистика за час*\n"
        for user_id, attempts in data["attempts"].items():
            nickname = data["users"].get(user_id, "Unknown")
            message += f"👤 {nickname}: *{attempts} попыток*\n"
        
        # Сбрасываем статистику
        data["attempts"] = {}
        save_data(data)
    
    try:
        await context.bot.send_message(
            chat_id=CHANNEL_ID,
            text=message,
            parse_mode="Markdown"
        )
    except Exception as e:
        logger.error(f"Ошибка отправки статистики: {e}")

def main():
    application = Application.builder().token(TOKEN).build()
    
    # Handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.WEB_APP_DATA, webapp_data))
    
    # Статистика каждый час
    application.job_queue.run_repeating(send_stats, interval=3600, first=10)
    
    # Start bot
    application.run_polling()

if __name__ == "__main__":
    main()
