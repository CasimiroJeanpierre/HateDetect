"""Incorpora el chequeo de autorización a app.py (rama de desarrollo).

NO modifica secrets, Supabase ni GitHub. Requiere exactamente el app.py
resultante del PR #1; si difiere, cancela sin escribir cambios.
"""

from pathlib import Path

HERE = Path(__file__).resolve().parent


def patch_app(source: str) -> str:
    insertion = 'from auth_google import render_login, save_history, list_history, delete_history\n'
    new_imports = insertion + 'from access_roles import access_role, can_use_private_history\n'
    if new_imports in source:
        raise ValueError('El control de roles ya fue instalado. No ejecutes el instalador dos veces.')
    old_login = 'client, uid = render_login()\n'
    new_login = '''client, uid = render_login()
role = access_role(client, uid)
if uid:
    if role is None:
        st.sidebar.error('Cuenta sin autorización para funciones privadas de HateDetect.')
    elif role == 'evaluator':
        st.sidebar.info('Rol Evaluador: funciones de anotación aún no publicadas.')
    else:
        st.sidebar.success('Acceso autorizado: ' + ('Administrador' if role == 'admin' else 'Moderador'))
'''
    old_checkbox = "    if uid:\n        save = st.checkbox('Guardar clasificación en mi Historial persistente', value=False)"
    new_checkbox = "    if uid and can_use_private_history(role):\n        save = st.checkbox('Guardar clasificación en mi Historial persistente', value=False)"
    old_guard = 'if client is not None and uid:'
    new_guard = 'if client is not None and uid and can_use_private_history(role):'

    changes = [
        (insertion, new_imports, 1),
        (old_login, new_login, 1),
        (old_checkbox, new_checkbox, 1),
        (old_guard, new_guard, 2),
    ]
    output = source
    for old, new, expected_count in changes:
        actual = output.count(old)
        if actual != expected_count:
            raise ValueError(f'Patrón de app.py no compatible: esperadas {expected_count} coincidencias, se encontraron {actual} para {old!r}. No se modificó el archivo.')
        output = output.replace(old, new)
    return output


def main():
    target = HERE / 'app.py'
    if not target.is_file():
        raise SystemExit('Falta app.py. Extrae el paquete dentro de la carpeta raíz de HateDetect.')
    original = target.read_text(encoding='utf-8')
    try:
        updated = patch_app(original)
    except ValueError as exc:
        raise SystemExit(str(exc))
    # Escritura solo después de validar todos los patrones.
    target.write_text(updated, encoding='utf-8', newline='\n')
    print('app.py actualizado: roles y Historial privado bajo autorización.')
    print('Pendiente: probar en rama, y después aplicar supabase_rls_roles.sql.')


if __name__ == '__main__':
    main()
