"""Main Telegram bot application."""

from telegram import BotCommand
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters
)

from ..storage import WorkflowStore
from ..utils.config import Config
from ..utils.commands import CommandLoader
from ..utils.logger import get_logger
from ..workflow import WorkflowManager
from .handlers import BotHandlers

logger = get_logger(__name__)


class TelegramBot:
    """Telegram bot application wrapper."""

    def __init__(self):
        """Initialize the bot."""
        # Initialize components
        self.workflow_store = WorkflowStore(
            config_path=Config.DATA_DIRECTORY / "workflows.json"
        )
        self.workflow_manager = WorkflowManager(
            workflow_store=self.workflow_store,
            workflows_dir=Config.DATA_DIRECTORY / "workflows"
        )

        # Load commands
        self.commands = CommandLoader.load_commands()

        # Initialize handlers
        self.handlers = BotHandlers(
            workflow_manager=self.workflow_manager,
            commands=self.commands
        )

        # Build application
        self.app = (
            Application.builder()
            .token(Config.TELEGRAM_BOT_TOKEN)
            .build()
        )

        self._register_handlers()

        logger.info("telegram_bot_initialized")

    def _register_handlers(self) -> None:
        """Register all command and message handlers."""
        # Command handlers
        self.app.add_handler(CommandHandler("start", self.handlers.start))
        self.app.add_handler(CommandHandler("help", self.handlers.help_command))
        self.app.add_handler(CommandHandler("upload", self.handlers.upload))
        self.app.add_handler(CommandHandler("update", self.handlers.update))
        self.app.add_handler(CommandHandler("workflows", self.handlers.workflows))
        self.app.add_handler(CommandHandler("activate", self.handlers.activate))
        self.app.add_handler(CommandHandler("remove", self.handlers.remove))
        self.app.add_handler(CommandHandler("info", self.handlers.info))

        # Document handler (for workflow uploads)
        self.app.add_handler(
            MessageHandler(filters.Document.ALL, self.handlers.handle_document)
        )

        # Message handler (for regular chat)
        self.app.add_handler(
            MessageHandler(filters.TEXT & ~filters.COMMAND, self.handlers.handle_message)
        )

        logger.info("handlers_registered")

    async def _set_bot_commands(self) -> None:
        """Set bot commands in Telegram."""
        try:
            bot_commands = [
                BotCommand(command=cmd["command"], description=cmd["description"])
                for cmd in self.commands
            ]
            await self.app.bot.set_my_commands(bot_commands)
            logger.info("bot_commands_set", count=len(bot_commands))
        except Exception as e:
            logger.error("bot_commands_set_failed", error=str(e))

    def run(self) -> None:
        """Start the bot."""
        logger.info("bot_starting")

        # Set commands on startup
        import asyncio
        asyncio.get_event_loop().run_until_complete(self._set_bot_commands())

        self.app.run_polling(allowed_updates=["message"])

    def stop(self) -> None:
        """Stop the bot and cleanup."""
        logger.info("bot_stopping")
