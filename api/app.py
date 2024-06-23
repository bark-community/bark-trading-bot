import os
import base58
import base64
import json
import asyncio

from flask import Flask, request, jsonify
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity
from flask_bcrypt import Bcrypt
from dotenv import load_dotenv
from solana.rpc.async_api import AsyncClient
from solana.rpc.commitment import Processed
from solana.rpc.types import TxOpts
from solders.keypair import Keypair
from solders.message import VersionedTransaction
from solders.pubkey import Pubkey
from jupiter_python_sdk.jupiter import Jupiter
from marshmallow import Schema, fields, ValidationError

from user_manager import UserManager

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)

# Initialize services
ENCRYPTION_KEY = os.getenv('ENCRYPTION_KEY')
DATABASE_URL = os.getenv('DATABASE_URL')
JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY')
PRIVATE_KEY = base58.b58decode(os.getenv('PRIVATE_KEY'))
SOLANA_RPC_ENDPOINT_URL = os.getenv('SOLANA_RPC_ENDPOINT_URL')

# Initialize Flask app
app = Flask(__name__)
app.config['JWT_SECRET_KEY'] = JWT_SECRET_KEY
jwt = JWTManager(app)
bcrypt = Bcrypt(app)
limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=["200 per day", "50 per hour"]
)

# Initialize Jupiter
private_key = Keypair.from_bytes(PRIVATE_KEY)
async_client = AsyncClient(SOLANA_RPC_ENDPOINT_URL)
jupiter = Jupiter(async_client, private_key)

# Initialize UserManager
user_manager = UserManager(ENCRYPTION_KEY)

# Schemas for data validation
class RegisterSchema(Schema):
    telegram_id = fields.Int(required=True)
    email = fields.Email(required=True)
    password = fields.Str(required=True)

class LoginSchema(Schema):
    email = fields.Email(required=True)
    password = fields.Str(required=True)

class SwapSchema(Schema):
    input_mint = fields.Str(required=True)
    output_mint = fields.Str(required=True)
    amount = fields.Int(required=True)
    slippage_bps = fields.Int(required=True)

class LimitOrderSchema(Schema):
    input_mint = fields.Str(required=True)
    output_mint = fields.Str(required=True)
    in_amount = fields.Int(required=True)
    out_amount = fields.Int(required=True)

class CreateDCASchema(Schema):
    input_mint = fields.Str(required=True)
    output_mint = fields.Str(required=True)
    total_in_amount = fields.Int(required=True)
    in_amount_per_cycle = fields.Int(required=True)
    cycle_frequency = fields.Int(required=True)
    min_out_amount_per_cycle = fields.Int(required=True)
    max_out_amount_per_cycle = fields.Int(required=True)
    start = fields.Int(required=True)

class CloseDCASchema(Schema):
    dca_pubkey = fields.Str(required=True)

# Error handling
@app.errorhandler(ValidationError)
def handle_validation_error(e):
    logging.error(f"Validation error: {e}")
    return jsonify(e.messages), 400

@app.errorhandler(404)
def page_not_found(e):
    return jsonify({"message": "Resource not found"}), 404

@app.errorhandler(500)
def internal_server_error(e):
    logging.error(f"Internal server error: {e}")
    return jsonify({"message": "Internal server error"}), 500

# User Registration and Login
@app.route('/register', methods=['POST'])
@limiter.limit("5 per minute")
def register():
    try:
        data = RegisterSchema().load(request.json)
        email = data['email']
        telegram_id = data['telegram_id']
        password = data['password']
        hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
        user_manager.create_user(telegram_id, email, hashed_password)
        logging.info(f"User registered: {email}")
        return jsonify({"message": "User registered successfully."})
    except ValidationError as err:
        return jsonify(err.messages), 400

@app.route('/login', methods=['POST'])
@limiter.limit("5 per minute")
def login():
    try:
        data = LoginSchema().load(request.json)
        email = data['email']
        password = data['password']
        user = user_manager.get_user_by_email(email)
        if user and bcrypt.check_password_hash(user.password, password):
            access_token = create_access_token(identity=user.telegram_id)
            logging.info(f"User logged in: {email}")
            return jsonify({"access_token": access_token})
        else:
            return jsonify({"message": "Invalid email or password"}), 401
    except ValidationError as err:
        return jsonify(err.messages), 400

# Asynchronous function to execute swap
async def execute_swap(input_mint, output_mint, amount, slippage_bps):
    try:
        transaction_data = await jupiter.swap(
            input_mint=input_mint,
            output_mint=output_mint,
            amount=amount,
            slippage_bps=slippage_bps,
        )
        raw_transaction = VersionedTransaction.from_bytes(base64.b64decode(transaction_data))
        signature = private_key.sign_message(raw_transaction.message.to_bytes_versioned())
        signed_txn = VersionedTransaction.populate(raw_transaction.message, [signature])
        opts = TxOpts(skip_preflight=False, preflight_commitment=Processed)
        result = await async_client.send_raw_transaction(txn=bytes(signed_txn), opts=opts)
        transaction_id = json.loads(result.to_json())['result']
        logging.info(f"Transaction sent: {transaction_id}")
        return transaction_id
    except Exception as e:
        logging.error(f"Error in execute_swap: {e}")
        raise

