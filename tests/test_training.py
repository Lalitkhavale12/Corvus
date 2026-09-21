"""Wave 0 stubs for Phase 2 training path (FR-2.1-FR-2.5, Claim 2).

All tests are red stubs: they reference not-yet-existing symbols in
src.training.train so collection succeeds but every test fails.
"""


def test_all_nine_configs_construct():
    from src.training import train as train_mod  # noqa

    assert hasattr(train_mod, "ESTIMATORS"), "STUB: ESTIMATORS registry missing"
    assert False, "STUB: all-nine-configs-construct not implemented"


def test_lineage_excluded_feature_count_24():
    from src.training import train as train_mod  # noqa

    assert hasattr(train_mod, "load_raw_splits"), "STUB: load_raw_splits missing"
    assert False, "STUB: lineage-excluded feature count != 24 not implemented"


def test_loader_reads_raw_only():
    from src.training import train as train_mod  # noqa

    assert hasattr(train_mod, "load_raw_splits"), "STUB: load_raw_splits missing"
    assert False, "STUB: loader raw-only assertion not implemented"


def test_run_logs_pipeline_and_model(tmp_mlflow_store):
    from src.training import train as train_mod  # noqa

    assert hasattr(train_mod, "run_experiment"), "STUB: run_experiment missing"
    assert False, "STUB: Claim 2 run-logs-pipeline-and-model not implemented"
