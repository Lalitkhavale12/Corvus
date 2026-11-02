"""
Visualization tests for Phase 6.

Tests the visualization module including:
- Prediction distribution plots
- ROC curves
- Confusion matrices
- Drift detection plots
"""

from __future__ import annotations

import numpy as np
import pytest
import plotly.graph_objects as go

from src.visualization import (
    plot_prediction_distribution,
    plot_roc_curve,
    plot_confusion_matrix,
    plot_data_drift,
    plot_drift_comparison,
    plot_drift_over_time,
    create_model_comparison_dashboard,
)


def test_prediction_distribution_plot():
    """Test prediction distribution plot creation."""
    np.random.seed(42)
    n = 100
    probabilities = np.random.beta(2, 5, n)
    predictions = (probabilities > 0.5).astype(int)
    actuals = (probabilities > 0.4).astype(int)

    fig = plot_prediction_distribution(probabilities, predictions, actuals)

    assert isinstance(fig, go.Figure)
    assert len(fig.data) > 0
    assert "Prediction Probability Distribution" in fig.layout.title.text


def test_roc_curve_plot():
    """Test ROC curve plot creation."""
    fpr = np.array([0.0, 0.1, 0.3, 0.5, 0.8, 1.0])
    tpr = np.array([0.0, 0.4, 0.7, 0.85, 0.95, 1.0])
    roc_auc = 0.85

    fig = plot_roc_curve(fpr, tpr, roc_auc)

    assert isinstance(fig, go.Figure)
    assert len(fig.data) == 2  # ROC curve + diagonal
    assert "ROC curve" in fig.data[0].name


def test_confusion_matrix_plot():
    """Test confusion matrix plot creation."""
    cm = np.array([[50, 10], [5, 35]])
    class_names = ["Negative", "Positive"]

    fig = plot_confusion_matrix(cm, class_names)

    assert isinstance(fig, go.Figure)
    assert len(fig.data) == 1
    assert "Confusion Matrix" in fig.layout.title.text


def test_drift_plot():
    """Test drift detection plot creation."""
    feature_names = ["age", "bp", "sg", "al", "su"]
    drift_scores = [0.1, 0.45, 0.05, 0.35, 0.02]

    fig = plot_data_drift(feature_names, drift_scores)

    assert isinstance(fig, go.Figure)
    assert len(fig.data) == 1
    assert "Data Drift Detection Results" in fig.layout.title.text


def test_drift_comparison_plot():
    """Test drift comparison plot creation."""
    reference_stats = {"age": 45.0, "bp": 80.0, "sg": 1.02}
    current_stats = {"age": 48.0, "bp": 85.0, "sg": 1.01}

    fig = plot_drift_comparison(reference_stats, current_stats)

    assert isinstance(fig, go.Figure)
    assert len(fig.data) == 2  # Reference + Current


def test_drift_over_time_plot():
    """Test drift over time plot creation."""
    timestamps = ["2024-01-01", "2024-02-01", "2024-03-01", "2024-04-01"]
    drift_scores = [0.1, 0.25, 0.35, 0.45]

    fig = plot_drift_over_time(timestamps, drift_scores)

    assert isinstance(fig, go.Figure)
    assert len(fig.data) == 1
    assert "Drift Score Over Time" in fig.layout.title.text


def test_model_comparison_dashboard():
    """Test model comparison dashboard creation."""
    model_metrics = {
        "v9": {"accuracy": 0.75, "precision": 0.70, "recall": 0.72, "f1": 0.71, "roc_auc": 0.85},
        "v11": {"accuracy": 0.82, "precision": 0.78, "recall": 0.80, "f1": 0.79, "roc_auc": 0.88},
    }

    fig = create_model_comparison_dashboard(model_metrics)

    assert isinstance(fig, go.Figure)
    assert len(fig.data) == 5  # 5 metrics
    assert "Model Comparison Dashboard" in fig.layout.title.text


def test_empty_predictions():
    """Test edge case with empty predictions."""
    probabilities = np.array([])
    predictions = np.array([], dtype=int)

    fig = plot_prediction_distribution(probabilities, predictions)

    assert isinstance(fig, go.Figure)
    # Should not crash with empty data


def test_single_class_predictions():
    """Test with only one class in predictions."""
    probabilities = np.array([0.1, 0.2, 0.3, 0.4, 0.5])
    predictions = np.array([0, 0, 0, 0, 0])

    fig = plot_prediction_distribution(probabilities, predictions)

    assert isinstance(fig, go.Figure)
    assert len(fig.data) == 1  # Only one class present


if __name__ == "__main__":
    test_prediction_distribution_plot()
    test_roc_curve_plot()
    test_confusion_matrix_plot()
    test_drift_plot()
    test_drift_comparison_plot()
    test_drift_over_time_plot()
    test_model_comparison_dashboard()
    test_empty_predictions()
    test_single_class_predictions()
    print("All visualization tests passed!")