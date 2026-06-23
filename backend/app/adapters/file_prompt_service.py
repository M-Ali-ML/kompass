import logging
import os
from app.ports.prompt_service import PromptServicePort

logger = logging.getLogger("kompass.prompts")

class FilePromptService(PromptServicePort):
    """File-based prompt service adapter for resolving prompt assets from a local directory."""

    def __init__(self, prompts_dir: str):
        """Initializes the prompt service with a root directory.

        Args:
            prompts_dir: Absolute path to the directory containing prompt templates.
        """
        self.prompts_dir = prompts_dir

    def get_prompt(self, name: str) -> str:
        # Standardize on markdown extension for prompts (.md)
        file_path = os.path.join(self.prompts_dir, f"{name}.md")
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                return f.read()
        except Exception as e:
            logger.error(f"Failed to read prompt '{name}' from path '{file_path}': {e}")
            return "You are a helpful travel planning assistant."
