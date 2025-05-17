import os
import asyncio
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ConversationHandler
from telegram import Update
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv()
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
MONGO_URI = os.getenv("MONGO_URI")

# Стани для ConversationHandler
NAME, AGE, CITY, INTERESTS = range(4)

# Ініціалізація Telegram
app = Application.builder().token(TELEGRAM_TOKEN).build()

async def start(update: Update, context):
    await update.message.reply_text("Вітаю в RaffaelLove! 😊 Напиши /profile, щоб створити анкету.")
    return None

async def profile_start(update: Update, context):
    await update.message.reply_text("Як тебе звати?")
    return NAME

async def get_name(update: Update, context):
    context.user_data["name"] = update.message.text
    await update.message.reply_text("Скільки тобі років?")
    return AGE

async def get_age(update: Update, context):
    try:
        context.user_data["age"] = int(update.message.text)
        await update.message.reply_text("З якого ти міста?")
        return CITY
    except ValueError:
        await update.message.reply_text("Будь ласка, введи число.")
        return AGE

async def get_city(update: Update, context):
    context.user_data["city"] = update.message.text
    await update.message.reply_text("Які твої інтереси?")
    return INTERESTS

async def get_interests(update: Update, context):
    context.user_data["interests"] = update.message.text
    user_data = {
        "user_id": update.effective_user.id,
        "name": context.user_data["name"],
        "age": context.user_data["age"],
        "city": context.user_data["city"],
        "interests": context.user_data["interests"]
    }

    # Збереження в MongoDB
    client = MongoClient(MONGO_URI)
    db = client["RaffaelLove"]
    collection = db["users"]
    collection.update_one({"user_id": user_data["user_id"]}, {"$set": user_data}, upsert=True)

    await update.message.reply_text("Анкета створена! Напиши /find, щоб знайти пару.")
    return ConversationHandler.END

async def find(update: Update, context):
    client = MongoClient(MONGO_URI)
    db = client["RaffaelLove"]
    collection = db["users"]
    users = list(collection.find({"user_id": {"$ne": update.effective_user.id}}))
    
    if users:
        other_user = users[0]
        await update.message.reply_text(
            f"Знайдено: {other_user['name']}, {other_user['age']} років, {other_user['city']}, інтереси: {other_user['interests']}"
        )
    else:
        await update.message.reply_text("Поки немає інших користувачів. 😔")
    
    return None

async def cancel(update: Update, context):
    await update.message.reply_text("Операцію скасовано.")
    return ConversationHandler.END

# Обробники
conv_handler = ConversationHandler(
    entry_points=[CommandHandler("profile", profile_start)],
    states={
        NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_name)],
        AGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_age)],
        CITY: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_city)],
        INTERESTS: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_interests)],
    },
    fallbacks=[CommandHandler("cancel", cancel)],
)

app.add_handler(CommandHandler("start", start))
app.add_handler(conv_handler)
app.add_handler(CommandHandler("find", find))

# Запуск бота
async def main():
    print("Бот запущено!")
    await app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    # Отримуємо поточний event loop
    loop = asyncio.get_event_loop()
    # Запускаємо main у поточному циклі
    loop.create_task(main())
    # Тримаємо цикл активним
    loop.run_forever()