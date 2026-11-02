"""
Model promotion module for Corvus CKD Prediction (Phase 5).

Implements champion/challenger model promotion logic:
- Compares new model performance with current production model
- Promotes challenger if it outperforms champion
- Updates configuration and MLflow model registry stage
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

import mlflow
from mlflow.tracking import MlflowClient

from src.utils.config import load_config
from src.utils.logger import get_logger

log = get_logger()


def get_model_versions(model_name: str = "corvus-ckd") -> list[dict]:
    """Get all model versions from MLflow model registry."""
    client = MlflowClient()
    
    try:
        versions = client.search_model_versions(f"name='{model_name}'")
    except Exception as e:
        log.warning(f"Failed to search model versions: {e}")
        return []
    
    results = []
    for mv in versions:
        results.append({
            "name": mv.name,
            "version": mv.version,
            "stage": mv.current_stage,
            "run_id": mv.run_id,
            "creation_timestamp": mv.creation_timestamp,
            "last_updated_timestamp": mv.last_updated_timestamp,
            "description": mv.description,
            "tags": dict(mv.tags),
            "metrics": mv.metadata.metrics if hasattr(mv, 'metadata') else {},
        })
    
    return results


def get_champion_model(model_name: str = "corvus-ckd") -> dict | None:
    """Get the current production (champion) model from MLflow registry."""
    client = MlflowClient()
    
    try:
        versions = client.search_model_versions(f"name='{model_name}' AND current_stage='Production'")
    except Exception as e:
        log.warning(f"Failed to search production model: {e}")
        return None
    
    if not versions:
        log.warning("No production model found")
        return None
    
    # Return the first production version
    mv = versions[0]
    return {
        "name": mv.name,
        "version": mv.version,
        "stage": mv.current_stage,
        "run_id": mv.run_id,
        "creation_timestamp": mv.creation_timestamp,
        "metrics": mv.metadata.metrics if hasattr(mv, 'metadata') else {},
    }


def get_challenger_models(model_name: str = "corvus-ckd") -> list[dict]:
    """Get all challenger (Staging) models from MLflow registry."""
    client = MlflowClient()
    
    try:
        versions = client.search_model_versions(f"name='{model_name}' AND current_stage='Staging'")
    except Exception as e:
        log.warning(f"Failed to search staging models: {e}")
        return []
    
    results = []
    for mv in versions:
        results.append({
            "name": mv.name,
            "version": mv.version,
            "stage": mv.current_stage,
            "run_id": mv.run_id,
            "creation_timestamp": mv.creation_timestamp,
            "metrics": mv.metadata.metrics if hasattr(mv, 'metadata') else {},
        })
    
    return results


def promote_challenger(
    model_name: str = "corvus-ckd",
    challenger_version: int | None = None,
    metric_name: str = "roc_auc",
    threshold_improvement: float = 0.01,
) -> dict:
    """
    Promote a challenger model to production if it outperforms the champion.
    
    Args:
        model_name: Name of the model in MLflow registry
        challenger_version: Specific version to promote (None = best challenger)
        metric_name: Metric to compare (e.g., 'roc_auc', 'f1', 'accuracy')
        threshold_improvement: Minimum improvement required (e.g., 0.01 = 1% better)
    
    Returns:
        Dictionary with promotion result
    """
    client = MlflowClient()
    
    # Get current champion
    champion = get_champion_model(model_name)
    
    # Get challengers
    challengers = get_challenger_models(model_name)
    
    if not challengers:
        log.warning("No challenger models found in Staging")
        return {"promoted": False, "reason": "No challenger models found"}
    
    # Select best challenger if not specified
    if challenger_version is None:
        # Sort by metric (higher is better for most metrics)
        challengers.sort(
            key=lambda m: m.get("metrics", {}).get(metric_name, 0),
            reverse=True,
        )
        challenger = challengers[0]
        challenger_version = challenger["version"]
    else:
        challenger = next((c for c in challengers if c["version"] == challenger_version), None)
        if challenger is None:
            log.error(f"Challenger version {challenger_version} not found in Staging")
            return {"promoted": False, "reason": "Challenger not found"}
    
    # Compare with champion
    champion_metric = champion.get("metrics", {}).get(metric_name, 0) if champion else 0
    challenger_metric = challenger.get("metrics", {}).get(metric_name, 0)
    
    log.info(f"Champion v{champion['version'] if champion else 'None'}: {metric_name} = {champion_metric}")
    log.info(f"Challenger v{challenger_version}: {metric_name} = {challenger_metric}")
    
    # Check if challenger is better
    if champion and champion_metric > 0:
        improvement = (challenger_metric - champion_metric) / champion_metric
        if improvement < threshold_improvement:
            log.info(
                f"Challenger improvement ({improvement:.4f}) below threshold "
                f"({threshold_improvement}). Not promoting."
            )
            return {
                "promoted": False,
                "reason": f"Improvement {improvement:.4f} below threshold {threshold_improvement}",
                "champion_version": champion["version"],
                "challenger_version": challenger_version,
                "champion_metric": champion_metric,
                "challenger_metric": challenger_metric,
            }
    
    # Promote challenger to Production
    try:
        client.transition_model_version_stage(
            name=model_name,
            version=challenger_version,
            stage="Production",
            archive_existing_versions=True,
        )
        log.info(f"Promoted model v{challenger_version} to Production")
        
        # Archive previous champion if different
        if champion and champion["version"] != challenger_version:
            client.transition_model_version_stage(
                name=model_name,
                version=champion["version"],
                stage="Archived",
            )
            log.info(f"Archived previous champion v{champion['version']}")
        
        return {
            "promoted": True,
            "champion_version": champion["version"] if champion else None,
            "challenger_version": challenger_version,
            "champion_metric": champion_metric,
            "challenger_metric": challenger_metric,
            "improvement": (challenger_metric - champion_metric) / champion_metric if champion_metric > 0 else None,
        }
    
    except Exception as e:
        log.error(f"Failed to promote challenger: {e}")
        return {"promoted": False, "reason": str(e)}


def evaluate_and_promote(
    model_name: str = "corvus-ckd",
    metric_name: str = "roc_auc",
    threshold_improvement: float = 0.01,
) -> dict:
    """
    Full promotion workflow: check drift, evaluate challenger, promote if better.
    
    Args:
        model_name: Name of the model in MLflow registry
        metric_name: Metric to compare
        threshold_improvement: Minimum improvement required
    
    Returns:
        Dictionary with promotion result
    """
    log.info("=" * 60)
    log.info("MODEL PROMOTION WORKFLOW")
    log.info("=" * 60)
    
    # Get current champion
    champion = get_champion_model(model_name)
    log.info(f"Current champion: v{champion['version'] if champion else 'None'}")
    
    # Get challengers
    challengers = get_challenger_models(model_name)
    log.info(f"Challenger models in Staging: {len(challengers)}")
    
    if not challengers:
        log.warning("No challenger models available for promotion")
        return {
            "promoted": False,
            "reason": "No challenger models in Staging",
        }
    
    # Promote best challenger
    result = promote_challenger(
        model_name=model_name,
        metric_name=metric_name,
        threshold_improvement=threshold_improvement,
    )
    
    log.info(f"Promotion result: {json.dumps(result, indent=2, default=str)}")
    
    return result


def update_config_with_pinned_version(
    model_version: str,
    config_path: str = "config/config.yaml",
) -> None:
    """
    Update config.yaml with the pinned model version.
    
    Args:
        model_version: Model version to pin
        config_path: Path to config.yaml
    """
    import yaml
    
    config_path = Path(config_path)
    if not config_path.exists():
        log.warning(f"Config file not found: {config_path}")
        return
    
    with open(config_path) as f:
        config = yaml.safe_load(f)
    
    config["api"]["v2_pinned_version"] = model_version
    
    with open(config_path, "w") as f:
        yaml.dump(config, f, default_flow_style=False)
    
    log.info(f"Updated config: api.v2_pinned_version = {model_version}")