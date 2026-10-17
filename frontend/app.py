"""Thin Streamlit client for the Corvus prediction API (FR-4.1).

Zero model logic lives here: this module renders a grouped 24-field form and
a CSV upload picker, forwards both to the API over HTTP, and displays
whatever the server returns. All validation decisions (422s) belong to the
server per the responsibility map — numeric blanks are sent as null so the
fitted pipeline imputers handle them (D-05), and categorical options mirror
the RESEARCH vocabularies only as a UI convenience, never as a validator.

Endpoint note: prediction paths now target /v2/* (serves model v11,
GradientBoosting, NHANES-native schema). The form fields still post the 24
CKD fields; /v2/* expects NHANES-native fields (RIDAGEYR, INDFMPIR, …) per
schemas.CKDRequestNative, so single/batch prediction will 422 until the form
fields are re-mapped to NHANES names. Health and model-info reads target
/v2/model_info where available; /health has no v2 equivalent.
"""

from __future__ import annotations

import io
import os

import httpx
import pandas as pd
import streamlit as st

API_URL = os.environ.get("API_URL", "http://localhost:8000")

# Field groups (display label, units hint). Order within each group follows
# config column order; the request payload always uses raw field names.
FIELD_GROUPS: dict[str, list[tuple[str, str]]] = {
    "Vitals & demographics": [
        ("age", "years"),
        ("bp", "mm Hg"),
        ("sg", "specific gravity"),
        ("al", "albumin (0–5)"),
        ("su", "sugar (0–5)"),
    ],
    "Blood labs": [
        ("bgr", "mg/dL"),
        ("bu", "mg/dL"),
        ("sc", "mg/dL"),
        ("sod", "mEq/L"),
        ("pot", "mEq/L"),
        ("hemo", "g/dL"),
        ("pcv", "%"),
        ("wc", "cells/cumm"),
        ("rc", "millions/cumm"),
    ],
}

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

# One-click demo patients (real test-set rows; blanks flow to the imputers).
PRESETS: dict[str, dict] = {
    "— enter manually —": {},
    "Demo A — expected CKD": {
        "age": "3", "bp": "", "sg": "1.01", "al": "2", "su": "0", "bgr": "",
        "bu": "22", "sc": "0.7", "sod": "", "pot": "", "hemo": "10.7",
        "pcv": "34", "wc": "12300", "rc": "", "rbc": "normal", "pc": "normal",
        "pcc": "notpresent", "ba": "notpresent", "htn": "no", "dm": "no",
        "cad": "no", "appet": "good", "pe": "no", "ane": "no",
    },
    "Demo B — expected healthy": {
        "age": "52", "bp": "80", "sg": "1.025", "al": "0", "su": "0",
        "bgr": "99", "bu": "25", "sc": "0.8", "sod": "135", "pot": "3.7",
        "hemo": "15", "pcv": "52", "wc": "6300", "rc": "5.3",
        "rbc": "normal", "pc": "normal", "pcc": "notpresent",
        "ba": "notpresent", "htn": "no", "dm": "no", "cad": "no",
        "appet": "good", "pe": "no", "ane": "no",
    },
}


def _parse_numeric(raw: str) -> float | None:
    """Blank means missing (None → server-side imputer); else a float."""
    raw = raw.strip()
    if not raw:
        return None
    return float(raw)


def _api_alive() -> dict | None:
    try:
        resp = httpx.get(f"{API_URL}/health", timeout=5)
        return resp.json() if resp.status_code == 200 else None
    except httpx.ConnectError:
        return None


def _show_verdict(prediction: int, probability: float, version: str) -> None:
    label = "CKD detected" if prediction == 1 else "No CKD detected"
    if prediction == 1:
        st.error(f"### {label}", icon="⚠️")
    else:
        st.success(f"### {label}", icon="✅")
    st.progress(probability, text=f"CKD probability: {probability:.1%}")
    st.caption(f"Model version: {version} · served by corvus-ckd")


st.set_page_config(page_title="Corvus CKD Prediction", page_icon="🫀", layout="wide")
st.title("Corvus CKD Prediction")

