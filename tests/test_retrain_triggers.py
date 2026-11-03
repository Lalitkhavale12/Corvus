"""Claim 5: the five retrain triggers and the champion/challenger verdict.

Pure logic only -- no Airflow scheduler, no MLflow server, no database.
"""

import pytest

from src.model_promotion import decide_promotion
from src.monitoring.retrain_triggers import TRIGGER_TYPES, evaluate_triggers


class TestTriggerSurface:
    def test_all_five_trigger_types_are_reported(self):
        verdict = evaluate_triggers()
        assert set(verdict["checks"]) == set(TRIGGER_TYPES)
        assert verdict["retrain"] is False
        assert verdict["fired_triggers"] == []

    def test_missing_evidence_never_counts_as_a_pass(self):
        verdict = evaluate_triggers()
        for check in verdict["checks"].values():
            assert check["fired"] is False
            assert check["detail"]


class TestScheduleTrigger:
    def test_fires_when_champion_is_older_than_the_window(self):
        verdict = evaluate_triggers(days_since_promotion=45, schedule_days=30)
        assert verdict["checks"]["schedule"]["fired"] is True
        assert "45.0d" in verdict["checks"]["schedule"]["detail"]

    def test_does_not_fire_inside_the_window(self):
        verdict = evaluate_triggers(days_since_promotion=3, schedule_days=30)
        assert verdict["checks"]["schedule"]["fired"] is False


class TestDriftTrigger:
    def test_fires_when_share_of_drifted_features_exceeds_threshold(self):
        drift_result = {"drift_check": {"drift_detected": True, "share_drifted_features": 0.42}}
        verdict = evaluate_triggers(drift_result=drift_result)
        assert verdict["checks"]["drift"]["fired"] is True

    def test_does_not_fire_on_a_single_drifted_column(self):
        """One column out of 23 is normal traffic, not a drift event."""
        pytest.importorskip("evidently", reason="declared optional at dev time")
        from src.monitoring.drift import check_drift_thresholds

        drift_check = check_drift_thresholds(
            {"share_drifted_features": 0.04, "n_drifted_features": 1, "n_features": 23}
        )
        assert drift_check["drift_detected"] is False
        verdict = evaluate_triggers(drift_result={"drift_check": drift_check})
        assert verdict["checks"]["drift"]["fired"] is False


class TestPerformanceTrigger:
    def test_fires_below_the_roc_floor(self):
        verdict = evaluate_triggers(labelled_roc_auc=0.71, roc_floor=0.80)
        assert verdict["checks"]["performance"]["fired"] is True

    def test_does_not_fire_above_the_floor(self):
        verdict = evaluate_triggers(labelled_roc_auc=0.82, roc_floor=0.80)
        assert verdict["checks"]["performance"]["fired"] is False


class TestVolumeTrigger:
    def test_fires_once_enough_new_rows_arrive(self):
        verdict = evaluate_triggers(new_rows_since_retrain=500, min_new_rows=500)
        assert verdict["checks"]["data_volume"]["fired"] is True

    def test_does_not_fire_below_the_bar(self):
        verdict = evaluate_triggers(new_rows_since_retrain=12, min_new_rows=500)
        assert verdict["checks"]["data_volume"]["fired"] is False


class TestManualTrigger:
    def test_fires_only_when_requested(self):
        assert evaluate_triggers(manual_requested=True)["checks"]["manual"]["fired"] is True
        assert evaluate_triggers()["checks"]["manual"]["fired"] is False


class TestRetrainDecision:
    def test_one_firing_trigger_is_enough(self):
        verdict = evaluate_triggers(manual_requested=True, days_since_promotion=1)
        assert verdict["retrain"] is True
        assert verdict["fired_triggers"] == ["manual"]

    def test_two_firing_triggers_are_both_reported(self):
        verdict = evaluate_triggers(manual_requested=True, days_since_promotion=90)
        assert verdict["retrain"] is True
        assert set(verdict["fired_triggers"]) == {"manual", "schedule"}


class TestPromotionVerdict:
    champion = {"version": "15", "roc_auc": 0.8214, "pr_auc": 0.55}

    def test_promotes_a_challenger_that_is_not_worse(self):
        verdict = decide_promotion(self.champion, {"roc_auc": 0.8215, "pr_auc": 0.55})
        assert verdict["promote"] is True
        assert verdict["reason"] == "no worse on ROC-AUC or PR-AUC"

    def test_refuses_a_challenger_below_the_deployment_floor(self):
        verdict = decide_promotion(self.champion, {"roc_auc": 0.74, "pr_auc": 0.60})
        assert verdict["promote"] is False
        assert "floor" in verdict["reason"]

    def test_refuses_a_challenger_that_ranks_worse(self):
        verdict = decide_promotion(self.champion, {"roc_auc": 0.8050, "pr_auc": 0.55})
        assert verdict["promote"] is False
        assert "worse than champion" in verdict["reason"]

    def test_refuses_matching_roc_with_worse_pr_auc(self):
        verdict = decide_promotion(self.champion, {"roc_auc": 0.8214, "pr_auc": 0.48})
        assert verdict["promote"] is False
        assert "PR-AUC" in verdict["reason"]

    def test_promotes_the_first_model_when_nothing_is_pinned(self):
        verdict = decide_promotion(None, {"roc_auc": 0.81})
        assert verdict["promote"] is True
        assert verdict["reason"] == "no champion pinned yet"

    def test_refuses_to_promote_blind_when_champion_metrics_are_missing(self):
        verdict = decide_promotion({"version": "15"}, {"roc_auc": 0.85})
        assert verdict["promote"] is False
        assert "blind" in verdict["reason"]

    def test_refuses_when_the_challenger_has_no_metrics(self):
        verdict = decide_promotion(self.champion, {})
        assert verdict["promote"] is False
        assert "unavailable" in verdict["reason"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
