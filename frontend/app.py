"""Thin Streamlit client for the Corvus prediction API (FR-4.1).

Zero model logic lives here: this module renders grouped NHANES-native fields
and a CSV upload picker, forwards both to the API over HTTP, and displays
whatever the server returns. All validation decisions (422s) belong to the
server per the responsibility map — numeric blanks are sent as null so the
fitted pipeline imputers handle them (D-05), and categorical options mirror
the NHANES vocabularies only as a UI convenience, never as a validator.

Prediction paths target /v2/* (serves model v11, GradientBoosting,
NHANES-native schema per schemas.CKDRequestNative: 16 numerics + 5
categoricals). Health reads /health (no v2 equivalent); model-info reads
/v2/model_info.
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
    "Demographics": [
        ("RIDAGEYR", "age in years"),
        ("INDFMPIR", "income poverty ratio"),
    ],
    "Vitals": [
        ("BMXBMI", "body mass index"),
        ("BPXOSY1", "systolic BP (mm Hg)"),
        ("BPXODI1", "diastolic BP (mm Hg)"),
    ],
    "Blood chemistry": [
        ("LBDSBUSI", ""),
        ("LBDSGLSI", "glucose (SI)"),
        ("LBXSNASI", "sodium (SI)"),
        ("LBXSKSI", "potassium (SI)"),
        ("LBDSCASI", "calcium (SI)"),
        ("LBDSPHSI", "phosphorus (SI)"),
    ],
    "Hematology": [
        ("LBXHGB", "hemoglobin (g/dL)"),
        ("LBXHCT", "hematocrit (%)"),
        ("LBXWBCSI", "WBC (SI)"),
        ("LBXRBCSI", "RBC (SI)"),
    ],
    "Metabolic": [
        ("LBXGH", "glycohemoglobin (%)"),
    ],
}

CATEGORICAL_OPTIONS: dict[str, list[str]] = {
    "RIAGENDR": ["1 — Male", "2 — Female"],
    "RIDRETH1": [
        "1 — Mexican American",
        "2 — Other Hispanic",
        "3 — White",
        "4 — Black",
        "5 — Other",
    ],
    "DMDEDUC2": [
        "1 — < 9th grade",
        "2 — 9–11th grade",
        "3 — HS grad / GED",
        "4 — Some college / AA",
        "5 — College grad",
        "9 — Missing",
    ],
    "DIQ010": ["1 — Yes", "2 — No", "3 — Borderline"],
    "MCQ035": ["1 — Yes", "2 — No", "9 — Don't know"],
}

# One-click demo patients (NHANES-native values; blanks flow to imputers).
PRESETS: dict[str, dict] = {
    "— enter manually —": {},
    "Demo A — expected CKD": {
        "RIDAGEYR": "65", "INDFMPIR": "1.5",
        "BMXBMI": "32", "BPXOSY1": "150", "BPXODI1": "95",
        "LBDSBUSI": "140", "LBDSGLSI": "130", "LBXSNASI": "135",
        "LBXSKSI": "4.0", "LBDSCASI": "9.0", "LBDSPHSI": "4.5",
        "LBXHGB": "11.0", "LBXHCT": "33", "LBXWBCSI": "7.5",
        "LBXRBCSI": "3.8", "LBXGH": "7.5",
        "RIAGENDR": "1 — Male", "RIDRETH1": "4 — Black",
        "DMDEDUC2": "3 — HS grad / GED", "DIQ010": "1 — Yes",
        "MCQ035": "1 — Yes",
    },
    "Demo B — expected healthy": {
        "RIDAGEYR": "35", "INDFMPIR": "3.5",
        "BMXBMI": "23", "BPXOSY1": "115", "BPXODI1": "75",
        "LBDSBUSI": "135", "LBDSGLSI": "90", "LBXSNASI": "140",
        "LBXSKSI": "4.2", "LBDSCASI": "9.5", "LBDSPHSI": "3.8",
        "LBXHGB": "15.0", "LBXHCT": "45", "LBXWBCSI": "6.0",
        "LBXRBCSI": "4.8", "LBXGH": "5.2",
        "RIAGENDR": "2 — Female", "RIDRETH1": "3 — White",
        "DMDEDUC2": "4 — Some college / AA", "DIQ010": "2 — No",
        "MCQ035": "2 — No",
    },
}


def _parse_numeric(raw: str) -> float | None:
    """Blank means missing (None → server-side imputer); else a float."""
    raw = raw.strip()
    if not raw:
        return None
    return float(raw)


def _parse_categorical(raw: str) -> str:
    """Strip the leading 'N — ' prefix, keep just the code value."""
    return raw.split(" — ")[0] if raw else raw


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
                        f"{field} ({hint}; blank = missing)" if hint else f"{field} (blank = missing)",
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
            numeric = {
                f: _parse_numeric(payload[f])
                for fields in FIELD_GROUPS.values()
                for f, _ in fields
            }
            categorical = {
                f: _parse_categorical(payload[f])
                for f in CATEGORICAL_OPTIONS
            }
            body = {**numeric, **categorical}
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
    st.write("Upload a CSV with NHANES-native columns — one bad row rejects the whole batch with its row number.")
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
