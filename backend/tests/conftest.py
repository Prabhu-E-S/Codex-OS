import pytest
from backend.main import _migrate_schema

@pytest.fixture(scope="session", autouse=True)
def run_schema_migrations():
    _migrate_schema()
