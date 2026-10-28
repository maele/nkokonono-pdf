"""Common processor contract. Each tool implements this interface."""
from __future__ import annotations

import abc
from dataclasses import dataclass
from pathlib import Path

from app.services.file_service import StoredFile


class ProcessorError(Exception):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


@dataclass
class ProcessorOutput:
    path: Path
    display_name: str
    mime_type: str
    notes: str | None = None


class BaseProcessor(abc.ABC):
    tool_name: str = ""

    @abc.abstractmethod
    def validate(self, inputs: list[StoredFile], options: dict) -> None:
        """Raise ProcessorError if inputs or options are invalid."""

    @abc.abstractmethod
    def process(
        self, inputs: list[StoredFile], options: dict, output_dir: Path
    ) -> list[ProcessorOutput]:
        """Produce output files. Raise ProcessorError on failure."""

    def validate_output(self, output: ProcessorOutput) -> None:
        path = output.path
        if not path.exists() or not path.is_file():
            raise ProcessorError("OUTPUT_VALIDATION_FAILED", "The output file is missing.")
        if path.stat().st_size == 0:
            raise ProcessorError("OUTPUT_VALIDATION_FAILED", "The output file is empty.")
