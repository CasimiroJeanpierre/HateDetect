import hashlib
import json
from pathlib import Path

import pytest
import sklearn

from model_release import load_selected_model

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "assets"

EXPECTED = {
    "published": "acb50ded09ca2b782210b730c915e3709f75c6767cf8cdebc6189fe6cc324b73",
    "v3": "1b8d300ee3682437b724a2eccf8b9626526280e35e06c7cdaafe216843fe0470",
}


@pytest.mark.parametrize("release", ["published", "v3"])
def test_real_model_integrity_and_prediction(release):
    assert sklearn.__version__ == "1.9.1"

    with (ASSETS / "summary.json").open(encoding="utf-8") as f:
        summary = json.load(f)

    filename = (
        "model.pkl" if release == "published"
        else "model_v3.joblib"
    )

    artifact = ASSETS / filename

    digest = hashlib.sha256(artifact.read_bytes()).hexdigest()
    assert digest == EXPECTED[release]

    model, selected = load_selected_model(
        ASSETS, summary, release
    )

    assert selected == release
    assert set(map(str, model.classes_)) == {
        "Neutro", "Odio", "Ofensivo"
    }

    text = "Me gusta estudiar programacion"

    prediction = str(model.predict([text])[0])
    assert prediction == "Neutro"

    probabilities = model.predict_proba([text])[0]
    assert len(probabilities) == 3
    assert all(0 <= float(p) <= 1 for p in probabilities)
    assert abs(sum(map(float, probabilities)) - 1) < 1e-6