# Sidebar: live serving state, straight from the API itself.
with st.sidebar:
    st.header("Serving state")
    st.caption(f"API: {API_URL}")
    health = _api_alive()
    if health is None:
        st.error(f"API unreachable at {API_URL} — is the stack up?")
    else:
        st.success("API up")
        try:
            info = httpx.get(f"{API_URL}/v2/model_info", timeout=5).json()
            st.caption(f"run `{info.get('run_id', '')[:8]}` · {info.get('resolution', '')}")
        except httpx.ConnectError:
            pass

tab_single, tab_batch = st.tabs(["Single prediction", "Batch CSV"])

with tab_single:
    preset_name = st.selectbox("Demo patient", list(PRESETS.keys()))
    preset = PRESETS[preset_name]
    # Seed widget defaults from the preset (manual edits after selection stick).
    for field, value in preset.items():
        st.session_state.setdefault(f"fld_{field}", value)

    with st.form("predict_form"):
        payload: dict = {}
        for group, fields in FIELD_GROUPS.items():
            st.subheader(group)
            cols = st.columns(3)
            for i, (field, hint) in enumerate(fields):
                with cols[i % 3]:
                    payload[field] = st.text_input(
                        f"{field} ({hint}; blank = missing)",
                        key=f"fld_{field}",
                    )
        st.subheader("History & examination")
        cols = st.columns(5)
        for i, (field, options) in enumerate(CATEGORICAL_OPTIONS.items()):
            with cols[i % 5]:
                payload[field] = st.selectbox(
                    field, options, key=f"fld_{field}",
                    index=options.index(preset.get(field, options[0]))
                    if preset.get(field) in options else 0,
                )
        submitted = st.form_submit_button("Predict", type="primary")

    if submitted:
        try:
            numeric = {f: _parse_numeric(payload[f]) for fields in FIELD_GROUPS.values() for f, _ in fields}
            body = {**numeric, **{f: payload[f] for f in CATEGORICAL_OPTIONS}}
        except ValueError as exc:
            st.error(f"Numeric field is not a number: {exc}")
        else:
            try:
                resp = httpx.post(f"{API_URL}/v2/predict", json=body, timeout=30)
            except httpx.ConnectError:
                st.error(f"Cannot reach the API at {API_URL} — is the stack up?")
            else:
                if resp.status_code == 200:
                    data = resp.json()
                    _show_verdict(data["prediction"], data["probability"], data["model_version"])
                elif resp.status_code == 422:
                    st.error(f"Rejected by server (422): {resp.json().get('detail')}")
                else:
                    st.error(f"Server error ({resp.status_code}): {resp.text}")

with tab_batch:
    st.write("Upload a CSV with the 24 columns — one bad row rejects the whole batch with its row number.")
    uploaded = st.file_uploader("CSV file", type=["csv"])
    if uploaded is not None:
        try:
            resp = httpx.post(
                f"{API_URL}/v2/batch_predict",
                files={"file": (uploaded.name, uploaded.getvalue(), "text/csv")},
                timeout=120,
            )
        except httpx.ConnectError:
            st.error(f"Cannot reach the API at {API_URL} — is the stack up?")
        else:
            if resp.status_code == 200:
                data = resp.json()
                df = pd.DataFrame(data["predictions"])
                n_pos = int((df["prediction"] == 1).sum())
                c1, c2, c3 = st.columns(3)
                c1.metric("Rows scored", data["count"])
                c2.metric("CKD flagged", n_pos)
                c3.metric("Model version", data["model_version"])
                st.dataframe(df, use_container_width=True)
                st.download_button(
                    "Download results CSV",
                    df.to_csv(index=False).encode(),
                    file_name="corvus_batch_results.csv",
                    mime="text/csv",
                )
            elif resp.status_code in (413, 422):
                st.error(f"Rejected by server ({resp.status_code}): {resp.json().get('detail')}")
            else:
                try:
                    detail = resp.json().get("detail", resp.text)
                except ValueError:
                    detail = resp.text
                st.error(f"Server error ({resp.status_code}): {detail}")
