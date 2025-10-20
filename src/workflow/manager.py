"""Workflow lifecycle management (single-user mode)."""

from pathlib import Path
from typing import Optional, Dict

from ..storage import WorkflowStore
from ..utils.logger import get_logger
from .loader import WorkflowLoader, Workflow

logger = get_logger(__name__)


class WorkflowManager:
    """Manage workflows (single-user mode)."""

    def __init__(self, workflow_store: WorkflowStore, workflows_dir: Path):
        """Initialize workflow manager.

        Args:
            workflow_store: WorkflowStore instance
            workflows_dir: Directory for storing workflow files
        """
        self.workflow_store = workflow_store
        self.workflows_dir = workflows_dir
        self.workflows_dir.mkdir(parents=True, exist_ok=True)

        # Cache loaded workflows
        self._workflow_cache: Dict[str, Workflow] = {}

        logger.info("workflow_manager_initialized", dir=str(workflows_dir))

    def save_workflow(
        self,
        workflow_name: str,
        file_content: bytes,
        is_update: bool = False
    ) -> bool:
        """Save an uploaded workflow file.

        Args:
            workflow_name: Name for the workflow
            file_content: Python file content
            is_update: Whether this is an update to existing workflow

        Returns:
            True if saved successfully, False otherwise
        """
        try:
            # Save file
            file_path = self.workflows_dir / f"{workflow_name}.py"
            file_path.write_bytes(file_content)

            # Validate it loads
            if not WorkflowLoader.validate_workflow_file(file_path):
                file_path.unlink()
                return False

            # Register in store
            self.workflow_store.add_workflow(
                workflow_name=workflow_name,
                file_path=str(file_path)
            )

            # Clear cache for this workflow
            if workflow_name in self._workflow_cache:
                del self._workflow_cache[workflow_name]

            action = "workflow_updated" if is_update else "workflow_saved"
            logger.info(action, workflow=workflow_name)
            return True

        except Exception as e:
            logger.error("workflow_save_failed", workflow=workflow_name, error=str(e))
            return False

    def load_workflow(self, workflow_name: str) -> Optional[Workflow]:
        """Load a workflow for execution.

        Args:
            workflow_name: Workflow name

        Returns:
            Loaded Workflow or None if not found
        """
        # Check cache first
        if workflow_name in self._workflow_cache:
            return self._workflow_cache[workflow_name]

        # Get workflow info
        workflow_info = self.workflow_store.get_workflow(workflow_name)
        if not workflow_info:
            return None

        try:
            # Load from file
            file_path = Path(workflow_info["file_path"])
            workflow = WorkflowLoader.load_workflow(file_path)

            # Cache it
            self._workflow_cache[workflow_name] = workflow

            return workflow

        except Exception as e:
            logger.error("workflow_load_failed", workflow=workflow_name, error=str(e))
            return None

    def activate_workflow(self, workflow_name: str) -> bool:
        """Activate a workflow.

        Args:
            workflow_name: Workflow name

        Returns:
            True if activated successfully, False otherwise
        """
        # Ensure workflow exists and can be loaded
        workflow = self.load_workflow(workflow_name)
        if not workflow:
            return False

        # Set as active
        self.workflow_store.set_active_workflow(workflow_name)

        logger.info("workflow_activated", workflow=workflow_name)
        return True

    def get_active_workflow(self) -> Optional[Workflow]:
        """Get the active workflow.

        Returns:
            Active Workflow or None
        """
        workflow_name = self.workflow_store.get_active_workflow()
        if not workflow_name:
            return None

        return self.load_workflow(workflow_name)

    def get_active_workflow_name(self) -> Optional[str]:
        """Get the active workflow name.

        Returns:
            Active workflow name or None
        """
        return self.workflow_store.get_active_workflow()

    def list_workflows(self) -> list:
        """List all workflows.

        Returns:
            List of workflow info dicts
        """
        return self.workflow_store.list_workflows()

    def workflow_exists(self, workflow_name: str) -> bool:
        """Check if a workflow exists.

        Args:
            workflow_name: Workflow name

        Returns:
            True if workflow exists, False otherwise
        """
        return self.workflow_store.workflow_exists(workflow_name)

    def remove_workflow(self, workflow_name: str) -> bool:
        """Remove a workflow.

        Args:
            workflow_name: Workflow name

        Returns:
            True if removed successfully, False otherwise
        """
        # Get workflow info
        workflow_info = self.workflow_store.get_workflow(workflow_name)
        if not workflow_info:
            return False

        try:
            # Delete file
            file_path = Path(workflow_info["file_path"])
            if file_path.exists():
                file_path.unlink()

            # Remove from store
            self.workflow_store.remove_workflow(workflow_name)

            # Clear cache
            if workflow_name in self._workflow_cache:
                del self._workflow_cache[workflow_name]

            logger.info("workflow_removed", workflow=workflow_name)
            return True

        except Exception as e:
            logger.error("workflow_remove_failed", workflow=workflow_name, error=str(e))
            return False

    def get_workflow_info(self, workflow_name: str) -> Optional[Dict]:
        """Get workflow information.

        Args:
            workflow_name: Workflow name

        Returns:
            Workflow info dict or None
        """
        return self.workflow_store.get_workflow(workflow_name)
