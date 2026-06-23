from abc import ABC, abstractmethod

class MathServicePort(ABC):
    @abstractmethod
    async def add(self, a: int, b: int) -> int:
        """Add two numbers using the math service."""
        pass
