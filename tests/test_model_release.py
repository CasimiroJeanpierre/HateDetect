"""Pruebas aisladas: no requieren Streamlit ni datos de la prueba final."""
from __future__ import annotations

import copy
import hashlib

import joblib
import pytest
import sklearn

import model_release as release


class FakeClassifier:
    classes_ = ["Neutro", "Odio", "Ofensivo"]

    def predict(self, texts):
        return ["Neutro"] * len(texts)


def fixture_model(monkeypatch, tmp_path, name="published"):
    binary = tmp_path / release.MODEL_CONFIGS[name]["filename"]
    joblib.dump(FakeClassifier(), binary)
    cfg = copy.deepcopy(release.MODEL_CONFIGS)
    cfg[name]["sha256"] = hashlib.sha256(binary.read_bytes()).hexdigest()
    cfg[name]["sklearn_version"] = sklearn.__version__
    monkeypatch.setattr(release, "MODEL_CONFIGS", cfg)
    return cfg, {"model_sha256": cfg["published"]["sha256"]}


def test_default_is_published(monkeypatch):
    monkeypatch.delenv("HATEDETECT_MODEL_VERSION", raising=False)
    assert release.selected_release() == "published"


def test_unsupported_selection_fail_closed():
    with pytest.raises(ValueError, match="no autorizada"):
        release.selected_release("../../cualquier.pkl")


def test_published_load_and_predict(monkeypatch, tmp_path):
    _, summary = fixture_model(monkeypatch, tmp_path)
    model, choice = release.load_selected_model(tmp_path, summary)
    assert choice == "published"
    assert model.predict(["comentario", "otro"]) == ["Neutro", "Neutro"]


def test_v3_only_when_explicitly_selected(monkeypatch, tmp_path):
    cfg, _ = fixture_model(monkeypatch, tmp_path, "v3")
    summary = {"model_sha256": cfg["published"]["sha256"]}
    model, choice = release.load_selected_model(tmp_path, summary, "v3")
    assert choice == "v3"
    assert model.predict(["saludo"]) == ["Neutro"]


def test_reject_tampered_blob(monkeypatch, tmp_path):
    _, summary = fixture_model(monkeypatch, tmp_path)
    (tmp_path / "model.pkl").write_bytes(b"untrusted pickle")
    with pytest.raises(ValueError, match="SHA-256"):
        release.load_selected_model(tmp_path, summary)


def test_reject_summary_mismatch(monkeypatch, tmp_path):
    _, _ = fixture_model(monkeypatch, tmp_path)
    with pytest.raises(ValueError, match="resumen público"):
        release.load_selected_model(tmp_path, {"model_sha256": "bad"})


def test_reject_library_version_mismatch(monkeypatch, tmp_path):
    cfg, summary = fixture_model(monkeypatch, tmp_path)
    cfg["published"]["sklearn_version"] = "0.0.0"
    with pytest.raises(ValueError, match="Incompatibilidad"):
        release.load_selected_model(tmp_path, summary)


def test_missing_v3_model_fails_not_fallback(tmp_path):
    summary = {"model_sha256": release.MODEL_CONFIGS["published"]["sha256"]}
    # Si sklearn no coincide, falla incluso ANTES de intentar la lectura (estricto).
    with pytest.raises((ValueError, FileNotFoundError)):
        release.load_selected_model(tmp_path, summary, "v3")
