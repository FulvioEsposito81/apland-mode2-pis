"""
Validators for MODE II data files.

Validates tab-delimited files with comma decimal separator format used for
landslide monitoring data (falda, pioggia, spostamento).
"""

from io import StringIO
from typing import Any

import pandas as pd


class ValidationResult:
    """Container for validation results with bilingual messages."""

    def __init__(self):
        self.valid = True
        self.errors: list[dict[str, str]] = []
        self.warnings: list[dict[str, str]] = []
        self.data: list[dict[str, Any]] | None = None

    def add_error(self, message_it: str, message_en: str) -> None:
        """Add an error message (invalidates the result)."""
        self.valid = False
        self.errors.append({'it': message_it, 'en': message_en})

    def add_warning(self, message_it: str, message_en: str) -> None:
        """Add a warning message (does not invalidate)."""
        self.warnings.append({'it': message_it, 'en': message_en})

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON response."""
        result = {
            'valid': self.valid,
            'errors': self.errors,
            'warnings': self.warnings,
        }
        if self.data is not None:
            result['data'] = self.data
        return result


def parse_european_float(value: str) -> float:
    """Parse a European-style float (comma as decimal separator)."""
    return float(value.replace(',', '.'))


def validate_data_file(file_content: str | bytes) -> ValidationResult:
    """
    Validate a MODE II data file.

    Expected format:
    - Tab-delimited, no headers
    - Column 1: Integer index (0-11)
    - Column 2: Float with comma decimal separator
    - Exactly 12 rows

    Args:
        file_content: The file content as string or bytes

    Returns:
        ValidationResult with valid status, errors, warnings, and parsed data
    """
    result = ValidationResult()

    # Convert bytes to string if needed
    if isinstance(file_content, bytes):
        try:
            file_content = file_content.decode('utf-8')
        except UnicodeDecodeError:
            try:
                file_content = file_content.decode('latin-1')
            except UnicodeDecodeError:
                result.add_error(
                    "Impossibile decodificare il file. Usare codifica UTF-8 o Latin-1.",
                    "Unable to decode file. Use UTF-8 or Latin-1 encoding."
                )
                return result

    # Remove BOM if present
    if file_content.startswith('\ufeff'):
        file_content = file_content[1:]

    # Split into lines and filter empty lines
    lines = [line.strip() for line in file_content.strip().split('\n') if line.strip()]

    # Check row count
    if len(lines) != 12:
        result.add_error(
            f"Il file deve contenere esattamente 12 righe. Trovate: {len(lines)}",
            f"File must contain exactly 12 rows. Found: {len(lines)}"
        )

    # Parse and validate each row
    parsed_data = []
    for i, line in enumerate(lines):
        # Split by tab
        parts = line.split('\t')

        if len(parts) != 2:
            result.add_error(
                f"Riga {i + 1}: formato non valido. Attesi 2 campi separati da tab, trovati {len(parts)}",
                f"Row {i + 1}: invalid format. Expected 2 tab-separated fields, found {len(parts)}"
            )
            continue

        # Validate index
        try:
            index = int(parts[0].strip())
            if index != i:
                result.add_error(
                    f"Riga {i + 1}: indice non sequenziale. Atteso {i}, trovato {index}",
                    f"Row {i + 1}: non-sequential index. Expected {i}, found {index}"
                )
        except ValueError:
            result.add_error(
                f"Riga {i + 1}: indice non valido '{parts[0].strip()}'. Deve essere un intero.",
                f"Row {i + 1}: invalid index '{parts[0].strip()}'. Must be an integer."
            )
            continue

        # Validate and parse value
        try:
            value = parse_european_float(parts[1].strip())
            parsed_data.append({'index': index, 'value': value})
        except ValueError:
            result.add_error(
                f"Riga {i + 1}: valore numerico non valido '{parts[1].strip()}'",
                f"Row {i + 1}: invalid numeric value '{parts[1].strip()}'"
            )

    # Store parsed data if validation passed
    if result.valid:
        result.data = parsed_data

    return result
