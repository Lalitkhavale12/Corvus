"""Thin Streamlit client for the Corvus prediction API (FR-4.1).

Zero model logic lives here: this module renders a 24-field form and a CSV
upload picker, forwards both to the API over HTTP, and displays whatever the
server returns. All validation decisions (422s) belong to the server per the
responsibility map — numeric blanks are sent as null so the fitted pipeline
imputers handle them (D-05), and categorical options are limited to the
RESEARCH vocabularies only as a UI convenience, never as a second validator.
"""

from __future__ import annotations

import os

import httpx
import streamlit as st

API_URL = os.environ.get("API_URL", "http://localhost:8000")

NUMERIC_FIELDS = [
    "age", "bp", "sg", "al", "su", "bgr", "bu", "sc",
    "sod", "pot", "hemo", "pcv", "wc", "rc",
]

CATEGORICAL_OPTIONS: dict[str, list[str]] = {
    "rbc": ["abnormal", "normal"],
    "pc": ["abnormal", "normal"],
    "pcc": ["notpresent", "present"],
    "ba": ["notpresent", "present"],
    "htn": ["no", "yes"],
    "dm": ["no", "yes"],
    "cad": ["no", "yes"],
    "appet": ["good", "poor"],
    "pe": ["no", "yes"],
    "ane": ["no", "yes"],
}


def _parse_numeric(raw: str) -> float | None:
    """Blank means missing (None → server-side imputer); else a float."""
    raw = raw.strip()
    if not raw:
        return None
    return float(raw)


st.title("Corvus CKD Prediction")

st.subheader("Single prediction")
with st.form("predict_form"):
    payload: dict = {}
    for field in NUMERIC_FIELDS:
        payload[field] = st.text_input(f"{field} (blank = missing)", key=f"num_{field}")
    for field, options in CATEGORICAL_OPTIONS.items():
        payload[field] = st.selectbox(field, options, key=f"cat_{field}")
    submitted = st.form_submit_button("Predict")

if submitted:
    try:
        body = {k: _parse_numeric(v) for k, v in
                ((f, payload[f]) for f in NUMERIC_FIELDS)}
        body.update({f: payload[f] for f in CATEGORICAL_OPTIONS})
    except ValueError as exc:
        st.error(f"Numeric field is not a number: {exc}")
    else:
        try:
            resp = httpx.post(f"{API_URL}/predict", json=body, timeout=30)
        except httpx.ConnectError:
            st.error(f"Cannot reach the API at {API_URL} — is the stack up?")
        else:
            if resp.status_code == 200:
                data = resp.json()
                st.success(
                    f"prediction={data['prediction']} "
                    f"probability={data['probability']:.4f} "
                    f"model_version={data['model_version']}"
                )
            elif resp.status_code == 422:
                st.error(f"Rejected by server (422): {resp.json().get('detail')}")
            else:
                st.error(f"Server error ({resp.status_code}): {resp.text}")

st.subheader("Batch prediction (CSV)")
uploaded = st.file_uploader("CSV with the 24 columns", type=["csv"])
if uploaded is not None:
    try:
        resp = httpx.post(
            f"{API_URL}/batch_predict",
            files={"file": (uploaded.name, uploaded.getvalue(), "text/csv")},
            timeout=120,
        )
    except httpx.ConnectError:
        st.error(f"Cannot reach the API at {API_URL} — is the stack up?")
    else:
        if resp.status_code == 200:
            data = resp.json()
            st.success(
                f"count={data['count']} model_version={data['model_version']}"
            )
            st.dataframe(data["predictions"])
        elif resp.status_code in (413, 422):
            st.error(f"Rejected by server ({resp.status_code}): {resp.json().get('detail')}")
        else:
            st.error(f"Server error ({resp.status_code}): {resp.text}")
