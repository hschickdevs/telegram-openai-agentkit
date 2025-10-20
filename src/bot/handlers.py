"""Telegram bot command and message handlers (single-user mode)."""

from typing import List, Dict
from telegram import Update
from telegram.ext import ContextTypes

from ..workflow import WorkflowManager
from ..utils.commands import CommandLoader
from ..utils.config import Config
from ..utils.logger import get_logger

logger = get_logger(__name__)


class BotHandlers:
    """Handler methods for Telegram bot commands (single-user mode)."""

    def __init__(
        self,
        workflow_manager: WorkflowManager,
        commands: List[Dict[str, str]] = None
    ):
        """Initialize bot handlers.

        Args:
            workflow_manager: WorkflowManager instance
            commands: List of command definitions
        """
        self.workflow_manager = workflow_manager
        self.commands = commands or []

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /start command."""
        await update.message.reply_text(
            "🤖 *Welcome to Telegram AgentKit!*\n\n"
            "Connect to your OpenAI Agent Builder workflows and chat with them directly in Telegram.\n\n"
            "*Getting Started:*\n"
            "1. Copy your workflow code from Agent Builder and save it as a `.py` or `.txt` file\n"
            "2. Use /upload to send the file and register your workflow\n"
            "3. Give your workflow a name when prompted\n"
            "4. Start chatting!\n\n"
            "Use /help to see all available commands.",
            parse_mode="Markdown"
        )

    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /help command."""
        help_message = CommandLoader.format_help_message(self.commands)
        await update.message.reply_text(help_message, parse_mode="Markdown")

    async def upload(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /upload command."""
        await update.message.reply_text(
            "📤 Please upload your workflow file.\n\n"
            "Copy the code from Agent Builder, save it as a `.py` or `.txt` file, then send it here."
        )

        # Store state to expect file upload
        context.user_data["awaiting_workflow_upload"] = True
        context.user_data["workflow_update_name"] = None

    async def update(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /update command."""
        if not context.args:
            await update.message.reply_text(
                "⚠️ Please provide a workflow name.\n"
                "Usage: `/update <workflow_name>`",
                parse_mode="Markdown"
            )
            return

        workflow_name = context.args[0]

        # Check if workflow exists
        if not self.workflow_manager.workflow_exists(workflow_name):
            await update.message.reply_text(
                f"❌ Workflow '*{workflow_name}*' not found.\n"
                f"Use /workflows to see available workflows.",
                parse_mode="Markdown"
            )
            return

        await update.message.reply_text(
            f"📤 Please upload the updated workflow file for '*{workflow_name}*'.\n\n"
            f"Copy the updated code from Agent Builder, save as a `.py` or `.txt` file, and send it here.",
            parse_mode="Markdown"
        )

        # Store state to expect file upload for update
        context.user_data["awaiting_workflow_upload"] = True
        context.user_data["workflow_update_name"] = workflow_name

    async def handle_document(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle document uploads (workflow files)."""
        if not context.user_data.get("awaiting_workflow_upload"):
            await update.message.reply_text(
                "❌ I wasn't expecting a file. Use /upload or /update first."
            )
            return

        document = update.message.document

        # Validate file type
        if not document.file_name.endswith(Config.ACCEPTED_FILE_TYPES):
            accepted_types = ", ".join(Config.ACCEPTED_FILE_TYPES)
            await update.message.reply_text(
                f"❌ Please upload a workflow file with one of these extensions: {accepted_types}"
            )
            return

        try:
            # Download file
            file = await context.bot.get_file(document.file_id)
            file_content = await file.download_as_bytearray()

            # Check if this is an update or new upload
            is_update = context.user_data.get("workflow_update_name") is not None

            if is_update:
                # Update existing workflow - save immediately
                workflow_name = context.user_data["workflow_update_name"]

                success = self.workflow_manager.save_workflow(
                    workflow_name=workflow_name,
                    file_content=bytes(file_content),
                    is_update=True
                )

                if not success:
                    await update.message.reply_text(
                        "❌ Failed to save workflow. Please ensure the file contains valid workflow code with a `run_workflow()` function."
                    )
                    return

                await update.message.reply_text(
                    f"✅ Workflow '*{workflow_name}*' updated successfully!",
                    parse_mode="Markdown"
                )

                context.user_data["awaiting_workflow_upload"] = False
                context.user_data["workflow_update_name"] = None
            else:
                # New upload - store file content and ask for name
                context.user_data["pending_workflow_file"] = bytes(file_content)
                context.user_data["awaiting_workflow_upload"] = False
                context.user_data["awaiting_workflow_name"] = True

                await update.message.reply_text(
                    "✅ File received!\n\n"
                    "What would you like to name this workflow?\n"
                    "(Use lowercase letters, numbers, and underscores only)"
                )

        except Exception as e:
            logger.error("document_upload_failed", error=str(e))
            await update.message.reply_text(
                "❌ An error occurred while processing your file. Please try again."
            )

    async def workflows(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /workflows command."""
        workflows = self.workflow_manager.list_workflows()
        active_workflow = self.workflow_manager.get_active_workflow_name()

        if not workflows:
            await update.message.reply_text(
                "📋 You haven't registered any workflows yet.\n"
                "Use /upload to register your first workflow!"
            )
            return

        response = "📋 *Your Workflows:*\n\n"
        for wf in workflows:
            active_marker = "🔄 " if wf["name"] == active_workflow else "   "
            response += f"{active_marker}*{wf['name']}*\n"

        response += f"\n💬 Active: *{active_workflow or 'None'}*"

        await update.message.reply_text(response, parse_mode="Markdown")

    async def activate(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /activate command."""
        if not context.args:
            await update.message.reply_text(
                "⚠️ Please provide a workflow name.\n"
                "Usage: `/activate <workflow_name>`",
                parse_mode="Markdown"
            )
            return

        workflow_name = context.args[0]

        success = self.workflow_manager.activate_workflow(workflow_name)

        if not success:
            await update.message.reply_text(
                f"❌ Workflow '*{workflow_name}*' not found.\n"
                f"Use /workflows to see available workflows.",
                parse_mode="Markdown"
            )
            return

        await update.message.reply_text(
            f"✅ Workflow '*{workflow_name}*' activated!",
            parse_mode="Markdown"
        )

    async def remove(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /remove command."""
        if not context.args:
            await update.message.reply_text(
                "⚠️ Please provide a workflow name.\n"
                "Usage: `/remove <workflow_name>`",
                parse_mode="Markdown"
            )
            return

        workflow_name = context.args[0]

        success = self.workflow_manager.remove_workflow(workflow_name)

        if not success:
            await update.message.reply_text(
                f"❌ Workflow '*{workflow_name}*' not found.",
                parse_mode="Markdown"
            )
            return

        await update.message.reply_text(
            f"🗑️ Workflow '*{workflow_name}*' removed.",
            parse_mode="Markdown"
        )

    async def info(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /info command."""
        active_workflow_name = self.workflow_manager.get_active_workflow_name()

        if not active_workflow_name:
            await update.message.reply_text(
                "⚠️ No active workflow. Use /upload or /activate first."
            )
            return

        workflow = self.workflow_manager.get_active_workflow()

        if not workflow:
            await update.message.reply_text(
                "❌ Could not load active workflow."
            )
            return

        response = (
            f"📋 *Active Workflow:* {active_workflow_name}\n\n"
            f"*Name:* {workflow.name}\n"
            f"*Description:* {workflow.description}"
        )

        await update.message.reply_text(response, parse_mode="Markdown")

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle regular chat messages and workflow naming."""
        message_text = update.message.text

        # STATE: Expecting workflow name (after file upload)
        if context.user_data.get("awaiting_workflow_name") is True:
            workflow_name = message_text.strip().replace(" ", "_").lower()

            # Validate name
            if not workflow_name.replace("_", "").isalnum():
                await update.message.reply_text(
                    "❌ Workflow name can only contain letters, numbers, and underscores.\n"
                    "Please provide a valid name."
                )
                return

            # Check if already exists
            if self.workflow_manager.workflow_exists(workflow_name):
                await update.message.reply_text(
                    f"❌ Workflow '*{workflow_name}*' already exists.\n"
                    f"Use `/update {workflow_name}` to update it, or choose a different name.",
                    parse_mode="Markdown"
                )
                return

            # Get stored file content and save workflow
            file_content = context.user_data.get("pending_workflow_file")
            success = self.workflow_manager.save_workflow(
                workflow_name=workflow_name,
                file_content=file_content,
                is_update=False
            )

            # Clear state
            context.user_data["awaiting_workflow_name"] = False
            context.user_data["pending_workflow_file"] = None

            if not success:
                await update.message.reply_text(
                    "❌ Failed to save workflow. Please ensure the file contains valid workflow code with a `run_workflow()` function."
                )
                return

            # Activate if first workflow
            workflows = self.workflow_manager.list_workflows()
            if len(workflows) == 1:
                self.workflow_manager.activate_workflow(workflow_name)
                await update.message.reply_text(
                    f"✅ Workflow '*{workflow_name}*' created and activated!\n"
                    f"Ready to chat!",
                    parse_mode="Markdown"
                )
            else:
                await update.message.reply_text(
                    f"✅ Workflow '*{workflow_name}*' created!\n"
                    f"Use `/activate {workflow_name}` to switch to it.",
                    parse_mode="Markdown"
                )
            return

        # NORMAL STATE: Chat with active workflow
        active_workflow_name = self.workflow_manager.get_active_workflow_name()

        if not active_workflow_name:
            await update.message.reply_text(
                "⚠️ No active workflow. Please use /upload to register a workflow first!"
            )
            return

        workflow = self.workflow_manager.get_active_workflow()

        if not workflow:
            await update.message.reply_text(
                "❌ Could not load active workflow. Please try /activate again."
            )
            return

        try:
            # Send loading message immediately
            loading_message = await update.message.reply_text(
                f"🔄 *[{active_workflow_name}]*\n\n⏳ Processing your request...",
                parse_mode="Markdown"
            )

            # Run workflow directly
            response = await workflow.run(message_text)

            # Format response with workflow header
            formatted_response = f"🔄 *[{active_workflow_name}]*\n\n{response}"

            # Update the loading message with the actual response
            await loading_message.edit_text(
                formatted_response,
                parse_mode="Markdown"
            )

        except Exception as e:
            logger.error("message_handling_failed", error=str(e))

            # Try to update the loading message with error, or send new message if that fails
            try:
                if 'loading_message' in locals():
                    await loading_message.edit_text(
                        "❌ An error occurred while processing your message. Please try again."
                    )
                else:
                    await update.message.reply_text(
                        "❌ An error occurred while processing your message. Please try again."
                    )
            except Exception:
                # If editing fails, just send a new message
                await update.message.reply_text(
                    "❌ An error occurred while processing your message. Please try again."
                )
