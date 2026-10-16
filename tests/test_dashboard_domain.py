import pytest

from frontend.domain import level_label, prediction_level


@pytest.mark.parametrize(
    ("value", "expected"),
    [(0, "normal"), (1.99, "normal"), (2, "atencao"), (3.99, "atencao"), (4, "alerta")],
)
def test_prediction_level(value, expected):
    assert prediction_level(value) == expected


def test_level_label_rejects_unknown_value():
    with pytest.raises(ValueError):
        level_label("desconhecido")
