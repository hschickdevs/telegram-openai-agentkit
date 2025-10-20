"""Main entry point for Telegram AgentKit bot."""

import sys

from .bot import TelegramBot
from .utils.config import Config
from .utils.logger import configure_logging, get_logger


def main() -> None:
    """Start the Telegram bot."""
    # Configure logging
    configure_logging(Config.LOG_LEVEL)
    logger = get_logger(__name__)

    # Validate configuration
    try:
        Config.validate()
    except ValueError as e:
        logger.error("configuration_error", error=str(e))
        sys.exit(1)

    # Initialize and run bot
    bot = TelegramBot()

    try:
        logger.info("starting_telegram_agentkit_bot")
        bot.run()
    except KeyboardInterrupt:
        logger.info("received_shutdown_signal")
        bot.stop()
    except Exception as e:
        logger.error("bot_crashed", error=str(e), exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
