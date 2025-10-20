"""Dynamic workflow loading from exported Python files."""

import importlib.util
import sys
from pathlib import Path
from typing import Callable
from abc import ABC, abstractmethod

from pydantic import BaseModel

from ..utils.logger import get_logger

logger = get_logger(__name__)


class Workflow(ABC):
    """Abstract base class for workflows."""

    @abstractmethod
    async def run(self, user_input: str) -> str:
        """Run the workflow with user input.

        Args:
            user_input: User's message

        Returns:
            Workflow response
        """
        pass

    @property
    @abstractmethod
    def name(self) -> str:
        """Get workflow name."""
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """Get workflow description."""
        pass


class AgentBuilderWorkflow(Workflow):
    """Wrapper for Agent Builder exported workflows.

    Agent Builder exports contain a `run_workflow()` async function
    that orchestrates multiple agents with conditional logic.
    """

    def __init__(self, run_workflow_func: Callable, workflow_name: str):
        """Initialize Agent Builder workflow.

        Args:
            run_workflow_func: The exported run_workflow() function
            workflow_name: Name of the workflow
        """
        self._run_workflow = run_workflow_func
        self._name = workflow_name

    async def run(self, user_input: str) -> str:
        """Run the Agent Builder workflow.

        Args:
            user_input: User's message

        Returns:
            Workflow response
        """
        try:
            # Agent Builder workflows expect WorkflowInput with input_as_text
            # The function is defined in the module: class WorkflowInput(BaseModel): input_as_text: str
            # We need to dynamically create an instance

            # Get the WorkflowInput class from the function's module
            workflow_module = self._run_workflow.__module__
            module = sys.modules[workflow_module]

            if hasattr(module, "WorkflowInput"):
                WorkflowInput = module.WorkflowInput
                workflow_input = WorkflowInput(input_as_text=user_input)
            else:
                # Fallback: create a basic input dict
                class WorkflowInputFallback(BaseModel):
                    input_as_text: str
                workflow_input = WorkflowInputFallback(input_as_text=user_input)

            # Run the workflow and capture result
            result = await self._run_workflow(workflow_input)

            # Extract response from result
            # Agent Builder workflows return a dict with "output_text" key
            if isinstance(result, dict) and "output_text" in result:
                return result["output_text"]
            elif isinstance(result, str):
                return result
            elif result is None:
                return "Workflow completed with no output."
            else:
                return str(result)

        except Exception as e:
            logger.error("agent_builder_workflow_failed", workflow=self._name, error=str(e))
            raise

    @property
    def name(self) -> str:
        """Get workflow name."""
        return self._name

    @property
    def description(self) -> str:
        """Get workflow description."""
        return f"Agent Builder workflow: {self._name}"


class WorkflowLoader:
    """Load and validate exported Agent Builder workflows."""

    @staticmethod
    def load_workflow(file_path: Path) -> Workflow:
        """Dynamically load a workflow from a Python file.

        Only supports Agent Builder exports with `run_workflow()` async function.

        Args:
            file_path: Path to the workflow Python file

        Returns:
            Loaded Workflow instance

        Raises:
            ValueError: If file cannot be loaded or doesn't contain a valid workflow
            FileNotFoundError: If file doesn't exist
        """
        if not file_path.exists():
            raise FileNotFoundError(f"Workflow file not found: {file_path}")

        try:
            # Load module from file
            spec = importlib.util.spec_from_file_location(
                f"workflow_{file_path.stem}",
                file_path
            )
            if not spec or not spec.loader:
                raise ValueError(f"Cannot load module from {file_path}")

            module = importlib.util.module_from_spec(spec)
            sys.modules[spec.name] = module
            spec.loader.exec_module(module)

            # Check for Agent Builder pattern (run_workflow function)
            if hasattr(module, "run_workflow") and callable(module.run_workflow):
                workflow_name = file_path.stem
                logger.info("agent_builder_workflow_loaded", file_path=str(file_path), workflow=workflow_name)
                return AgentBuilderWorkflow(module.run_workflow, workflow_name)

            # No valid workflow found
            raise ValueError(
                "No run_workflow() function found in file. "
                "Please upload a workflow exported from OpenAI Agent Builder."
            )

        except Exception as e:
            logger.error("workflow_load_failed", file_path=str(file_path), error=str(e))
            raise ValueError(f"Failed to load workflow: {e}")

    @staticmethod
    def validate_workflow_file(file_path: Path) -> bool:
        """Validate that a file contains a loadable workflow.

        Args:
            file_path: Path to workflow file

        Returns:
            True if valid, False otherwise
        """
        try:
            WorkflowLoader.load_workflow(file_path)
            return True
        except Exception:
            return False
