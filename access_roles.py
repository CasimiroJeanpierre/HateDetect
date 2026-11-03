"""Control de acceso por lista permitida y rol para HateDetect.

No es un sustituto de RLS: las políticas de Supabase deben comprobar
la autorización de forma independiente para cada operación de BD.
"""

from __future__ import annotations

ALLOWED_ROLES = frozenset({'admin', 'moderator', 'evaluator'})
PRIVATE_HISTORY_ROLES = frozenset({'admin', 'moderator'})


def access_role(client, uid):
    """Consulta el permiso actual. Ante error o usuario no registrado, deniega."""
    if client is None or not isinstance(uid, str) or not uid:
        return None
    try:
        response = (
            client.table('hatedetect_authorized_users')
            .select('role,active')
            .eq('user_id', uid)
            .limit(1)
            .execute()
        )
        records = response.data or []
        if not isinstance(records, list) or len(records) != 1:
            return None
        row = records[0]
        if not isinstance(row, dict) or row.get('active') is not True:
            return None
        role = row.get('role')
        return role if role in ALLOWED_ROLES else None
    except Exception:
        # Nunca permitir el acceso ante errores de conexión, RLS o sesión.
        return None


def can_use_private_history(role):
    """Solo los roles admin y moderator pueden conservar/modificar Historial."""
    return role in PRIVATE_HISTORY_ROLES
