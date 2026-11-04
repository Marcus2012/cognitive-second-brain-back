from unittest.mock import Mock, patch

from sqlalchemy.schema import CreateSchema

from app.db import ensure_schema


def test_existing_schema_does_not_require_database_create_privilege():
    connection = Mock()
    with patch("app.db.inspect") as inspect:
        inspect.return_value.has_schema.return_value = True
        ensure_schema(connection, "cognitive_brain")
        inspect.return_value.has_schema.assert_called_once_with("cognitive_brain")
    connection.execute.assert_not_called()


def test_new_database_creates_missing_application_schema():
    connection = Mock()
    with patch("app.db.inspect") as inspect:
        inspect.return_value.has_schema.return_value = False
        ensure_schema(connection, "cognitive_brain")
    statement = connection.execute.call_args.args[0]
    assert isinstance(statement, CreateSchema)
    assert statement.element == "cognitive_brain"
    assert statement.if_not_exists
