from unittest.mock import MagicMock

import pytest

from access_roles import access_role, can_use_private_history
from auth_google import save_history, list_history, delete_history


def test_history_roles():
    assert can_use_private_history("admin")
    assert can_use_private_history("moderator")
    assert not can_use_private_history("evaluator")
    assert not can_use_private_history(None)


def test_save_requires_session():
    with pytest.raises(PermissionError):
        save_history(None, None, "texto", "Neutro", 1.0)


def test_read_and_delete_require_session():
    with pytest.raises(PermissionError):
        list_history(None, None)
    with pytest.raises(PermissionError):
        delete_history(None, None, "registro-1")


def test_reject_invalid_category():
    with pytest.raises(ValueError):
        save_history(MagicMock(), "usuario-A", "texto", "Otra", 1.0)


def test_reject_invalid_text_length():
    for text in ("", "a" * 2001):
        with pytest.raises(ValueError):
            save_history(MagicMock(), "usuario-A", text, "Neutro", 1.0)


def test_reject_unknown_model():
    with pytest.raises(ValueError):
        save_history(
            MagicMock(), "usuario-A", "texto",
            "Neutro", 1.0, model_name="modelo-no-autorizado"
        )


def test_insert_uses_database_identity():
    client = MagicMock()

    save_history(
        client, "usuario-A", "texto sintetico",
        "Neutro", 1.0, model_name="TF-IDF + LR (v3)"
    )

    payload = client.table.return_value.insert.call_args.args[0]

    assert "user_id" not in payload
    assert payload["model_name"] == "TF-IDF + LR (v3)"


def test_read_filters_by_user():
    client = MagicMock()
    list_history(client, "usuario-A")

    query = client.table.return_value.select.return_value
    query.eq.assert_called_with("user_id", "usuario-A")


def test_delete_filters_by_user_and_record():
    client = MagicMock()
    delete_history(client, "usuario-A", "registro-1")

    query = client.table.return_value.delete.return_value
    query.eq.assert_called_with("user_id", "usuario-A")
    query.eq.return_value.eq.assert_called_with(
        "id", "registro-1"
    )


def test_role_lookup_fails_closed():
    client = MagicMock()
    client.table.side_effect = RuntimeError("Conexion no disponible")

    assert access_role(client, "usuario-A") is None
