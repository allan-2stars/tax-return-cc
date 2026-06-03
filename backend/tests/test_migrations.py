import importlib.util
import sys
import types
from pathlib import Path

import sqlalchemy as sa


def _load_revision(filename: str):
    path = Path(__file__).resolve().parents[1] / "alembic" / "versions" / filename
    spec = importlib.util.spec_from_file_location(path.stem, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    existing_alembic = sys.modules.get("alembic")
    fake_alembic = types.ModuleType("alembic")
    fake_alembic.op = None
    sys.modules["alembic"] = fake_alembic
    try:
        spec.loader.exec_module(module)
    finally:
        if existing_alembic is None:
            sys.modules.pop("alembic", None)
        else:
            sys.modules["alembic"] = existing_alembic
    return module


class _SqliteOps:
    def __init__(self, connection):
        self.connection = connection

    def get_bind(self):
        return self.connection

    def add_column(self, table_name: str, column: sa.Column) -> None:
        nullable = "" if column.nullable else " NOT NULL"
        default = ""
        if column.server_default is not None:
            default_value = column.server_default.arg
            default = f" DEFAULT '{default_value}'"
        column_type = column.type.compile(dialect=self.connection.dialect)
        self.connection.exec_driver_sql(
            f"ALTER TABLE {table_name} ADD COLUMN {column.name} {column_type}{nullable}{default}"
        )

    def alter_column(self, *args, **kwargs) -> None:
        return None

    def drop_column(self, *args, **kwargs) -> None:
        return None


def test_workspace_evidence_reconcile_migration_is_idempotent_for_existing_columns():
    revision = _load_revision("a1d2e3f4b5c6_add_workspace_evidence_reconcile_fields.py")
    engine = sa.create_engine("sqlite:///:memory:")
    metadata = sa.MetaData()
    sa.Table(
        "workspaces",
        metadata,
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("name", sa.String(255)),
        sa.Column("financial_year", sa.String(10)),
        sa.Column("evidence_reconciled_at", sa.DateTime(timezone=True), nullable=True),
    )
    metadata.create_all(engine)

    with engine.begin() as connection:
        revision.op = _SqliteOps(connection)
        revision.upgrade()
        columns = {column["name"] for column in sa.inspect(connection).get_columns("workspaces")}

    assert "evidence_reconciled_at" in columns
    assert "evidence_reconcile_status" in columns
    assert "evidence_reconcile_meta" in columns
