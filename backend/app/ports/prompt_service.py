from abc import ABC, abstractmethod

class PromptServicePort(ABC):
    """Port interface for resolving prompt resources (from files, databases, or third-party registry services)."""

    @abstractmethod
    def get_prompt(self, name: str) -> str:
        """Retrieves a prompt template by its identifier name.

        Args:
            name: The name of the prompt template (e.g. 'system_prompt').

        Returns:
            The raw string content of the prompt.
        """
        pass
