"""Command definitions loader."""

import json
from pathlib import Path
from typing import List, Dict

from .logger import get_logger

logger = get_logger(__name__)


class CommandLoader:
    """Load and format bot commands."""

    @staticmethod
    def load_commands(commands_file: Path = None) -> List[Dict[str, str]]:
        """Load commands from JSON file.

        Args:
            commands_file: Path to commands.json file

        Returns:
            List of command dicts with 'command' and 'description' keys
        """
        if commands_file is None:
            # Default to src directory
            commands_file = Path(__file__).parent.parent / "commands.json"

        try:
            with open(commands_file, "r") as f:
                commands = json.load(f)
            logger.info("commands_loaded", count=len(commands))
            return commands
        except Exception as e:
            logger.error("commands_load_failed", error=str(e))
            return []

    @staticmethod
    def format_help_message(commands: List[Dict[str, str]]) -> str:
        """Format commands into a help message.

        Args:
            commands: List of command definitions

        Returns:
            Formatted help message with Markdown
        """
        # Group commands
        workflow_commands = []
        conversation_commands = []
        general_commands = []

        for cmd in commands:
            command = cmd["command"]
            if command in ["upload", "update", "workflows", "activate", "remove"]:
                workflow_commands.append(cmd)
            elif command in ["info"]:
                conversation_commands.append(cmd)
            elif command in ["start"]:
                continue
            else:
                general_commands.append(cmd)

        # Build message
        message = "🔧 *Available Commands:*\n\n"

        if workflow_commands:
            message += "*Workflow Management:*\n"
            for cmd in workflow_commands:
                # Add usage hints for commands with parameters
                usage = ""
                if cmd["command"] in ["update", "activate", "remove"]:
                    usage = f" <name>"
                message += f"/{cmd['command']}{usage} - {cmd['description']}\n"
            message += "\n"

        if conversation_commands:
            message += "*Conversation:*\n"
            for cmd in conversation_commands:
                message += f"/{cmd['command']} - {cmd['description']}\n"
            message += "\n"

        if general_commands:
            message += "*General:*\n"
            for cmd in general_commands:
                message += f"/{cmd['command']} - {cmd['description']}\n"
            message += "\n"

        message += "💬 Just send a message to chat with your active workflow!"

        return message
