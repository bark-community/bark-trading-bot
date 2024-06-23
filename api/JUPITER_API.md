import base58
import base64
import json

from solders import message
from solders.pubkey import Pubkey
from solders.keypair import Keypair
from solders.transaction import VersionedTransaction

from solana.rpc.types import TxOpts
from solana.rpc.async_api import AsyncClient
from solana.rpc.commitment import Processed

from jupiter_python_sdk.jupiter import Jupiter, Jupiter_DCA


private_key = Keypair.from_bytes(base58.b58decode(os.getenv("PRIVATE-KEY"))) # Private key as string
async_client = AsyncClient("SOLANA-RPC-ENDPOINT-URL")
jupiter = Jupiter(async_client, private_key)


"""
EXECUTE A SWAP
"""
transaction_data = await jupiter.swap(
    input_mint="So11111111111111111111111111111111111111112",
    output_mint="EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
    amount=5_000_000,
    slippage_bps=1,
)
# Returns str: serialized transactions to execute the swap.

raw_transaction = VersionedTransaction.from_bytes(base64.b64decode(transaction_data))
signature = private_key.sign_message(message.to_bytes_versioned(raw_transaction.message))
signed_txn = VersionedTransaction.populate(raw_transaction.message, [signature])
opts = TxOpts(skip_preflight=False, preflight_commitment=Processed)
result = await async_client.send_raw_transaction(txn=bytes(signed_txn), opts=opts)
transaction_id = json.loads(result.to_json())['result']
print(f"Transaction sent: https://explorer.solana.com/tx/{transaction_id}")


"""
OPEN LIMIT ORDER
"""
transaction_data = await jupiter.open_order(
    input_mint=So11111111111111111111111111111111111111112",
    output_mint=EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
    in_amount=5_000_000,
    out_amount=100_000,
)
# Returns dict: {'transaction_data': serialized transactions to create the limit order, 'signature2': signature of the account that will be opened}

raw_transaction = VersionedTransaction.from_bytes(base64.b64decode(transaction_data['transaction_data']))
signature = private_key.sign_message(message.to_bytes_versioned(raw_transaction.message))
signed_txn = VersionedTransaction.populate(raw_transaction.message, [signature, transaction_data['signature2']])
opts = TxOpts(skip_preflight=False, preflight_commitment=Processed)
result = await async_client.send_raw_transaction(txn=bytes(signed_txn), opts=opts)
transaction_id = json.loads(result.to_json())['result']
print(f"Transaction sent: https://explorer.solana.com/tx/{transaction_id}")


"""
CREATE DCA ACCOUNT
"""
create_dca_account = await jupiter.dca.create_dca(
    input_mint=Pubkey.from_string("So11111111111111111111111111111111111111112"),
    output_mint=Pubkey.from_string("EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"),
    total_in_amount=5_000_000,
    in_amount_per_cycle=100_000,
    cycle_frequency=60,
    min_out_amount_per_cycle=0,
    max_out_amount_per_cycle=0,
    start=0
)
# Returns DCA Account Pubkey and transaction hash.


"""
CLOSE DCA ACCOUNT
"""
close_dca_account = await jupiter.dca.close_dca(
    dca_pubkey=Pubkey.from_string("45iYdjmFUHSJCQHnNpWNFF9AjvzRcsQUP9FDBvJCiNS1")
)
# Returns transaction hash.