@app.route('/swap', methods=['POST'])
@jwt_required()
@limiter.limit("5 per minute")
def swap():
    try:
        data = SwapSchema().load(request.json)
        telegram_id = get_jwt_identity()
        input_mint = data['input_mint']
        output_mint = data['output_mint']
        amount = data['amount']
        slippage_bps = data['slippage_bps']
        transaction_id = asyncio.run(execute_swap(input_mint, output_mint, amount, slippage_bps))
        return jsonify({"message": f"Transaction sent: https://explorer.solana.com/tx/{transaction_id}", "transaction_id": transaction_id})
    except ValidationError as err:
        return jsonify(err.messages), 400
    except Exception as e:
        return jsonify({"message": f"Error executing swap: {str(e)}"}), 500

# Asynchronous function to open limit order
async def execute_limit_order(input_mint, output_mint, in_amount, out_amount):
    try:
        transaction_data = await jupiter.open_order(
            input_mint=input_mint,
            output_mint=output_mint,
            in_amount=in_amount,
            out_amount=out_amount,
        )
        raw_transaction = VersionedTransaction.from_bytes(base64.b64decode(transaction_data['transaction_data']))
        signature = private_key.sign_message(raw_transaction.message.to_bytes_versioned())
        signed_txn = VersionedTransaction.populate(raw_transaction.message, [signature, transaction_data['signature2']])
        opts = TxOpts(skip_preflight=False, preflight_commitment=Processed)
        result = await async_client.send_raw_transaction(txn=bytes(signed_txn), opts=opts)
        transaction_id = json.loads(result.to_json())['result']
        logging.info(f"Transaction sent: {transaction_id}")
        return transaction_id
    except Exception as e:
        logging.error(f"Error in execute_limit_order: {e}")
        raise

@app.route('/limit_order', methods=['POST'])
@jwt_required()
@limiter.limit("5 per minute")
def limit_order():
    try:
        data = LimitOrderSchema().load(request.json)
        telegram_id = get_jwt_identity()
        input_mint = data['input_mint']
        output_mint = data['output_mint']
        in_amount = data['in_amount']
        out_amount = data['out_amount']
        transaction_id = asyncio.run(execute_limit_order(input_mint, output_mint, in_amount, out_amount))
        return jsonify({"message": f"Transaction sent: https://explorer.solana.com/tx/{transaction_id}", "transaction_id": transaction_id})
    except ValidationError as err:
        return jsonify(err.messages), 400
    except Exception as e:
        return jsonify({"message": f"Error executing limit order: {str(e)}"}), 500

# Asynchronous function to create DCA account
async def execute_create_dca(input_mint, output_mint, total_in_amount, in_amount_per_cycle, cycle_frequency, min_out_amount_per_cycle, max_out_amount_per_cycle, start):
    try:
        create_dca_account = await jupiter.dca.create_dca(
            input_mint=Pubkey.from_string(input_mint),
            output_mint=Pubkey.from_string(output_mint),
            total_in_amount=total_in_amount,
            in_amount_per_cycle=in_amount_per_cycle,
            cycle_frequency=cycle_frequency,
            min_out_amount_per_cycle=min_out_amount_per_cycle,
            max_out_amount_per_cycle=max_out_amount_per_cycle,
            start=start
        )
        logging.info(f"DCA account created: {create_dca_account}")
        return create_dca_account
    except Exception as e:
        logging.error(f"Error in execute_create_dca: {e}")
        raise

@app.route('/create_dca', methods=['POST'])
@jwt_required()
@limiter.limit("5 per minute")
def create_dca():
    try:
        data = CreateDCASchema().load(request.json)
        telegram_id = get_jwt_identity()
        input_mint = data['input_mint']
        output_mint = data['output_mint']
        total_in_amount = data['total_in_amount']
        in_amount_per_cycle = data['in_amount_per_cycle']
        cycle_frequency = data['cycle_frequency']
        min_out_amount_per_cycle = data['min_out_amount_per_cycle']
        max_out_amount_per_cycle = data['max_out_amount_per_cycle']
        start = data['start']
        dca_account = asyncio.run(execute_create_dca(input_mint, output_mint, total_in_amount, in_amount_per_cycle, cycle_frequency, min_out_amount_per_cycle, max_out_amount_per_cycle, start))
        return jsonify(dca_account)
    except ValidationError as err:
        return jsonify(err.messages), 400
    except Exception as e:
        return jsonify({"message": f"Error creating DCA account: {str(e)}"}), 500

# Asynchronous function to close DCA account
async def execute_close_dca(dca_pubkey):
    try:
        close_dca_account = await jupiter.dca.close_dca(
            dca_pubkey=Pubkey.from_string(dca_pubkey)
        )
        logging.info(f"DCA account closed: {close_dca_account}")
        return close_dca_account
    except Exception as e:
        logging.error(f"Error in execute_close_dca: {e}")
        raise

@app.route('/close_dca', methods=['POST'])
@jwt_required()
@limiter.limit("5 per minute")
def close_dca():
    try:
        data = CloseDCASchema().load(request.json)
        telegram_id = get_jwt_identity()
        dca_pubkey = data['dca_pubkey']
        result = asyncio.run(execute_close_dca(dca_pubkey))
        return jsonify(result)
    except ValidationError as err:
        return jsonify(err.messages), 400
    except Exception as e:
        return jsonify({"message": f"Error closing DCA account: {str(e)}"}), 500

# Running the Flask app
if __name__ == '__main__':
    app.run(debug=True)
