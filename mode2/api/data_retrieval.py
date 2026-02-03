"""
Data retrieval for MODE II imported datasets.

Retrieves data from dynamically created import tables for calibration and prevision calculations.
"""

from uuid import UUID

from django.db import connection

from .importers import get_table_name


class DataNotFoundError(Exception):
    """Raised when requested data table does not exist."""

    def __init__(self, message_it: str, message_en: str):
        self.message_it = message_it
        self.message_en = message_en
        super().__init__(message_en)


def table_exists(table_name: str) -> bool:
    """
    Check if a table exists in the database.

    Args:
        table_name: The name of the table to check

    Returns:
        True if the table exists, False otherwise
    """
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables
                WHERE table_name = %s
            )
        """, [table_name])
        return cursor.fetchone()[0]


def get_imported_data(uuid: UUID, data_type: str) -> list[tuple[int, float]]:
    """
    Retrieve imported data from a dynamic table.

    Args:
        uuid: The dataset UUID
        data_type: The data type ('pioggia', 'falda', 'spostamento')

    Returns:
        List of (index, value) tuples ordered by index

    Raises:
        DataNotFoundError: If the table doesn't exist for this dataset
    """
    table_name = get_table_name(uuid, data_type)

    if not table_exists(table_name):
        data_type_names = {
            'pioggia': ('pioggia', 'rainfall'),
            'falda': ('falda', 'water table'),
            'spostamento': ('spostamento', 'displacement'),
        }
        name_it, name_en = data_type_names.get(data_type, (data_type, data_type))
        raise DataNotFoundError(
            f"Dati di {name_it} non trovati per questo dataset.",
            f"{name_en.capitalize()} data not found for this dataset."
        )

    with connection.cursor() as cursor:
        cursor.execute(f'''
            SELECT index, value
            FROM "{table_name}"
            ORDER BY index ASC
        ''')
        rows = cursor.fetchall()

    return [(row[0], row[1]) for row in rows]


def get_all_imported_data(uuid: UUID) -> dict[str, list[tuple[int, float]]]:
    """
    Retrieve all imported data types for a dataset.

    Args:
        uuid: The dataset UUID

    Returns:
        Dictionary with keys 'pioggia', 'falda', 'spostamento' containing
        lists of (index, value) tuples. Missing data types will have empty lists.
    """
    result = {}
    for data_type in ['pioggia', 'falda', 'spostamento']:
        try:
            result[data_type] = get_imported_data(uuid, data_type)
        except DataNotFoundError:
            result[data_type] = []
    return result


def check_required_data(uuid: UUID, required_types: list[str]) -> list[dict[str, str]]:
    """
    Check if all required data types exist for a dataset.

    Args:
        uuid: The dataset UUID
        required_types: List of required data types

    Returns:
        List of error dictionaries for missing data types (empty if all exist)
    """
    errors = []
    data_type_names = {
        'pioggia': ('pioggia', 'rainfall'),
        'falda': ('falda', 'water table'),
        'spostamento': ('spostamento', 'displacement'),
    }

    for data_type in required_types:
        table_name = get_table_name(uuid, data_type)
        if not table_exists(table_name):
            name_it, name_en = data_type_names.get(data_type, (data_type, data_type))
            errors.append({
                'it': f"Dati di {name_it} non trovati per questo dataset.",
                'en': f"{name_en.capitalize()} data not found for this dataset."
            })

    return errors
