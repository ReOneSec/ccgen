import logging
import random
import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler, CallbackContext, MessageHandler, filters
from datetime import datetime, timedelta

# Set up logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# Your Telegram bot token
TOKEN = '8128501037:AAHGil80gIhstmUuxBhE9O9rad0Xjk1QPNE'

# Rate limiting settings
rate_limit = {}
max_requests_per_minute = 5

def is_rate_limited(user_id):
    """Check if the user has exceeded the rate limit."""
    now = datetime.now()
    if user_id not in rate_limit:
        rate_limit[user_id] = []
    
    # Remove timestamps older than 1 minute
    rate_limit[user_id] = [timestamp for timestamp in rate_limit[user_id] if timestamp > now - timedelta(minutes=1)]
    
    if len(rate_limit[user_id]) < max_requests_per_minute:
        rate_limit[user_id].append(now)
        return False
    return True

def generate_card(bin_number=None, month=None, year=None, cvv=None):
    """Generate a random credit/debit card number based on optional parameters."""
    if bin_number:
        card_number = bin_number + ''.join([str(random.randint(0, 9)) for _ in range(16 - len(bin_number))])
    else:
        card_number = ''.join([str(random.randint(0, 9)) for _ in range(16)])

    expiry_month = month if month is not None else random.randint(1, 12)
    expiry_year = year if year is not None else random.randint(2025, 2030)
    card_cvv = cvv if cvv is not None else ''.join([str(random.randint(0, 9)) for _ in range(3)])

    return f"{card_number}|{expiry_month:02}|{expiry_year}|{card_cvv}"

def validate_card(card_data):
    """Validate the card using the specified API."""
    url = "https://api.chkr.cc/"
    try:
        response = requests.post(url, json={"data": card_data})
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        logging.error(f"API request failed: {e}")
        return None

def start(update: Update, context: CallbackContext) -> None:
    """Start command handler."""
    update.message.reply_text(
        'Welcome! Use the following commands:\n'
        '/gen [BIN] - Generate 10 random card numbers (optionally with a specific BIN).\n'
        '/gen [BIN]|[mm]|[yyyy] - Generate cards with a specific expiry date.\n'
        '/gen [BIN]|[mm]|[yyyy]|[CVV] - Generate cards with a specific CVV.\n'
        '/chk <CardNumber|mm|yyyy|CVV> - Check a specific card.\n'
        '/feedback <message> - Provide feedback about the bot.\n'
        '/help - Show this help message.'
    )

def gen(update: Update, context: CallbackContext) -> None:
    """Generate cards based on user input and send them in monospace format."""
    user_id = update.message.from_user.id
    
    if is_rate_limited(user_id):
        update.message.reply_text('You are being rate limited. Please wait a minute before trying again.')
        return

    if len(context.args) == 0:
        update.message.reply_text('Please provide a BIN or card details in the format: `<BIN>` or `<BIN>|<mm>|<yyyy>` or `<BIN>|<mm>|<yyyy>|<CVV>`')
        return
    
    user_input = context.args[0].split('|')
    bin_number = user_input[0]

    month = int(user_input[1]) if len(user_input) > 1 and user_input[1].isdigit() else None
    year = int(user_input[2]) if len(user_input) > 2 and user_input[2].isdigit() else None
    cvv = user_input[3] if len(user_input) > 3 else None

    cards = [generate_card(bin_number, month, year, cvv) for _ in range(10)]
    cards_message = "\n".join(f"`{card}`" for card in cards)

    update.message.reply_text(
        f"Generated Cards:\n```\n{cards_message}\n```", 
        parse_mode='MarkdownV2'
    )

def chk(update: Update, context: CallbackContext) -> None:
    """Check the card provided by the user."""
    if len(context.args) < 4:
        update.message.reply_text('Please provide a card in the format: `CardNumber|mm|yyyy|CVV`')
        return
    
    card_data = "|".join(context.args)
    validation_response = validate_card(card_data)

    if validation_response is None:
        update.message.reply_text('Error: Unable to validate card at this time. Please try again later.')
        return

    if validation_response['code'] == 1:
        status = "✅ Live"
    elif validation_response['code'] == 0:
        status = "❌ Die"
    else:
        status = "⚠️ Unknown"

    message = (
        f"Validation Status: {status}\n"
        f"Bank: {validation_response['card']['bank']}\n"
        f"Type: {validation_response['card']['type']}\n"
        f"Category: {validation_response['card']['category']}\n"
        f"Brand: {validation_response['card']['brand']}\n"
        f"Country: {validation_response['card']['country']['name']} ({validation_response['card']['country']['code']})\n"
        f"Currency: {validation_response['card']['country']['currency']}\n"
    )
    update.message.reply_text(message)

def feedback(update: Update, context: CallbackContext) -> None:
    """Collect user feedback."""
    feedback_text = ' '.join(context.args)
    if feedback_text:
        logging.info(f"Feedback from user {update.message.from_user.id}: {feedback_text}")
        update.message.reply_text("Thank you for your feedback!")
    else:
        update.message.reply_text("Please provide feedback after the /feedback command.")

def help_command(update: Update, context: CallbackContext) -> None:
    """Help command handler."""
    update.message.reply_text(
        'This bot helps you generate and validate credit/debit cards.\n\n'
        'Commands:\n'
        '/gen <BIN> - Generates 10 random card numbers for the specified BIN.\n'
        '/gen <BIN>|<mm>|<yyyy> - Generate cards with the specified expiry date.\n'
        '/gen <BIN>|<mm>|<yyyy>|<CVV> - Generate cards with the specified expiry date and CVV.\n'
        '/chk <CardNumber|mm|yyyy|CVV> - Validate a specific card. Example:\n'
        '`/chk 4242424242424242|12|2025|123`\n\n'
        'Note: Always use this bot responsibly and within legal boundaries.'
    )

def main() -> None:
    """Run the bot."""
    updater = Updater(TOKEN)

    dispatcher = updater.dispatcher

    # Register command handlers
    dispatcher.add_handler(CommandHandler("start", start))
    dispatcher.add_handler(CommandHandler("help", help_command))
    dispatcher.add_handler(CommandHandler("gen", gen))
    dispatcher.add_handler(CommandHandler("chk", chk))
    dispatcher.add_handler(CommandHandler("feedback", feedback))
    dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, lambda update, context: update.message.reply_text('Please use commands /gen to generate cards or /chk <CardNumber|mm|yyyy|CVV> to check a card. For assistance, type /help.')))

    # Start the bot
    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()
  
