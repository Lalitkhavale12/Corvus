"""
Model visualization module for Corvus CKD Prediction (Phase 6).

Provides visualization functions for model performance including:
- Prediction distribution plots
- ROC curves
- Confusion matrices
"""

from __future__ import annotations

import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from typing import Optional

from src.utils.logger import get_logger

log = get_logger()


def plot_prediction_distribution(
    probabilities: np.ndarray,
    predictions: np.ndarray,
    actuals: np.ndarray | None = None,
    title: str = "Prediction Probability Distribution",
) -> go.Figure:
    """
    Create a histogram of prediction probabilities colored by prediction class.

    Args:
        probabilities: Prediction probabilities
        predictions: Predicted class labels (0 or 1)
        actuals: Actual class labels (optional, for comparison)
        title: Plot title

    Returns:
        Plotly figure object
    """
    fig = go.Figure()

    # Add histograms for each class
    for pred_class in [0, 1]:
        mask = predictions == pred_class
        if mask.sum() > 0:
            fig.add_trace(
                go.Histogram(
                    x=probabilities[mask],
                    name=f"Predicted {pred_class}",
                    opacity=0.7,
                    nbinsx=30,
                    marker_color="#00288e" if pred_class == 1 else "#006c4a",
                )
            )

    fig.update_layout(
        title=title,
        xaxis_title="Prediction Probability",
        yaxis_title="Count",
        barmode="overlay",
        template="plotly_white",
        height=500,
        width=800,
    )

    log.info(f"Created prediction distribution plot with {len(probabilities)} samples")
    return fig


def plot_roc_curve(
    fpr: np.ndarray,
    tpr: np.ndarray,
    roc_auc: float,
    title: str = "ROC Curve",
) -> go.Figure:
    """
    Create ROC curve plot.

    Args:
        fpr: False positive rates
        tpr: True positive rates
        roc_auc: ROC AUC score
        title: Plot title

    Returns:
        Plotly figure object
    """
    fig = go.Figure()

    fig.add_trace(
        go.Scatter(
            x=fpr,
            y=tpr,
            mode="lines",
            name=f"ROC curve (AUC = {roc_auc:.3f})",
            line=dict(color="#00288e", width=2),
        )
    )

    # Add diagonal line (random classifier)
    fig.add_trace(
        go.Scatter(
            x=[0, 1],
            y=[0, 1],
            mode="lines",
            name="Random classifier",
            line=dict(color="gray", width=1, dash="dash"),
        )
    )

    fig.update_layout(
        title=title,
        xaxis_title="False Positive Rate",
        yaxis_title="True Positive Rate",
        xaxis=dict(range=[0, 1]),
        yaxis=dict(range=[0, 1]),
        template="plotly_white",
        height=500,
        width=600,
    )

    log.info(f"Created ROC curve plot with AUC = {roc_auc:.3f}")
    return fig


def plot_confusion_matrix(
    cm: np.ndarray,
    class_names: list[str] | None = None,
    title: str = "Confusion Matrix",
) -> go.Figure:
    """
    Create confusion matrix heatmap.

    Args:
        cm: Confusion matrix array
        class_names: Class names for labels
        title: Plot title

    Returns:
        Plotly figure object
    """
    if class_names is None:
        class_names = ["Negative", "Positive"]

    fig = go.Figure(
        data=go.Heatmap(
            z=cm,
            x=class_names,
            y=class_names,
            colorscale="Blues",
            text=cm,
            texttemplate="%{text}",
            textfont={"size": 14},
        )
    )

    fig.update_layout(
        title=title,
        xaxis_title="Predicted",
        yaxis_title="Actual",
        template="plotly_white",
        height=500,
        width=500,
    )

    log.info("Created confusion matrix plot")
    return fig


def create_model_comparison_dashboard(
    model_metrics: dict[str, dict[str, float]],
    title: str = "Model Comparison Dashboard",
) -> go.Figure:
    """
    Create a dashboard comparing multiple models.

    Args:
        model_metrics: Dictionary of model_name -> metrics dict
        title: Plot title

    Returns:
        Plotly figure object
    """
    models = list(model_metrics.keys())
    metrics = list(model_metrics[models[0]].keys()) if models else []

    fig = make_subplots(
        rows=1,
        cols=len(metrics),
        subplot_titles=[m.replace("_", " ").title() for m in metrics],
        shared_yaxes=True,
    )

    for i, metric in enumerate(metrics):
        values = [model_metrics[m].get(metric, 0) for m in models]
        fig.add_trace(
            go.Bar(
                x=models,
                y=values,
                name=metric,
                marker_color="#00288e",
            ),
            row=1,
            col=i + 1,
        )

    fig.update_layout(
        title=title,
        template="plotly_white",
        height=500,
        width=300 * len(metrics),
        showlegend=False,
    )

    log.info(f"Created model comparison dashboard with {len(models)} models")
    return fig