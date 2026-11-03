"""Instala Clasificación por lotes en el app.py vigente de HateDetect (main post RBAC).

Valida anclas exactas antes de escribir. No modifica autenticación ni Historial.
"""
from pathlib import Path

IMPORT_ANCHOR = 'from access_roles import access_role, can_use_private_history\n'
NAV_ANCHOR = "page = st.sidebar.radio('Sección', ['Clasificación', 'Reportes', 'Historial'])"
REPORT_ANCHOR = "elif page == 'Reportes':\n"


def patch_app(src: str) -> str:
    if 'Clasificación por lotes' in src or 'render_batch_page' in src:
        raise ValueError('La clasificación por lotes ya parece estar instalada.')
    for anchor in (IMPORT_ANCHOR, NAV_ANCHOR, REPORT_ANCHOR):
        occurrences = src.count(anchor)
        if occurrences != 1:
            raise ValueError(f'Código de app.py incompatible: se esperó una ancla, hay {occurrences}: {anchor!r}.')
    src = src.replace(IMPORT_ANCHOR,
                      IMPORT_ANCHOR + 'from batch_classification import render_batch_page\n', 1)
    src = src.replace(NAV_ANCHOR,
                      "page = st.sidebar.radio('Sección', ['Clasificación', 'Clasificación por lotes', 'Reportes', 'Historial'])", 1)
    src = src.replace(REPORT_ANCHOR,
                      "elif page == 'Clasificación por lotes':\n"
                      "    render_batch_page(model, clean_for_inference)\n\n"
                      + REPORT_ANCHOR, 1)
    return src


def main():
    root = Path(__file__).resolve().parent
    app = root / 'app.py'
    module = root / 'batch_classification.py'
    if not app.is_file() or not module.is_file():
        raise SystemExit('Falta app.py o batch_classification.py. Extrae todo el ZIP en la carpeta HateDetect correcta.')
    try:
        source = app.read_text(encoding='utf-8-sig')
        updated = patch_app(source)
    except (OSError, ValueError) as exc:
        raise SystemExit(f'No se modificó app.py: {exc}') from exc
    temp = root / 'app.py.batch-tmp'
    temp.write_text(updated, encoding='utf-8')
    temp.replace(app)
    print('Instalado: Clasificación por lotes integrada en app.py.')
    print('No se modificaron credenciales, Google Auth, roles RBAC ni políticas RLS.')
    print('Pendiente: ejecutar pruebas y desplegar primero en rama de pruebas.')


if __name__ == '__main__':
    main()
