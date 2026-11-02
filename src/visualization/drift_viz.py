"""
Drift visualization module for Corvus CKD Prediction (Phase 6).

Provides visualization functions for drift detection results.
"""

from __future__ import annotations

import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from typing import Optional

from src.utils.logger import get_logger

log = get_logger()


def plot_data_drift(
    feature_names: list[str],
    drift_scores: list[float],
    p_values: list[float] | None = None,
    title: str = "Data Drift Detection Results",
) -> go.Figure:
    """
    Create drift detection bar chart showing drift scores per feature.

    Args:
        feature_names: List of feature names
        drift_scores: Drift scores for each feature
        p_values: P-values for each feature (optional)
        title: Plot title

    Returns:
        Plotly figure object
    """
    fig = go.Figure()

    # Color code by drift significance
    colors = ["#dc2626" if s > 0.3 else "#2563eb" for s in drift_scores]

    fig.add_trace(
        go.Bar(
            x=feature_names,
            y=drift_scores,
            name="Drift Score",
            marker_color=colors,
            text=[f"{s:.3f}" for s in drift_scores],
            textposition="outside",
        )
    )

    # Add threshold line at 0.3
    fig.add_hline(
        y=0.3,
        line_dash="dash",
        line_color="red",
        annotation_text="Drift threshold (0.3)",
        annotation_position="top right",
    )

    fig.update_layout(
        title=title,
        xaxis_title="Feature",
        yaxis_title="Drift Score",
        template="plotly_white",
        height=500,
        width=max(800, len(feature_names) * 40),
        xaxis_tickangle=-45,
    )

    log.info(f"Created drift detection plot with {len(feature_names)} features")
    return fig


def plot_drift_comparison(
    reference_stats: dict[str, float],
    current_stats: dict[str, float],
    feature_names: list[str] | None = None,
    title: str = "Feature Distribution Comparison",
) -> go.Figure:
    """
    Create comparison plot between reference and current feature distributions.

    Args:
        reference_stats: Reference feature statistics
        current_stats: Current feature statistics
        feature_names: Feature names to plot
        title: Plot title

    Returns:
        Plotly figure object
    """
    if feature_names is None:
        feature_names = list(reference_stats.keys())

    ref_values = [reference_stats.get(f, 0) for f in feature_names]
    cur_values = [current_stats.get(f, 0) for f in feature_names]

    fig = go.Figure()

    fig.add_trace(
        go.Bar(
            name="Reference",
            x=feature_names,
            y=ref_values,
            marker_color="#00288e",
        )
    )

    fig.add_trace(
        go.Bar(
            name="Current",
            x=feature_names,
            y=cur_values,
            marker_color="#006c4a",
        )
    )

    fig.update_layout(
        title=title,
        xaxis_title="Feature",
        yaxis_title="Value",
        barmode="group",
        template="plotly_white",
        height=500,
        width=max(800, len(feature_names) * 50),
        xaxis_tickangle=-45,
    )

    log.info(f"Created drift comparison plot with {len(feature_names)} features")
    return fig


def plot_drift_over_time(
    timestamps: list[str],
    drift_scores: list[float],
    title: str = "Drift Score Over Time",
) -> go.Figure:
    """
    Create time series plot of drift scores over time.

    Args:
        timestamps: List of timestamps
        drift_scores: Drift scores at each timestamp
        title: Plot title

    Returns:
        Plotly figure object
    """
    fig = go.Figure()

    fig.add_trace(
        go.Scatter(
            x=timestamps,
            y=drift_scores,
            mode="lines+markers",
            name="Drift Score",
            line=dict(color="#00288e", width=2),
            marker=dict(size=6),
        )
    )

    fig.add_hline(
        y=0.3,
        line_dash="dash",
        line_color="red",
        annotation_text="Drift threshold",
        annotation_position="top right",
    )

    fig.update_layout(
        title=title,
        xaxis_title="Time",
        yaxis_title="Drift Score",
        template="plotly_white",
        height=400,
        width=900,
    )

    log.info(f"Created drift over time plot with {len(timestamps)} time points")
    return fig