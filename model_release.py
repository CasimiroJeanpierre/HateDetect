"""Selección controlada de modelos de HateDetect; sin cambios automáticos en producción.

Importante: solo cargar artefactos de confianza cuya huella SHA256 esté fijada aquí.
La selección por defecto es 'published'. La candidata v3 exige artefacto y
versión de scikit-learn compatibles antes de activarse.
"""
from __future__ import annotations

import hashlib
import os
import warnings
from pathlib import Path

import joblib
import sklearn
from sklearn.exceptions import InconsistentVersionWarning

LABELS = frozenset({"Odio", "Ofensivo", "Neutro"})
MODEL_CONFIGS = {
    "published": {
        "filename": "model.pkl",
        "sha256": "acb50ded09ca2b782210b730c915e3709f75c6767cf8cdebc6189fe6cc324b73",
        "sklearn_version": "1.9.1",
    },
    "v3": {
        "filename": "model_v3.joblib",
        "sha256": "1b8d300ee3682437b724a2eccf8b9626526280e35e06c7cdaafe216843fe0470",
        "sklearn_version": "1.9.1",  # Reentrenado con el corpus de desarrollo de 432
    },
}


def selected_release(explicit: str | None = None) -> str:
    """La opción inválida falla de forma cerrada: nunca se cambia de modelo en silencio."""
    selection = (explicit if explicit is not None else os.getenv("HATEDETECT_MODEL_VERSION", "published"))
    if selection not in MODEL_CONFIGS:
        raise ValueError("Versión del modelo no autorizada (published/v3).")
    return selection


def load_selected_model(assets_dir: Path, public_summary: dict, release: str | None = None):
    """Verifica metadatos, versión y SHA antes de deserializar un modelo de confianza.

    Devuelve (model, version). Nunca descarga modelos ni lee rutas desde el usuario.
    """
    choice = selected_release(release)
    cfg = MODEL_CONFIGS[choice]
    if choice == "published" and public_summary.get("model_sha256") != cfg["sha256"]:
        raise ValueError("El hash del resumen público no coincide con el artefacto publicado.")
    if sklearn.__version__ != cfg["sklearn_version"]:
        raise ValueError(
            "Incompatibilidad de scikit-learn para modelo {}: artefacto {}, entorno {}. "
            "No habilitar esta versión en producción hasta homologar la serialización.".format(
                choice, cfg["sklearn_version"], sklearn.__version__
            )
        )
    path = Path(assets_dir) / cfg["filename"]
    if hashlib.sha256(path.read_bytes()).hexdigest() != cfg["sha256"]:
        raise ValueError("SHA-256 del modelo no válido; carga cancelada.")
    with warnings.catch_warnings():
        warnings.simplefilter("error", InconsistentVersionWarning)
        try:
            model = joblib.load(path)
        except InconsistentVersionWarning as exc:
            raise ValueError("Modelo serializado con una versión incompatible de sklearn.") from exc
    if not hasattr(model, "predict") or frozenset(map(str, model.classes_)) != LABELS:
        raise ValueError("El modelo no ofrece el contrato Odio/Ofensivo/Neutro.")
    return model, choice
