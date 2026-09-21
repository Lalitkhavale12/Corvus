"""Wave 0 stubs for Phase 2 registry lifecycle (FR-2.4, FR-3.1-FR-3.3, D-03/D-06/D-07).

All tests are red stubs: they reference not-yet-existing symbols in
src.evaluation.evaluate so collection succeeds but every test fails.
"""


def test_winner_is_strict_max_roc_auc():
    from src.evaluation import evaluate as eval_mod  # noqa

    assert hasattr(eval_mod, "select_winner"), "STUB: select_winner missing"
    assert False, "STUB: strict-max ROC-AUC winner selection not implemented"


def test_stage_transitions():
    from src.evaluation import evaluate as eval_mod  # noqa

    assert hasattr(eval_mod, "apply_registry_stages"), (
        "STUB: apply_registry_stages missing"
    )
    assert False, "STUB: winner-to-Staging / superseded-to-Archived not implemented"


def test_every_run_registers_version():
    from src.evaluation import evaluate as eval_mod  # noqa

    assert hasattr(eval_mod, "run_evaluation"), "STUB: run_evaluation missing"
    assert False, "STUB: every-run-registers-version not implemented"


def test_no_production_transition():
    from src.evaluation import evaluate as eval_mod  # noqa

    assert hasattr(eval_mod, "apply_registry_stages"), (
        "STUB: apply_registry_stages missing"
    )
    assert False, "STUB: no-Production-transition assertion not implemented"
