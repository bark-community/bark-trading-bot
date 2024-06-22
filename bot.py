import os
import telebot
import logging
from cryptography.fernet import Fernet
from dotenv import load_dotenv
from solana.keypair import Keypair
from solana.rpc.api import Client
from base58 import b58encode
from jupiter_swap_api import JupiterSwapAPI
from referral_system import ReferralSystem
from pnl_tracker import PNLTracker
from user_management import UserManager
from price_alerts import PriceAlertManager
from solana_api import SolanaAPI
from ratelimit import limits, sleep_and_retry

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)

# Initialize bot and services
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
ENCRYPTION_KEY = os.getenv('ENCRYPTION_KEY')
JUPITER_SWAP_API_KEY = os.getenv('JUPITER_SWAP_API')
SOLANA_API_KEY = os.getenv('SOLANA_API_KEY')

cipher_suite = Fernet(ENCRYPTION_KEY)
bot = telebot.TeleBot(TELEGRAM_TOKEN)
jupiter_swap_api = JupiterSwapAPI(JUPITER_SWAP_API_KEY)
referral_system = ReferralSystem()
pnl_tracker = PNLTracker(jupiter_swap_api)
user_manager = UserManager(cipher_suite)
price_alert_manager = PriceAlertManager()
solana_api = SolanaAPI(SOLANA_API_KEY)
solana_client = Client("https://api.mainnet-beta.solana.com")
SOLANA_PROGRAM_ID = "TOKEN_2022_PROGRAM_ID"

LOW_BALANCE_THRESHOLD = 0.0069

# Define rate limits
CALLS = 10
RATE_LIMIT_PERIOD = 60  # seconds

@sleep_and_retry
@limits(calls=CALLS, period=RATE_LIMIT_PERIOD)
def limited_api_call():
    pass  # Dummy function for rate limiting

def main_menu_markup():
    markup = telebot.types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    markup.add(
        telebot.types.KeyboardButton('💰 Buy'),
        telebot.types.KeyboardButton('🔄 Refresh'),
        telebot.types.KeyboardButton('🏦 Wallet'),
        telebot.types.KeyboardButton('⚙️ Settings'),
        telebot.types.KeyboardButton('📊 Dashboard'),
        telebot.types.KeyboardButton('📈 Market Data')
    )
    return markup

@bot.message_handler(commands=['start'])
def send_welcome(message):
    user_id = message.from_user.id
    if not user_manager.is_user_verified(user_id):
        bot.reply_to(message, "Please verify your account using /verify before using BarkBOT.")
        return

    if not user_manager.has_wallet(user_id):
        wallet = generate_wallet()
        user_manager.save_wallet(user_id, wallet)
        bot.reply_to(message, f"🔑 New Solana wallet generated:\n\nPublic Key: {wallet['public_key']}\nPrivate Key: {wallet['private_key']}\n\nPlease save your private key securely.", reply_markup=main_menu_markup())
    else:
        wallet = user_manager.get_wallet(user_id)
        balance_warning = "⚠️ Your balance is below 0.0069 SOL. Please add more to pay for transaction fees!" if solana_api.get_balance(wallet['public_key']) < LOW_BALANCE_THRESHOLD else ""
        bot.reply_to(message, f"🎉 Welcome back to BarkBOT! 🎉\n\nYour wallet address is:\n\n📍 {wallet['public_key']}\n\nTo buy a token, paste the token address or tap “💰 Buy”.\n\nTap \"🔄 Refresh\" to update your balance.\nTap \"🏦 Wallet\" to withdraw your SOL and export private key.\n\nAdvanced traders can set a custom RPC, slippage, and priority in \"⚙️ Settings\".\n\n{balance_warning}", reply_markup=main_menu_markup())

@bot.message_handler(commands=['verify'])
def verify_user(message):
    bot.reply_to(message, "✉️ Please provide your email for verification.")
    bot.register_next_step_handler(message, process_verification)

