import csv
import io
import pathlib
import sys

import pandas as pd
import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from batch_classification import (BatchCSVError, MAX_CSV_BYTES, classify_rows,
                                  export_csv_bytes, read_comments_csv)
from install_batch import patch_app


class DummyModel:
    def __init__(self, labels=None):
        self.labels = labels
        self.calls = []

    def predict(self, texts):
        self.calls.append(list(texts))
        return self.labels if self.labels is not None else ['Neutro'] * len(texts)


def cleaner(s):
    return ' '.join(s.split())


def test_utf8_bom_semicolon_and_quoted_commas():
    rows = read_comments_csv('comentario;id\n"Hola, mundo";1\n"¡Bien!";2\n'.encode('utf-8-sig'))
    assert [row['comentario'] for row in rows] == ['Hola, mundo', '¡Bien!']


def test_english_and_single_column():
    assert read_comments_csv(b'comment\nHello\nWorld\n')[0]['comentario'] == 'Hello'


def test_inconsistent_or_wrong_headers():
    with pytest.raises(BatchCSVError):
        read_comments_csv(b'generacion\nMillennial\n')
    with pytest.raises(BatchCSVError):
        read_comments_csv(b'comentario,otro\nhola,uno,sobra\n')
    with pytest.raises(BatchCSVError):
        read_comments_csv(b'comentario,texto\nhola,otro\n')


def test_encoding_and_empty():
    with pytest.raises(BatchCSVError):
        read_comments_csv(b'')
    with pytest.raises(BatchCSVError):
        read_comments_csv(b'comentario\n\xff\n')
    with pytest.raises(BatchCSVError):
        read_comments_csv(b'comentario\n' + b'a' * MAX_CSV_BYTES)


def test_row_limit():
    src = 'comentario\n' + 'texto\n' * 501
    with pytest.raises(BatchCSVError):
        read_comments_csv(src.encode())
    assert len(read_comments_csv(('comentario\n' + 'texto\n' * 500).encode())) == 500


def test_vectorization_preserves_order_and_invalid_rows():
    rows = [{'fila': 2, 'comentario': ' Hola '},
            {'fila': 3, 'comentario': '   '},
            {'fila': 4, 'comentario': 'Malo'},
            {'fila': 5, 'comentario': 'a'*2001}]
    model = DummyModel(['Neutro', 'Ofensivo'])
    results = classify_rows(rows, model, cleaner)
    assert model.calls == [['Hola', 'Malo']]
    assert results['valid'] == 2 and results['invalid'] == 2
    assert results['counts'] == {'Odio': 0, 'Ofensivo': 1, 'Neutro': 1}
    assert results['table']['Categoría'].tolist() == ['Neutro', '', 'Ofensivo', '']
    assert results['table']['Fila'].tolist() == [2, 3, 4, 5]


def test_all_invalid_does_not_invoke_model():
    model = DummyModel()
    result = classify_rows([{'fila':2,'comentario':'  '}], model, cleaner)
    assert result['valid'] == 0
    assert model.calls == []


def test_rejects_unknown_model_labels():
    with pytest.raises(ValueError):
        classify_rows([{'fila': 2, 'comentario': 'Hola'}], DummyModel(['Otra']), cleaner)


def test_excel_formula_injection_is_escaped():
    original = '=HYPERLINK("http://example.test","clic")'
    results = classify_rows([{'fila':2, 'comentario':original}], DummyModel(), cleaner)
    out = export_csv_bytes(results['table'])
    reader = csv.DictReader(io.StringIO(out.decode('utf-8-sig')))
    first = next(reader)
    assert first['Comentario'].startswith("'=")
    assert first['Texto procesado'].startswith("'=")


def test_regular_text_survives_export():
    table = pd.DataFrame([{'Fila':2, 'Comentario':'Hola, mundo', 'Texto procesado':'Hola, mundo',
                           'Categoría':'Neutro', 'Estado':'Clasificada'}])
    data = export_csv_bytes(table).decode('utf-8-sig')
    assert '"Hola, mundo"' in data


def test_source_patch_does_not_touch_auth_or_history():
    base = '''from access_roles import access_role, can_use_private_history
page = st.sidebar.radio('Sección', ['Clasificación', 'Reportes', 'Historial'])
if page == 'Clasificación':
    pass
elif page == 'Reportes':
    pass
else:
    pass
'''
    changed = patch_app(base)
    assert 'render_batch_page(model, clean_for_inference)' in changed
    assert "['Clasificación', 'Clasificación por lotes', 'Reportes', 'Historial']" in changed
    assert "elif page == 'Reportes':" in changed
    assert 'from access_roles import access_role, can_use_private_history' in changed
    with pytest.raises(ValueError):
        patch_app(changed)


def test_source_patch_refuses_unknown_app():
    with pytest.raises(ValueError):
        patch_app('print("otra app")')
