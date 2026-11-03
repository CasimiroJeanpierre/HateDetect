"""Pruebas offline de validaciones y aislamiento del módulo de historial.

El aislamiento real RLS requiere usuarios de prueba, no se simula como aprobado.
"""
import pathlib
import sys
from unittest.mock import MagicMock

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

# No Streamlit installed in the test container; minimal stubbing of import-only API.
if 'streamlit' not in sys.modules:
    import types
    st = types.ModuleType('streamlit')
    st.session_state = {}
    sys.modules['streamlit'] = st
if 'supabase' not in sys.modules:
    import types
    sb = types.ModuleType('supabase')
    sb.create_client = MagicMock()
    sys.modules['supabase'] = sb

from auth_google import save_history, list_history, delete_history


def test_unauthenticated_requests_blocked():
    with pytest.raises(PermissionError):
        save_history(None, None, 'prueba', 'Neutro', 1.0)
    with pytest.raises(PermissionError):
        list_history(None, None)
    with pytest.raises(PermissionError):
        delete_history(None, None, 'record-id')


def test_rejects_invalid_prediction_and_empty_text():
    c = MagicMock()
    with pytest.raises(ValueError):
        save_history(c, 'user-1', 'x', 'Otra', 1)
    with pytest.raises(ValueError):
        save_history(c, 'user-1', '', 'Odio', 1)


def test_insert_does_not_trust_or_send_user_id():
    client = MagicMock()
    save_history(client, 'user-1', 'mensaje de prueba', 'Neutro', 1.2239)
    payload = client.table.return_value.insert.call_args[0][0]
    assert 'user_id' not in payload
    assert payload['inference_ms'] == 1.224
    client.table.assert_called_with('hatedetect_history')


def test_query_defense_in_depth_filters_uid():
    client = MagicMock()
    client.table.return_value.select.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value.data = []
    list_history(client, 'user-A')
    client.table.return_value.select.return_value.eq.assert_called_with('user_id', 'user-A')


def test_delete_filters_owner_and_record():
    client = MagicMock()
    delete_history(client, 'user-A', 'record-123')
    client.table.return_value.delete.return_value.eq.assert_called_with('user_id', 'user-A')
    client.table.return_value.delete.return_value.eq.return_value.eq.assert_called_with('id', 'record-123')
