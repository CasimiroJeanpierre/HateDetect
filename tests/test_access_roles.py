import pathlib
import sys
from types import SimpleNamespace
from unittest.mock import MagicMock

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from access_roles import access_role, can_use_private_history
from install_rbac import patch_app


def client_with(rows):
    client = MagicMock()
    client.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.return_value = SimpleNamespace(data=rows)
    return client


def test_admin_moderator_allowed():
    for role in ('admin', 'moderator'):
        client = client_with([{'role': role, 'active': True}])
        assert access_role(client, 'user-1') == role
        assert can_use_private_history(role)
        client.table.return_value.select.return_value.eq.assert_called_with('user_id', 'user-1')


def test_evaluator_has_no_history_privileges():
    assert access_role(client_with([{'role': 'evaluator', 'active': True}]), 'u1') == 'evaluator'
    assert not can_use_private_history('evaluator')


def test_non_authorized_and_revoked_denied():
    for row in ([], [{'role': 'moderator', 'active': False}], [{'role': 'admin', 'active': None}], [{'role': 'superuser', 'active': True}]):
        assert access_role(client_with(row), 'user-1') is None
    assert not can_use_private_history(None)


def test_bad_identity_and_fail_closed():
    assert access_role(None, 'user') is None
    assert access_role(client_with([]), '') is None
    assert access_role(client_with([]), None) is None
    c = MagicMock()
    c.table.side_effect = RuntimeError('BD indisponible')
    assert access_role(c, 'user-1') is None


def test_patch_source_guarded_and_idempotent():
    example = '''from auth_google import render_login, save_history, list_history, delete_history
client, uid = render_login()
    if uid:
        save = st.checkbox('Guardar clasificación en mi Historial persistente', value=False)
                if client is not None and uid:
        pass
    if client is not None and uid:
        pass
'''
    p = patch_app(example)
    assert 'from access_roles import access_role' in p
    assert p.count('and can_use_private_history(role)') == 3
    try:
        patch_app(p)
    except ValueError:
        pass
    else:
        raise AssertionError('No debe ser posible aplicar dos veces')


def test_patch_does_not_modify_unknown_app():
    try:
        patch_app('print("app incompatible")')
    except ValueError:
        pass
    else:
        raise AssertionError('El instalador no debe inventar cambios para versiones distintas')
