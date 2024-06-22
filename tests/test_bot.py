import unittest
from unittest.mock import patch, MagicMock
from bot import get_balances, execute_buy, execute_withdraw_sol, user_manager, jupiter_swap_api, solana_api, bot

class TestBarkBOT(unittest.TestCase):

    @patch('test_bot.user_manager.get_wallet')
    @patch('test_bot.solana_api.get_balance')
    @patch('test_bot.jupiter_swap_api.get_token_balance')
    def test_get_balances(self, mock_get_token_balance, mock_get_balance, mock_get_wallet):
        mock_get_wallet.return_value = {'public_key': 'mock_public_key'}
        mock_get_balance.return_value = 10.0
        mock_get_token_balance.return_value = 100.0

        sol_balance, bark_balance = get_balances(1)
        self.assertEqual(sol_balance, 10.0)
        self.assertEqual(bark_balance, 100.0)

    @patch('test_bot.user_manager.get_wallet')
    @patch('test_bot.jupiter_swap_api.buy_token')
    @patch('test_bot.jupiter_swap_api.get_transaction_receipt')
    def test_execute_buy(self, mock_get_transaction_receipt, mock_buy_token, mock_get_wallet):
        mock_get_wallet.return_value = {'public_key': 'mock_public_key'}
        mock_buy_token.return_value = 'mock_tx_id'
        mock_get_transaction_receipt.return_value = 'mock_receipt'

        message = MagicMock()
        message.text = 'yes'
        execute_buy(message, 'mock_token_address', 1.0)
        bot.reply_to.assert_called_with(message, '✅ Successfully purchased tokens at address mock_token_address.\nTransaction Receipt:\nmock_receipt')

    @patch('test_bot.user_manager.get_wallet')
    @patch('test_bot.solana_api.transfer_sol')
    def test_execute_withdraw_sol(self, mock_transfer_sol, mock_get_wallet):
        mock_get_wallet.return_value = {'public_key': 'mock_public_key'}
        message = MagicMock()
        message.text = '0.1 mock_recipient_address'

        execute_withdraw_sol(message)
        mock_transfer_sol.assert_called_with('mock_public_key', 'mock_recipient_address', 0.1)
        bot.reply_to.assert_called_with(message, '✅ Successfully transferred 0.1 SOL to mock_recipient_address.')

if __name__ == '__main__':
    unittest.main()
