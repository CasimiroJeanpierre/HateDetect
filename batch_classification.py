"""Clasificación automática por lotes de CSV sintéticos en HateDetect.

No realiza llamadas a Supabase, no usa privilegios de administrador y mantiene
los resultados solo en el estado de la sesión activa de Streamlit.
"""
from __future__ import annotations

import csv
import hashlib
import io
import time

import pandas as pd

MAX_CSV_BYTES = 1_048_576  # 1 MiB de contenido UTF-8
MAX_ROWS = 500
MAX_TEXT_CHARS = 2_000
COLUMN_ALIASES = frozenset({'comentario', 'texto', 'comment', 'text'})
LABELS = ('Odio', 'Ofensivo', 'Neutro')
OUTPUT_COLUMNS = ('Fila', 'Comentario', 'Texto procesado', 'Categoría', 'Estado')


class BatchCSVError(ValueError):
    """CSV mal formado o que no cumple límites del prototipo."""


def read_comments_csv(raw: bytes) -> list[dict]:
    """Lee comentarios de un CSV UTF-8; admite coma, punto y coma y BOM."""
    if not isinstance(raw, bytes) or not raw:
        raise BatchCSVError('El archivo CSV está vacío.')
    if len(raw) > MAX_CSV_BYTES:
        raise BatchCSVError('El CSV supera el límite de 1 MiB.')
    try:
        decoded = raw.decode('utf-8-sig')
    except UnicodeDecodeError as exc:
        raise BatchCSVError('El archivo debe estar codificado en UTF-8.') from exc
    if '\x00' in decoded:
        raise BatchCSVError('El CSV contiene caracteres nulos no permitidos.')
    try:
        dialect = csv.Sniffer().sniff(decoded[:4096], delimiters=',;')
        delimiter = dialect.delimiter
    except csv.Error:
        delimiter = ','
    try:
        reader = csv.DictReader(io.StringIO(decoded, newline=''), delimiter=delimiter, strict=True)
        if not reader.fieldnames:
            raise BatchCSVError('Falta la fila de encabezados.')
        headers = reader.fieldnames
        matches = [field for field in headers if field and field.strip().casefold() in COLUMN_ALIASES]
        if len(matches) != 1:
            raise BatchCSVError('Se requiere una única columna llamada comentario, texto, comment o text.')
        target = matches[0]
        comments = []
        for number, row in enumerate(reader, start=2):
            if len(comments) >= MAX_ROWS:
                raise BatchCSVError('El CSV supera el máximo de 500 comentarios.')
            # Los delimitadores sobrantes generan una clave None en DictReader.
            if None in row or row.get(target) is None:
                raise BatchCSVError('La fila {} tiene columnas inconsistentes; revisa las comillas del CSV.'.format(number))
            comments.append({'fila': number, 'comentario': row[target]})
    except csv.Error as exc:
        raise BatchCSVError('CSV mal formado. Revisa delimitadores y comillas.') from exc
    if not comments:
        raise BatchCSVError('El CSV no contiene filas de comentarios.')
    return comments


def classify_rows(rows: list[dict], model, clean_fn) -> dict:
    """Predice de forma vectorizada; preserva orden y filas inválidas."""
    if not rows or len(rows) > MAX_ROWS:
        raise BatchCSVError('La cantidad de filas debe estar entre 1 y 500.')
    output = []
    valid_texts = []
    valid_indices = []
    for row in rows:
        original = row.get('comentario', '')
        if not isinstance(original, str):
            original = ''
        item = {
            'Fila': row['fila'], 'Comentario': original,
            'Texto procesado': '', 'Categoría': '', 'Estado': '',
        }
        if len(original) > MAX_TEXT_CHARS:
            item['Estado'] = 'Omitida: supera 2000 caracteres'
        else:
            cleaned = clean_fn(original)
            if not cleaned:
                item['Estado'] = 'Omitida: texto vacío'
            elif len(cleaned) > MAX_TEXT_CHARS:
                item['Estado'] = 'Omitida: texto procesado demasiado largo'
            else:
                item['Texto procesado'] = cleaned
                valid_indices.append(len(output))
                valid_texts.append(cleaned)
        output.append(item)
    start = time.perf_counter()
    if valid_texts:
        predictions = list(model.predict(valid_texts))
    else:
        predictions = []
    elapsed_ms = round((time.perf_counter() - start) * 1000, 2)
    if len(predictions) != len(valid_texts):
        raise ValueError('El clasificador devolvió una cantidad inesperada de predicciones.')
    if any(str(label) not in LABELS for label in predictions):
        raise ValueError('El clasificador devolvió una categoría desconocida.')
    counts = {name: 0 for name in LABELS}
    for index, label in zip(valid_indices, predictions):
        category = str(label)
        output[index]['Categoría'] = category
        output[index]['Estado'] = 'Clasificada'
        counts[category] += 1
    valid = len(valid_texts)
    return {
        'table': pd.DataFrame(output, columns=list(OUTPUT_COLUMNS)),
        'valid': valid,
        'invalid': len(output) - valid,
        'counts': counts,
        'inference_ms': elapsed_ms,
    }


