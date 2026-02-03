"""
Importers for MODE II data files.

Handles dynamic table creation and data insertion for landslide monitoring data.
"""

from typing import Any
from uuid import UUID

from django.db import connection


def get_table_name(uuid: UUID, data_ref_name: str) -> str:
    """
    Generate table name from UUID and data reference name.

    Format: import_{uuid_no_hyphens}_{data_ref_name}

    Args:
        uuid: The dataset UUID
        data_ref_name: The data reference name (e.g., 'falda', 'pioggia')

    Returns:
        Sanitized table name
    """
    uuid_clean = str(uuid).replace('-', '')
    # Sanitize data_ref_name to only allow alphanumeric and underscore
    safe_ref_name = ''.join(c if c.isalnum() or c == '_' else '_' for c in data_ref_name.lower())
    return f"import_{uuid_clean}_{safe_ref_name}"


def create_import_table(uuid: UUID, data_ref_name: str) -> str:
    """
    Create a new import table for the given dataset and data type.

    Schema:
    - id: SERIAL PRIMARY KEY
    - index: INTEGER NOT NULL
    - value: DOUBLE PRECISION NOT NULL
    - created_at: TIMESTAMP WITH TIME ZONE DEFAULT NOW()

    Args:
        uuid: The dataset UUID
        data_ref_name: The data reference name

    Returns:
        The created table name
    """
    table_name = get_table_name(uuid, data_ref_name)

    with connection.cursor() as cursor:
        # Drop table if exists (for reimport scenarios)
        cursor.execute(f'DROP TABLE IF EXISTS "{table_name}"')

        # Create new table
        cursor.execute(f'''
            CREATE TABLE "{table_name}" (
                id SERIAL PRIMARY KEY,
                index INTEGER NOT NULL,
                value DOUBLE PRECISION NOT NULL,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
            )
        ''')

    return table_name


def import_data(uuid: UUID, data_ref_name: str, data: list[dict[str, Any]]) -> dict[str, Any]:
    """
    Import validated data into a new table.

    Args:
        uuid: The dataset UUID
        data_ref_name: The data reference name
        data: List of dictionaries with 'index' and 'value' keys

    Returns:
        Dictionary with import result details
    """
    table_name = create_import_table(uuid, data_ref_name)

    with connection.cursor() as cursor:
        # Insert all rows
        for row in data:
            cursor.execute(
                f'INSERT INTO "{table_name}" (index, value) VALUES (%s, %s)',
                [row['index'], row['value']]
            )

    return {
        'table_name': table_name,
        'rows_imported': len(data),
    }
