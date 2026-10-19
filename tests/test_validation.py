import pandas as pd
import pytest

from src.validation import validate_dataset


def valid_frame() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "horizonte": [1, 2],
            "inicio_semana_t": ["2023-01-02", "2024-01-01"],
            "data_corte": ["2023-01-08", "2024-01-07"],
            "inicio_semana_alvo": ["2023-01-09", "2024-01-15"],
            "ano_alvo": [2023, 2024],
            "target_casos": [3, 4],
            "split": ["validacao", "teste"],
            "cenario_geografico": ["principal_sem_importados_conhecidos"] * 2,
            "fonte_disponibilidade": ["DT_ENCERRA"] * 2,
        }
    )


def test_valid_dataset_passes():
    validate_dataset(valid_frame())


def test_duplicate_key_fails():
    frame = pd.concat([valid_frame().iloc[[0]]] * 2, ignore_index=True)
    with pytest.raises(ValueError, match="duplicada"):
        validate_dataset(frame)


def test_leakage_column_fails():
    frame = valid_frame()
    frame["casos_t_mais_1"] = 10
    with pytest.raises(ValueError, match="leakage"):
        validate_dataset(frame)


def test_wrong_target_date_fails():
    frame = valid_frame()
    frame.loc[0, "inicio_semana_alvo"] = "2023-01-02"
    with pytest.raises(ValueError, match="futuro"):
        validate_dataset(frame)
