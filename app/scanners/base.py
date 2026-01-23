"""Base scanner interface."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass


@dataclass
class ScanResult:
    """Result from a scanner operation."""

    success: bool
    message: str
    data: list | dict | None = None
    error: str | None = None


class ScannerBase(ABC):
    """Abstract base class for all scanners."""

    @abstractmethod
    async def execute(self) -> ScanResult:
        """Execute the scan operation.

        Returns:
            ScanResult with results or error details
        """

    @property
    @abstractmethod
    def name(self) -> str:
        """Get scanner identifier.

        Returns:
            Scanner name string
        """
