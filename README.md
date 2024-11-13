# Stock News Telegram Bot

This project is a Telegram bot that provides stock news and financial analysis. The bot uses various APIs to fetch and analyze stock data, and it communicates with users in Hebrew.

## Features

- **Stock Analysis**: Provides detailed stock analysis using GPT-4.
- **Cost Management**: Calculates and informs users about the cost of operations.
- **User Feedback**: Offers clear feedback to users at each step.

## Requirements

- Python 3.8+
- `python-telegram-bot` library
- `openai` library
- `requests` library

## Installation

1. Clone the repository:
    ```sh
    git clone https://github.com/ellacarmon/StockyBot.git
    cd StockyBot
    ```

2. Create a virtual environment and activate it:
    ```sh
    python -m venv .venv
    source .venv/bin/activate  # On Windows use `.venv\Scripts\activate`
    ```

3. Install the required packages:
    ```sh
    pip install -r requirements.txt
    ```

4. Create a `.env` file in the root directory and add your API keys:
    ```dotenv
    ALPHA_VANTAGE_KEY=your_alpha_vantage_key
    ANTHROPIC_API_KEY=your_anthropic_api_key
    OPENAI_API_KEY=your_openai_api_key
    AZURE_API_KEY=your_azure_api_key
    TELEGRAM_TOKEN=your_telegram_token
    ```

## Usage

1. Run the bot:
    ```sh
    python main.py
    ```

2. Interact with the bot on Telegram.

## Project Structure

- `main.py`: Entry point of the application.
- `telegram_bot.py`: Contains the bot logic and interaction with the Telegram API.
- `.env`: Environment variables for API keys and tokens (not included in the repository).

## Contributing

Contributions are welcome! Please open an issue or submit a pull request.

## License

This project is licensed under the MIT License.