def process_verification(message):
    email = message.text
    verification_code = user_manager.generate_verification_code(message.from_user.id, email)
    bot.reply_to(message, f"A verification code has been sent to {email}. Please enter the code to verify your account.")
    bot.register_next_step_handler(message, confirm_verification, email, verification_code)

def confirm_verification(message, email, verification_code):
    user_code = message.text
    if user_code == verification_code:
        user_manager.verify_user(message.from_user.id)
        bot.reply_to(message, "✅ Your account has been verified! You can now use BarkBOT.")
    else:
        bot.reply_to(message, "❌ Invalid verification code. Please try again.")
        bot.register_next_step_handler(message, confirm_verification, email, verification_code)

def generate_wallet():
    keypair = Keypair.generate()
    public_key = str(keypair.public_key)
    private_key = b58encode(keypair.secret_key).decode('utf-8')
    return {'public_key': public_key, 'private_key': private_key}

@bot.message_handler(commands=['help'])
def show_help(message):
    markup = telebot.types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        telebot.types.InlineKeyboardButton('Trading Commands', callback_data='help_trading'),
        telebot.types.InlineKeyboardButton('Account Management', callback_data='help_account'),
        telebot.types.InlineKeyboardButton('Security Features', callback_data='help_security'),
        telebot.types.InlineKeyboardButton('Market Data', callback_data='help_market')
    )
    bot.reply_to(message, "❓ Select a topic to get help:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('help_'))
def help_topic(call):
    topic = call.data.split('_')[1]
    help_texts = {
        'trading': (
            "📈 Trading Commands:\n"
            "/autobuy - Automatically buy BARK tokens by pasting its address.\n"
            "/setalert - Set a price alert for BARK tokens.\n"
            "/pnl - Get your PNL overview.\n"
            "/history - View your transaction history.\n"
        ),
        'account': (
            "👤 Account Management:\n"
            "/register - Register as a new user.\n"
            "/profile - View and update your profile.\n"
            "/referral - Get your referral link and earn rewards.\n"
        ),
        'security': (
            "🔒 Security Features:\n"
            "/enable_2fa - Enable two-factor authentication.\n"
            "/disable_2fa - Disable two-factor authentication.\n"
        ),
        'market': (
            "📊 Market Data:\n"
            "/market - Get the latest market data.\n"
        )
    }
    bot.send_message(call.message.chat.id, help_texts.get(topic, "❓ No help available for this topic."))

@bot.message_handler(func=lambda message: message.text == '🔄 Refresh')
def refresh_balance(message):
    user_id = message.from_user.id
    sol_balance, bark_balance = get_balances(user_id)
    balance_warning = "⚠️ Your balance is below 0.0069 SOL. Please add more to pay for transaction fees!" if sol_balance < LOW_BALANCE_THRESHOLD else ""
    balance_text = (
        f"💼 Your current balances are:\n\n"
        f"SOL: {sol_balance} SOL\n"
        f"BARK: {bark_balance} BARK\n\n"
        f"{balance_warning}"
    )
    bot.reply_to(message, balance_text)

def get_balances(user_id):
    try:
        wallet = user_manager.get_wallet(user_id)
        sol_balance = solana_api.get_balance(wallet['public_key'])
        bark_balance = jupiter_swap_api.get_token_balance(wallet['public_key'], SOLANA_PROGRAM_ID)
        return sol_balance, bark_balance
    except Exception as e:
        logging.error(f"Error retrieving balances for user {user_id}: {e}")
        return 0, 0

@bot.message_handler(func=lambda message: message.text == '💰 Buy')
def initiate_buy(message):
    bot.reply_to(message, "🔹 Please send the token address you want to buy.")
    bot.register_next_step_handler(message, execute_buy)

def execute_buy(message):
    token_address = message.text
    user_id = message.from_user.id
    try:
        limited_api_call()
        token_info = jupiter_swap_api.get_token_info(token_address)
        confirm_text = (
            f"📊 Token Information:\n\n"
            f"Name: {token_info['name']}\n"
            f"Symbol: {token_info['symbol']}\n"
            f"Price: {token_info['price']} SOL\n\n"
            "Do you want to proceed with the purchase? (yes/no)"
        )
        bot.reply_to(message, confirm_text)
        bot.register_next_step_handler(message, confirm_buy, token_address, token_info['price'])
    except Exception as e:
        logging.error(f"Error retrieving token information for address {token_address}: {e}")
        bot.reply_to(message, f"❌ Failed to retrieve token information: {str(e)}")

def confirm_buy(message, token_address, token_price):
    if message.text.lower() == 'yes':
        user_id = message.from_user.id
        try:
            limited_api_call()
            wallet = user_manager.get_wallet(user_id)
            tx_id = jupiter_swap_api.buy_token(token_address, wallet['public_key'], token_price)
            receipt = jupiter_swap_api.get_transaction_receipt(tx_id)
            bot.reply_to(message, f"✅ Successfully purchased tokens at address {token_address}.\nTransaction Receipt:\n{receipt}")
        except Exception as e:
            logging.error(f"Error purchasing tokens at address {token_address}: {e}")
            bot.reply_to(message, f"❌ Failed to purchase tokens: {str(e)}")
    else:
        bot.reply_to(message, "❌ Purchase cancelled.")

@bot.message_handler(func=lambda message: message.text == '🏦 Wallet')
def wallet_menu(message):
    markup = telebot.types.InlineKeyboardMarkup(row_width=1)
    markup.add(
        telebot.types.InlineKeyboardButton('Withdraw SOL', callback_data='withdraw_sol'),
        telebot.types.InlineKeyboardButton('Withdraw BARK', callback_data='withdraw_bark'),
        telebot.types.InlineKeyboardButton('Export Private Key', callback_data='export_key')
    )
    bot.reply_to(message, "🏦 Wallet Options:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == 'withdraw_sol')
def withdraw_sol(call):
    bot.send_message(call.message.chat.id, "🔹 Please send the amount of SOL you want to withdraw and the recipient address separated by a space (e.g., 0.1 9tV5oXSkPzYBwZJCnreMA4Q2NYZox7snJYEbxmFEaSac).")
    bot.register_next_step_handler(call.message, execute_withdraw_sol)

def execute_withdraw_sol(message):
    try:
        amount, recipient_address = message.text.split()
        amount = float(amount)
        user_id = message.from_user.id
        limited_api_call()
        wallet = user_manager.get_wallet(user_id)
        solana_api.transfer_sol(wallet['public_key'], recipient_address, amount)
        bot.reply_to(message, f"✅ Successfully transferred {amount} SOL to {recipient_address}.")
    except Exception as e:
        logging.error(f"Error transferring SOL: {e}")
        bot.reply_to(message, f"❌ Failed to transfer SOL: {str(e)}")

@bot.callback_query_handler(func=lambda call: call.data == 'withdraw_bark')
def withdraw_bark(call):
    bot.send_message(call.message.chat.id, "🔹 Please send the amount of BARK you want to withdraw and the recipient address separated by a space (e.g., 10 9tV5oXSkPzYBwZJCnreMA4Q2NYZox7snJYEbxmFEaSac).")
    bot.register_next_step_handler(call.message, execute_withdraw_bark)

def execute_withdraw_bark(message):
    try:
        amount, recipient_address = message.text.split()
        amount = float(amount)
        user_id = message.from_user.id
        limited_api_call()
        wallet = user_manager.get_wallet(user_id)
        jupiter_swap_api.transfer_bark(wallet['public_key'], recipient_address, amount)
        bot.reply_to(message, f"✅ Successfully transferred {amount} BARK to {recipient_address}.")
    except Exception as e:
        logging.error(f"Error transferring BARK: {e}")
        bot.reply_to(message, f"❌ Failed to transfer BARK: {str(e)}")

@bot.callback_query_handler(func=lambda call: call.data == 'export_key')
def export_key(call):
    try:
        private_key = user_manager.get_private_key(call.from_user.id)
        bot.send_message(call.message.chat.id, f"🔑 Your private key is: {private_key}")
    except Exception as e:
        logging.error(f"Error exporting private key for user {call.from_user.id}: {e}")
        bot.reply_to(call.message, f"❌ Failed to export private key: {str(e)}")

@bot.message_handler(func=lambda message: message.text == '⚙️ Settings')
def settings_menu(message):
    markup = telebot.types.InlineKeyboardMarkup(row_width=1)
    markup.add(
        telebot.types.InlineKeyboardButton('Set Custom RPC', callback_data='set_rpc'),
        telebot.types.InlineKeyboardButton('Set Slippage', callback_data='set_slippage'),
        telebot.types.InlineKeyboardButton('Set Priority', callback_data='set_priority')
    )
    bot.reply_to(message, "⚙️ Advanced Settings:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == 'set_rpc')
def set_rpc(call):
    bot.send_message(call.message.chat.id, "🔹 Please send the custom RPC URL.")
    bot.register_next_step_handler(call.message, update_rpc)

def update_rpc(message):
    custom_rpc = message.text
    try:
        user_manager.update_rpc(message.from_user.id, custom_rpc)
        bot.reply_to(message, "✅ Custom RPC has been set.")
    except Exception as e:
        logging.error(f"Error setting custom RPC for user {message.from_user.id}: {e}")
        bot.reply_to(message, f"❌ Failed to set custom RPC: {str(e)}")

@bot.callback_query_handler(func=lambda call: call.data == 'set_slippage')
def set_slippage(call):
    bot.send_message(call.message.chat.id, "🔹 Please send the slippage percentage (e.g., 0.5 for 0.5%).")
    bot.register_next_step_handler(call.message, update_slippage)

def update_slippage(message):
    try:
        slippage = float(message.text)
        user_manager.update_slippage(message.from_user.id, slippage)
        bot.reply_to(message, "✅ Slippage has been set.")
    except Exception as e:
        logging.error(f"Error setting slippage for user {message.from_user.id}: {e}")
        bot.reply_to(message, f"❌ Failed to set slippage: {str(e)}")

@bot.callback_query_handler(func=lambda call: call.data == 'set_priority')
def set_priority(call):
    bot.send_message(call.message.chat.id, "🔹 Please send the priority level (e.g., high, medium, low).")
    bot.register_next_step_handler(call.message, update_priority)

def update_priority(message):
    priority = message.text.lower()
    try:
        user_manager.update_priority(message.from_user.id, priority)
        bot.reply_to(message, "✅ Priority has been set.")
    except Exception as e:
        logging.error(f"Error setting priority for user {message.from_user.id}: {e}")
        bot.reply_to(message, f"❌ Failed to set priority: {str(e)}")

@bot.message_handler(func=lambda message: message.text == '📊 Dashboard')
def show_dashboard(message):
    user_id = message.from_user.id
    pnl = pnl_tracker.get_pnl(user_id)
    recent_transactions = pnl_tracker.get_recent_transactions(user_id)
    dashboard_text = (
        f"📊 Dashboard:\n\n"
        f"Total PNL: {pnl['total_pnl']} SOL\n"
        f"Total Volume: {pnl['total_volume']} SOL\n"
        f"Win/Loss Ratio: {pnl['win_loss_ratio']}\n"
        f"Average Hold Time: {pnl['average_hold_time']} hours\n\n"
        f"Recent Transactions:\n"
    )
    for tx in recent_transactions:
        dashboard_text += f"- {tx['date']}: {tx['amount']} SOL ({tx['status']})\n"
    bot.reply_to(message, dashboard_text)

@bot.message_handler(func=lambda message: message.text == '📈 Market Data')
def show_market_data(message):
    market_data = jupiter_swap_api.get_market_data()
    market_text = (
        "📈 Market Data:\n\n"
        f"Latest Price: {market_data['latest_price']} SOL\n"
        f"24h Volume: {market_data['24h_volume']} SOL\n"
        f"Market Cap: {market_data['market_cap']} SOL\n"
        f"24h Change: {market_data['24h_change']}%\n"
    )
    bot.reply_to(message, market_text)

if __name__ == '__main__':
    logging.info("Starting BarkBOT...")
    bot.polling()