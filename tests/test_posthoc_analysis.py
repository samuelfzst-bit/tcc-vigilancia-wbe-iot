import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from src.posthoc_analysis import (
    dashboard_predictions,
    threshold_sensitivity,
    validate_final_run,
    weekly_error_audit,
)


def sample_predictions() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "horizonte": [1, 1, 1, 1],
            "inicio_semana_alvo": pd.date_range("2024-01-07", periods=4, freq="W"),
            "observado": [0.0, 2.0, 4.0, 6.0],
            "previsto": [1.0, 3.0, 3.0, 5.0],
            "erro": [1.0, 1.0, -1.0, -1.0],
            "erro_absoluto": [1.0, 1.0, 1.0, 1.0],
            "limiar_alerta": [4.0] * 4,
            "alerta_observado": [False, False, True, True],
            "alerta_previsto": [False, False, False, True],
        }
    )


def test_threshold_four_remains_official() -> None:
    result = threshold_sensitivity(sample_predictions(), thresholds=(2, 4))
    official = result.loc[result["limiar_alerta"].eq(4)].iloc[0]
    exploratory = result.loc[result["limiar_alerta"].eq(2)].iloc[0]
    assert official["status_metodologico"] == "oficial_congelado"
    assert exploratory["status_metodologico"] == "exploratorio_pos_hoc"
    assert official["falsos_negativos"] == 1


def test_weekly_audit_classifies_alert_errors() -> None:
    result = weekly_error_audit(sample_predictions())
    assert set(result["tipo_alerta"]) == {
        "verdadeiro_positivo",
        "falso_negativo",
        "verdadeiro_negativo",
    }
    assert set(result["ranking_erro_absoluto"]) == {1, 2, 3, 4}


def test_dashboard_uses_attention_without_changing_alert() -> None:
    protocol = {"versao_protocolo": "v1"}
    manifest = {"git_commit": "abc123"}
    result = dashboard_predictions(
        sample_predictions(), protocol, manifest, execution_id="run-1"
    )
    assert result["nivel_previsto"].tolist() == ["normal", "atencao", "atencao", "alerta"]
    assert result["limiar_alerta"].eq(4).all()
    assert result["limiar_atencao"].eq(2).all()
    assert result["cenario_geografico"].eq(
        "principal_sem_importados_conhecidos"
    ).all()
    assert pd.to_datetime(result["inicio_semana_alvo"]).sub(
        pd.to_datetime(result["inicio_semana_t"])
    ).dt.days.eq(7).all()


def test_integrity_check_rejects_changed_file(tmp_path: Path) -> None:
    tracked = tmp_path / "resultado.csv"
    tracked.write_text("ok", encoding="utf-8")
    import hashlib

    digest = hashlib.sha256(b"ok").hexdigest()
    manifest = {
        "test_opened_once": True,
        "model_change_after_test_allowed": False,
        "files": {"resultado.csv": digest},
    }
    (tmp_path / "manifest_final.json").write_text(json.dumps(manifest), encoding="utf-8")
    validate_final_run(tmp_path)
    tracked.write_text("alterado", encoding="utf-8")
    with pytest.raises(ValueError, match="hash divergente"):
        validate_final_run(tmp_path)
