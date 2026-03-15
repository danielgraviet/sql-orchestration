from pathlib import Path

_SCHEMA_PATH = Path(__file__).parent / "schema.sql"


def get_schema_string() -> str:
    """Returns the full DDL from schema.sql as a plain string for prompt injection."""
    return _SCHEMA_PATH.read_text()
