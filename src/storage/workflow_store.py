"""Simple JSON-based workflow storage (single-user)."""

import json
from pathlib import Path
from typing import Optional, List, Dict, Any

from ..utils.logger import get_logger

logger = get_logger(__name__)


class WorkflowStore:
    """Simple JSON-based storage for workflows (single-user mode)."""

    def __init__(self, config_path: Path):
        """Initialize workflow store.

        Args:
            config_path: Path to JSON config file
        """
        self.config_path = config_path
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        self._ensure_config()
        logger.info("workflow_store_initialized", path=str(config_path))

    def _ensure_config(self) -> None:
        """Ensure config file exists with default structure."""
        if not self.config_path.exists():
            self._save_config({
                "active": None,
                "workflows": {}
            })

    def _load_config(self) -> Dict[str, Any]:
        """Load config from JSON file."""
        try:
            with open(self.config_path, "r") as f:
                return json.load(f)
        except Exception as e:
            logger.error("config_load_failed", error=str(e))
            return {"active": None, "workflows": {}}

    def _save_config(self, config: Dict[str, Any]) -> None:
        """Save config to JSON file."""
        try:
            with open(self.config_path, "w") as f:
                json.dump(config, f, indent=2)
        except Exception as e:
            logger.error("config_save_failed", error=str(e))

    def get_active_workflow(self) -> Optional[str]:
        """Get the active workflow name.

        Returns:
            Active workflow name or None
        """
        config = self._load_config()
        return config.get("active")

    def set_active_workflow(self, workflow_name: Optional[str]) -> None:
        """Set the active workflow.

        Args:
            workflow_name: Workflow name to activate (None to deactivate)
        """
        config = self._load_config()
        config["active"] = workflow_name
        self._save_config(config)
        logger.info("active_workflow_set", workflow=workflow_name)

    def add_workflow(
        self,
        workflow_name: str,
        file_path: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """Register a workflow.

        Args:
            workflow_name: Workflow name
            file_path: Path to workflow Python file
            metadata: Optional workflow metadata
        """
        config = self._load_config()
        config["workflows"][workflow_name] = {
            "file_path": file_path,
            "metadata": metadata or {}
        }
        self._save_config(config)
        logger.info("workflow_registered", workflow=workflow_name)

    def get_workflow(self, workflow_name: str) -> Optional[Dict[str, Any]]:
        """Get workflow info.

        Args:
            workflow_name: Workflow name

        Returns:
            Workflow info dict or None
        """
        config = self._load_config()
        workflow_data = config["workflows"].get(workflow_name)
        if workflow_data:
            return {
                "name": workflow_name,
                "file_path": workflow_data["file_path"],
                "metadata": workflow_data.get("metadata", {})
            }
        return None

    def list_workflows(self) -> List[Dict[str, Any]]:
        """List all workflows.

        Returns:
            List of workflow info dicts
        """
        config = self._load_config()
        workflows = []
        for name, data in config["workflows"].items():
            workflows.append({
                "name": name,
                "file_path": data["file_path"],
                "metadata": data.get("metadata", {})
            })
        return workflows

    def remove_workflow(self, workflow_name: str) -> bool:
        """Remove a workflow.

        Args:
            workflow_name: Workflow name

        Returns:
            True if workflow was removed, False if not found
        """
        config = self._load_config()
        if workflow_name in config["workflows"]:
            del config["workflows"][workflow_name]

            # Clear active if removing active workflow
            if config.get("active") == workflow_name:
                config["active"] = None

            self._save_config(config)
            logger.info("workflow_removed", workflow=workflow_name)
            return True
        return False

    def workflow_exists(self, workflow_name: str) -> bool:
        """Check if a workflow exists.

        Args:
            workflow_name: Workflow name

        Returns:
            True if workflow exists, False otherwise
        """
        config = self._load_config()
        return workflow_name in config["workflows"]