def _safe_csv_cell(value):
    """Neutraliza fórmulas de Excel en columnas de texto controladas por usuarios."""
    s = str(value) if value is not None else ''
    if s.lstrip(' \t\r\n').startswith(('=', '+', '-', '@')):
        return "'" + s
    return s


def export_csv_bytes(table: pd.DataFrame) -> bytes:
    """CSV UTF-8 BOM; comentarios de entrada neutralizados para Excel."""
    buffer = io.StringIO(newline='')
    writer = csv.writer(buffer)
    writer.writerow(OUTPUT_COLUMNS)
    for row in table.itertuples(index=False, name=None):
        record = dict(zip(OUTPUT_COLUMNS, row))
        for key in ('Comentario', 'Texto procesado'):
            record[key] = _safe_csv_cell(record[key])
        writer.writerow([record.get(key, '') for key in OUTPUT_COLUMNS])
    return buffer.getvalue().encode('utf-8-sig')


def render_batch_page(model, clean_fn):
    """Sección Streamlit; no persiste entradas ni resultados en Supabase."""
    import streamlit as st

    st.title('Clasificación automática por lotes')
    st.info('Prototipo académico: utiliza únicamente comentarios sintéticos, sin datos personales.')
    st.caption('Archivo CSV UTF-8; columna comentario (o texto/comment/text); máximo 500 filas y 1 MiB.')
    sample = 'comentario\n"Me gusta aprender programación"\n"Hoy compartiré mi proyecto"\n"Buen día a todos"\n'
    st.download_button(
        'Descargar CSV de ejemplo', data=sample.encode('utf-8-sig'),
        file_name='hatedetect_comentarios_ejemplo.csv', mime='text/csv',
        key='batch_example_download',
    )
    uploaded = st.file_uploader('Selecciona un CSV de comentarios', type=['csv'], key='batch_csv_uploader')
    if uploaded is None:
        st.info('Carga un CSV para comenzar. Los resultados solo se guardan temporalmente en esta sesión.')
        st.session_state.pop('hatedetect_batch_result', None)
        return
    if uploaded.size > MAX_CSV_BYTES:
        st.error('El CSV supera el límite de 1 MiB. Reduce el archivo antes de clasificarlo.')
        st.session_state.pop('hatedetect_batch_result', None)
        return
    raw = uploaded.getvalue()
    digest = hashlib.sha256(raw).hexdigest()
    if st.button('Clasificar archivo automáticamente', type='primary', key='batch_run'):
        try:
            rows = read_comments_csv(raw)
            with st.spinner('Clasificando comentarios...'):
                results = classify_rows(rows, model, clean_fn)
            st.session_state['hatedetect_batch_result'] = {'digest': digest, 'results': results}
        except (BatchCSVError, ValueError) as exc:
            st.session_state.pop('hatedetect_batch_result', None)
            st.error(str(exc))
        except Exception:
            st.session_state.pop('hatedetect_batch_result', None)
            st.error('No se pudo completar la clasificación. Verifica el archivo o intenta con menos filas.')
    stored = st.session_state.get('hatedetect_batch_result')
    if not stored or stored.get('digest') != digest:
        return
    results = stored['results']
    a, b, c = st.columns(3)
    a.metric('Comentarios clasificados', results['valid'])
    b.metric('Filas omitidas', results['invalid'])
    c.metric('Inferencia del modelo', f"{results['inference_ms']:.2f} ms")
    st.caption('El tiempo mide solamente el cálculo de predicciones, no la carga ni el procesamiento del archivo.')
    counts = pd.DataFrame([{'Categoría': k, 'Cantidad': v} for k, v in results['counts'].items()])
    st.subheader('Distribución de categorías predichas')
    st.bar_chart(counts.set_index('Categoría'))
    st.subheader('Resultados por comentario')
    st.dataframe(results['table'], hide_index=True, use_container_width=True)
    st.download_button(
        'Descargar resultados CSV', data=export_csv_bytes(results['table']),
        file_name='hatedetect_resultados_lotes.csv', mime='text/csv', key='batch_results_download',
    )
    st.warning('Son predicciones automáticas exploratorias; no representan precisión validada ni justifican sanciones automáticas.')
    st.caption('El CSV no se almacena en Supabase; permanece únicamente en memoria de esta sesión durante el uso.')
