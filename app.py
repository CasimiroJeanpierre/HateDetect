"""HateDetect — demostración pública académica y Historial Supabase por usuario."""
import hashlib
import json
import re
import time
import unicodedata
from pathlib import Path

import joblib
import pandas as pd
import streamlit as st

from auth_google import render_login, save_history, list_history, delete_history

ROOT = Path(__file__).resolve().parent
ASSETS = ROOT / 'assets'
ALLOWED_LABELS = {'Odio', 'Ofensivo', 'Neutro'}
st.set_page_config(page_title='HateDetect | Demostración académica', page_icon='🛡️', layout='wide')


def clean_for_inference(text):
    if not isinstance(text, str):
        return ''
    value = unicodedata.normalize('NFKC', text)
    value = re.sub(r'[\u200b\u200e\u200f\ufeff]', '', value)
    value = re.sub(r'[\u00a0\u1680\u2000-\u200a\u202f\u205f\u3000]', ' ', value)
    value = re.sub(r'(?:https?://|www\.)\S+?(?=[.,;!?)]*(?:\s|$))', '[URL]', value, flags=re.IGNORECASE)
    value = re.sub(r'[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}', '[EMAIL]', value)
    value = re.sub(r'(?<!\w)\+?\d[\d ()-]{7,}\d(?!\w)', '[PHONE]', value)
    value = re.sub(r'(?<!\w)(?:/?u/|@)[A-Za-z0-9_-]+', '[USER]', value, flags=re.IGNORECASE)
    return re.sub(r'\s+', ' ', value).strip()


@st.cache_data
def load_summary():
    with (ASSETS / 'summary.json').open(encoding='utf-8') as file:
        report = json.load(file)
    if report.get('origin') != 'sintetico' or report.get('selected_model') != 'logistic':
        raise ValueError('Metadatos públicos del modelo inválidos')
    return report


@st.cache_resource(show_spinner='Cargando clasificador...')
def load_model():
    report = load_summary()
    path = ASSETS / 'model.pkl'
    if hashlib.sha256(path.read_bytes()).hexdigest() != report.get('model_sha256'):
        raise ValueError('Integridad del modelo no válida')
    # Only load the trusted locally trained and hashed artifact.
    return joblib.load(path)


st.sidebar.title('🛡️ HateDetect')
st.sidebar.caption('Capstone UPN — demostración pública')
page = st.sidebar.radio('Sección', ['Clasificación', 'Reportes', 'Historial'])
st.sidebar.divider()
st.sidebar.warning('Prototipo académico: no es un sistema de moderación autónoma.')
st.sidebar.caption('Sin acceso al panel de anotadores ni a datos privados de evaluadores.')
client, uid = render_login()

try:
    summary, model = load_summary(), load_model()
except (OSError, ValueError, ImportError):
    st.error('No se pudo cargar el modelo público o los metadatos.')
    st.stop()

if 'session_history' not in st.session_state:
    st.session_state.session_history = []

if page == 'Clasificación':
    st.title('Clasificación de comentarios')
    st.info('Solo datos sintéticos de demostración. No introduzcas datos personales.')
    st.caption('TF-IDF + LogisticRegression, seleccionado mediante validación.')
    input_text = st.text_area('Comentario a analizar', max_chars=2000, height=150,
                              placeholder='Escribe un comentario sintético en español o inglés')
    if uid:
        save = st.checkbox('Guardar clasificación en mi Historial persistente', value=False)
    else:
        save = st.checkbox('Guardar temporalmente en esta sesión', value=False)
        st.caption('Inicia sesión con Google en la barra lateral para guardar permanentemente.')

    if st.button('Clasificar', type='primary'):
        cleaned = clean_for_inference(input_text)
        if not cleaned:
            st.warning('Introduce un comentario válido.')
        else:
            started = time.perf_counter()
            prediction = str(model.predict([cleaned])[0])
            elapsed = (time.perf_counter() - started) * 1000
            if prediction not in ALLOWED_LABELS:
                st.error('La salida no coincide con las categorías esperadas.')
                st.stop()
            a, b = st.columns(2)
            a.metric('Categoría predicha', prediction)
            b.metric('Inferencia del modelo', f'{elapsed:.2f} ms')
            st.caption('El tiempo no incluye transmisión ni representación de la página.')
            st.warning('Requiere revisión humana. Las probabilidades no están calibradas.')
            if hasattr(model, 'predict_proba'):
                probs = model.predict_proba([cleaned])[0]
                st.dataframe(pd.DataFrame({
                    'Categoría': model.classes_, 'Probabilidad sin calibrar': probs
                }), hide_index=True, use_container_width=True)
            st.write('Texto procesado')
            st.code(cleaned, language=None)
            if save:
                if client is not None and uid:
                    try:
                        save_history(client, uid, cleaned, prediction, elapsed)
                        st.success('Guardado en tu Historial persistente privado.')
                    except Exception:
                        st.error('No fue posible guardar. Revisa la sesión o la conexión a Supabase.')
                else:
                    st.session_state.session_history.insert(0, {
                        'Texto': cleaned, 'Categoría': prediction,
                        'Modelo': 'TF-IDF + LogisticRegression',
                        'Tiempo (ms)': round(elapsed, 3)
                    })
                    st.success('Guardado solo en esta sesión.')

