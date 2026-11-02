"""HateDetect — demostración pública segura, separada de los datos de investigación."""
import json
import hashlib
import re
import time
import unicodedata
from pathlib import Path

import joblib
import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parent
ASSETS = ROOT / "assets"
ALLOWED_LABELS = {"Odio", "Ofensivo", "Neutro"}

st.set_page_config(page_title="HateDetect | Demostración académica", page_icon="🛡️", layout="wide")


def clean_for_inference(text):
    """Preprocesamiento compatible con la implementación local, sin prometer anonimización total."""
    if not isinstance(text, str):
        return ""
    value = unicodedata.normalize("NFKC", text)
    value = re.sub(r"[\u200b\u200e\u200f\ufeff]", "", value)
    value = re.sub(r"[\u00a0\u1680\u2000-\u200a\u202f\u205f\u3000]", " ", value)
    value = re.sub(r"(?:https?://|www\.)\S+?(?=[.,;!?)]*(?:\s|$))", "[URL]", value, flags=re.IGNORECASE)
    value = re.sub(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}", "[EMAIL]", value)
    value = re.sub(r"(?<!\w)\+?\d[\d ()-]{7,}\d(?!\w)", "[PHONE]", value)
    value = re.sub(r"(?<!\w)(?:/?u/|@)[A-Za-z0-9_-]+", "[USER]", value, flags=re.IGNORECASE)
    return re.sub(r"\s+", " ", value).strip()


@st.cache_resource(show_spinner="Cargando clasificador...")
def load_model():
    # Verificar integridad antes de deserializar exclusivamente un modelo propio y verificado.
    report = load_summary()
    path = ASSETS / "model.pkl"
    checksum = hashlib.sha256(path.read_bytes()).hexdigest()
    if checksum != report.get("model_sha256"):
        raise ValueError("El modelo publicado no coincide con el hash esperado")
    return joblib.load(path)


@st.cache_data
def load_summary():
    with (ASSETS / "summary.json").open(encoding="utf-8") as f:
        report = json.load(f)
    if report.get("origin") != "sintetico" or report.get("selected_model") != "logistic":
        raise ValueError("Metadatos públicos del modelo no válidos")
    return report


st.sidebar.title("🛡️ HateDetect")
st.sidebar.caption("Capstone UPN — demostración pública")
page = st.sidebar.radio("Sección", ["Clasificación", "Reportes", "Historial de esta sesión"])
st.sidebar.divider()
st.sidebar.warning("Prototipo académico. No es un sistema de moderación autónoma.")
st.sidebar.caption("Sin acceso al panel de anotadores ni a datos privados de los evaluadores.")

try:
    summary = load_summary()
    model = load_model()
except (OSError, ValueError, ImportError) as exc:
    st.error("Falta el modelo público o sus metadatos. Revisa la exportación de la ejecución local.")
    st.stop()

if "session_history" not in st.session_state:
    st.session_state.session_history = []

if page == "Clasificación":
    st.title("Clasificación de comentarios")
    st.info("Solo datos sintéticos de demostración. No introduzcas nombres, contraseñas ni otros datos personales.")
    st.caption("Clasificador publicado: TF-IDF + LogisticRegression, seleccionado mediante validación.")
    text = st.text_area("Comentario a analizar", max_chars=2000, height=150,
                        placeholder="Escribe aquí un comentario de prueba en español o inglés")
    save = st.checkbox("Conservar este resultado temporalmente en mi sesión", value=False,
                       help="No se escribe en una base de datos; desaparece al finalizar la sesión.")
    if st.button("Clasificar", type="primary"):
        cleaned = clean_for_inference(text)
        if not cleaned:
            st.warning("Introduce un comentario válido.")
        else:
            started = time.perf_counter()
            prediction = str(model.predict([cleaned])[0])
            elapsed = (time.perf_counter() - started) * 1000
            if prediction not in ALLOWED_LABELS:
                st.error("La salida del clasificador no coincide con las categorías esperadas.")
                st.stop()
            a, b = st.columns(2)
            a.metric("Categoría predicha", prediction)
            b.metric("Inferencia del modelo", f"{elapsed:.2f} ms")
            st.caption("El tiempo no incluye transmisión ni representación de la página.")
            st.warning("Requiere revisión humana. Las probabilidades del modelo no están calibradas.")
            if hasattr(model, "predict_proba"):
                probabilities = model.predict_proba([cleaned])[0]
                st.dataframe(pd.DataFrame({"Categoría": model.classes_, "Probabilidad sin calibrar": probabilities}),
                             hide_index=True, use_container_width=True)
            st.write("Texto procesado")
            st.code(cleaned, language=None)
            if save:
                st.session_state.session_history.insert(0, {"Texto": cleaned, "Categoría": prediction,
                                                             "Modelo": "TF-IDF + LogisticRegression", "Tiempo (ms)": round(elapsed, 3)})
                st.success("Resultado guardado únicamente en esta sesión.")

elif page == "Reportes":
    st.title("Evaluación de los modelos")
    st.info("Resultados de laboratorio sobre 72 comentarios sintéticos revisados; no reflejan rendimiento en Reddit real.")
    sizes = summary.get("split_sizes", {})
    a, b, c = st.columns(3)
    a.metric("Entrenamiento", int(sizes.get("train", 0)))
    b.metric("Validación", int(sizes.get("validation", 0)))
    c.metric("Prueba", int(sizes.get("test", 0)))
    st.subheader("Comparación de cuatro enfoques")
    metrics = pd.DataFrame(summary.get("results", []))
    if not metrics.empty:
        display = metrics.rename(columns={"model_name": "Modelo", "validation_macro_f1": "Macro-F1 validación",
                                          "macro_f1": "Macro-F1 prueba", "precision_odio": "Precisión Odio",
                                          "recall_odio": "Recall Odio"})
        st.dataframe(display, hide_index=True, use_container_width=True)
        if "Macro-F1 prueba" in display:
            st.bar_chart(display.set_index("Modelo")[["Macro-F1 validación", "Macro-F1 prueba"]])
    st.success("Modelo seleccionado por validación: TF-IDF + LogisticRegression")
    st.caption("XLM-RoBERTa se entrenó y evaluó localmente. Esta versión web no descarga su checkpoint de 1,12 GB.")
    st.caption("La evaluación tiene solo 11 ejemplos de prueba: cifras exploratorias e intervalos amplios.")

else:
    st.title("Historial temporal de esta sesión")
    st.warning("Esta demostración pública NO incluye Historial persistente ni cuentas. Los registros se aíslan en la sesión actual y se pierden al cerrarla.")
    if st.session_state.session_history:
        st.dataframe(pd.DataFrame(st.session_state.session_history), hide_index=True, use_container_width=True)
        if st.button("Borrar mi historial temporal"):
            st.session_state.session_history = []
            st.rerun()
    else:
        st.info("No hay clasificaciones guardadas en esta sesión.")

st.divider()
st.caption("HateDetect · Evaluación académica · Datos sintéticos · Clasificaciones sujetas a revisión humana.")
