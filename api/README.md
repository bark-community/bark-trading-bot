# BarkBOT API

BarkBOT is a Telegram bot that allows users to manage their Solana wallets, trade tokens, set price alerts, and manage referrals. This project also includes a RESTful API built using Flask, providing endpoints for user management, trading operations, and more.

## Features

- **User Registration and Login:** Secure registration and login using JWT.
- **Wallet Management:** Generate and manage Solana wallets.
- **Trading Operations:** Buy tokens using the Jupiter Trading API.
- **Price Alerts:** Set and manage price alerts for tokens.
- **Referral System:** Manage and track referrals.
- **Transaction History:** Retrieve user transaction history.
- **Webhooks:** Support for asynchronous operations via webhooks.
- **Enhanced Security:** JWT-based authentication.
- **Rate Limiting:** Prevent abuse with rate limiting.

## Prerequisites

- Python 3.7+
- PostgreSQL

## Installation

1. **Clone the repository:**

    ```sh
    git clone https://github.com/your-repo/barkbot.git
    cd barkbot
    ```

2. **Install dependencies:**

    ```sh
    pip install -r requirements.txt
    ```

3. **Set up environment variables:**
    
    Create a `.env` file in the project root with the following content:

    ```env
    TELEGRAM_TOKEN=<your-telegram-bot-token>
    ENCRYPTION_KEY=<your-encryption-key>
    JUPITER_API_KEY=<your-jupiter-api-key>
    SOLANA_API_KEY=<your-solana-api-key>
    DATABASE_URL=postgresql://barkbotuser:<password>@localhost:5432/barkbot
    JWT_SECRET_KEY=<your-jwt-secret-key>
    PRIVATE_KEY=<your-private-key>
    SOLANA_RPC_ENDPOINT_URL=<your-solana-rpc-endpoint-url>
    ```

4. **Set up PostgreSQL:**

    Install PostgreSQL and create a database:

    ```sh
    sudo apt-get install postgresql postgresql-contrib
    sudo -u postgres createdb barkbot
    sudo -u postgres createuser -P barkbotuser
    ```

5. **Run the Flask application:**

    ```sh
    python app.py
    ```

    The API will be available at `http://127.0.0.1:5000/`.


6. **Or Run Docker Compose:**

- In the terminal, navigate to the root directory of your project.
  Run the following command to start the services:

```sh
docker-compose -f barkbot.yaml up
```
## API Endpoints

### User Management

- **Register:**
    - Endpoint: `/register`
    - Method: `POST`
    - Request Body:
        ```json
        {
            "telegram_id": 123456,
            "email": "user@example.com",
            "password": "yourpassword"
        }
        ```
    - Description: Register a new user.

- **Login:**
    - Endpoint: `/login`
    - Method: `POST`
    - Request Body:
        ```json
        {
            "email": "user@example.com",
            "password": "yourpassword"
        }
        ```
    - Description: Log in and receive a JWT token.

### Wallet Management

- **Generate Wallet:**
    - Endpoint: `/generate_wallet`
    - Method: `POST`
    - Headers: `Authorization: Bearer <JWT_TOKEN>`
    - Request Body:
        ```json
        {
            "telegram_id": 123456
        }
        ```
    - Description: Generate a new Solana wallet.

- **Get Wallet:**
    - Endpoint: `/get_wallet`
    - Method: `GET`
    - Headers: `Authorization: Bearer <JWT_TOKEN>`
    - Description: Retrieve the user's wallet information.

### Trading Operations

- **Buy Token:**
    - Endpoint: `/buy_token`
    - Method: `POST`
    - Headers: `Authorization: Bearer <JWT_TOKEN>`
    - Request Body:
        ```json
        {
            "telegram_id": 123456,
            "token_address": "TOKEN_ADDRESS"
        }
        ```
    - Description: Buy tokens using the Jupiter Trading API.

- **Get Market Data:**
    - Endpoint: `/get_market_data`
    - Method: `GET`
    - Headers: `Authorization: Bearer <JWT_TOKEN>`
    - Description: Retrieve the latest market data.

### Price Alerts

- **Set Price Alert:**
    - Endpoint: `/set_price_alert`
    - Method: `POST`
    - Headers: `Authorization: Bearer <JWT_TOKEN>`
    - Request Body:
        ```json
        {
            "telegram_id": 123456,
            "token_address": "TOKEN_ADDRESS",
            "target_price": 100.0
        }
        ```
    - Description: Set a price alert for a token.

- **Get Price Alerts:**
    - Endpoint: `/get_price_alerts`
    - Method: `GET`
    - Headers: `Authorization: Bearer <JWT_TOKEN>`
    - Description: Retrieve all price alerts for the user.

- **Delete Price Alert:**
    - Endpoint: `/delete_price_alert`
    - Method: `DELETE`
    - Headers: `Authorization: Bearer <JWT_TOKEN>`
    - Request Body:
        ```json
        {
            "telegram_id": 123456,
            "token_address": "TOKEN_ADDRESS",
            "target_price": 100.0
        }
        ```
    - Description: Delete a specific price alert.

### Referral System

- **Create Referral:**
    - Endpoint: `/create_referral`
    - Method: `POST`
    - Headers: `Authorization: Bearer <JWT_TOKEN>`
    - Request Body:
        ```json
        {
            "telegram_id": 123456,
            "referral_code": "REFERRAL_CODE"
        }
        ```
    - Description: Create a referral.

- **Get Referrals:**
    - Endpoint: `/get_referrals`
    - Method: `GET`
    - Headers: `Authorization: Bearer <JWT_TOKEN>`
    - Description: Retrieve all referrals for the user.

### PNL Tracker

- **Get PNL:**
    - Endpoint: `/pnl`
    - Method: `GET`
    - Headers: `Authorization: Bearer <JWT_TOKEN>`
    - Description: Retrieve the user's profit and loss data.

### Webhooks

- **Webhook:**
    - Endpoint: `/webhook`
    - Method: `POST`
    - Description: Webhook endpoint for asynchronous notifications.

## Testing the API

You can use tools like Postman or cURL to test the API endpoints. Remember to get the JWT token from the `/login` endpoint and use it in the `Authorization` header as `Bearer <JWT_TOKEN>`.

### Example cURL Commands

- **Register User:**

    ```sh
    curl -X POST http://127.0.0.1:5000/register -H "Content-Type: application/json" -d '{"telegram_id": 123456, "email": "user@example.com", "password": "yourpassword"}'
    ```

- **Login:**

    ```sh
    curl -X POST http://127.0.0.1:5000/login -H "Content-Type: application/json" -d '{"email": "user@example.com", "password": "yourpassword"}'
    ```

- **Generate Wallet:**

    ```sh
    curl -X POST http://127.0.0.1:5000/generate_wallet -H "Content-Type: application/json" -H "Authorization: Bearer <JWT_TOKEN>" -d '{"telegram_id": 123456}'
    ```

- **Buy Token:**

    ```sh
    curl -X POST http://127.0.0.1:5000/buy_token -H "Content-Type: application/json" -H "Authorization: Bearer <JWT_TOKEN>" -d '{"telegram_id": 123456, "token_address": "TOKEN_ADDRESS"}'
    ```

## Instructions for Use

- Set up your environment by cloning the repository and installing the required packages.
- Configure your environment variables in the .env file.
- Run the Flask application using python app.py.
- Test the API using Postman or cURL with the provided endpoints and example commands.

## Contributing

Contributions are welcome! Please fork the repository and submit a pull request for any improvements or bug fixes.

## License

MIT License.