elif page == 'Reportes':
    st.title('Evaluación de modelos')
    st.info('Laboratorio con 72 comentarios sintéticos; estos resultados no estiman el rendimiento en Reddit real.')
    sizes = summary.get('split_sizes', {})
    a, b, c = st.columns(3)
    a.metric('Entrenamiento', int(sizes.get('train', 0)))
    b.metric('Validación', int(sizes.get('validation', 0)))
    c.metric('Prueba', int(sizes.get('test', 0)))
    st.subheader('Comparación de los cuatro modelos')
    table = pd.DataFrame(summary.get('results', []))
    if not table.empty:
        table = table.rename(columns={
            'model_name': 'Modelo', 'validation_macro_f1': 'Macro-F1 validación',
            'macro_f1': 'Macro-F1 prueba', 'balanced_accuracy': 'Exactitud balanceada',
            'precision_odio': 'Precisión Odio', 'recall_odio': 'Recall Odio'
        })
        st.dataframe(table, hide_index=True, use_container_width=True)
        st.bar_chart(table.set_index('Modelo')[['Macro-F1 validación', 'Macro-F1 prueba']])
        st.download_button('Exportar métricas CSV', data=table.to_csv(index=False).encode('utf-8-sig'),
                           file_name='hatedetect_metricas_sinteticas.csv', mime='text/csv')
        st.caption('Macro-F1: promedio no ponderado de los F1 de cada categoría.')
    st.success('Modelo publicado: TF-IDF + LogisticRegression (seleccionado por validación).')
    st.caption('Los otros tres enfoques se comparan por métricas; no ejecutan inferencia en esta versión web.')
    st.caption('Solo 11 ejemplos de prueba: estimaciones exploratorias con incertidumbre considerable.')

else:
    st.title('Historial de clasificaciones')
    if client is not None and uid:
        st.success('Sesión autenticada. Los registros se conservan en Supabase y están protegidos con RLS.')
        try:
            records = list_history(client, uid)
        except Exception:
            st.error('No fue posible consultar el Historial. Vuelve a iniciar sesión.')
            records = []
        if records:
            display = pd.DataFrame(records).rename(columns={
                'created_at': 'Fecha (UTC)', 'comment_text': 'Comentario',
                'category': 'Categoría', 'model_name': 'Modelo',
                'inference_ms': 'Tiempo (ms)'
            })
            st.dataframe(display.drop(columns=['id'], errors='ignore'), hide_index=True,
                         use_container_width=True)
            st.caption('Se muestran como máximo los últimos 100 registros de tu cuenta.')
            labels = {f"{r['created_at']} · {r['category']} · {r['id'][:8]}": r['id'] for r in records}
            to_delete = st.selectbox('Eliminar registro seleccionado', list(labels), key='history_delete_select')
            if st.button('Eliminar de mi Historial', key='history_delete_btn'):
                try:
                    delete_history(client, uid, labels[to_delete])
                    st.success('Registro eliminado.')
                    st.rerun()
                except Exception:
                    st.error('No se pudo eliminar el registro.')
        else:
            st.info('Tu cuenta aún no tiene registros guardados.')
    else:
        st.info('Para consultar un Historial persistente, inicia sesión con Google en la barra lateral.')
        st.warning('Sin inicio de sesión, el Historial es únicamente temporal por sesión.')
        if st.session_state.session_history:
            st.dataframe(pd.DataFrame(st.session_state.session_history), hide_index=True,
                         use_container_width=True)
            if st.button('Borrar historial temporal'):
                st.session_state.session_history = []
                st.rerun()
        else:
            st.info('No hay clasificaciones temporales guardadas.')

st.divider()
st.caption('HateDetect · Investigación académica · Corpus sintético · Revisión humana requerida.')
