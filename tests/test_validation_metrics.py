"""Testes das métricas de validação (app/climate_news/validation.py)."""

from __future__ import annotations

import csv

import pytest

from app.climate_news.validation import (
    binary_metrics,
    cohen_kappa,
    confusion_table,
    decision_metrics,
    evaluate_annotations,
    gold_label,
    load_annotation_csv,
    wilson_interval,
)


def test_binary_metrics_known_values():
    y_true = [True] * 8 + [False] * 12
    y_pred = [True] * 6 + [False] * 2 + [True] * 3 + [False] * 9
    m = binary_metrics(y_true, y_pred)
    assert (m["tp"], m["fn"], m["fp"], m["tn"]) == (6, 2, 3, 9)
    assert m["precision"] == pytest.approx(6 / 9)
    assert m["recall"] == pytest.approx(6 / 8)
    assert m["f1"] == pytest.approx(2 * (6 / 9) * (6 / 8) / ((6 / 9) + (6 / 8)))
    assert m["false_positive_rate"] == pytest.approx(3 / 12)
    assert m["false_negative_rate"] == pytest.approx(2 / 8)
    assert m["accuracy"] == pytest.approx(15 / 20)


def test_undefined_metrics_are_none_not_zero():
    m = binary_metrics([False, False], [False, False])
    assert m["precision"] is None and m["recall"] is None and m["f1"] is None
    assert m["false_positive_rate"] == 0.0


def test_weighted_metrics_scale_counts():
    m = binary_metrics([True, False], [True, True], weights=[10, 30])
    assert (m["tp"], m["fp"]) == (10, 30)
    assert m["precision"] == pytest.approx(0.25)


def test_decision_metrics_treats_only_verified_as_positive_and_counts_pending():
    m = decision_metrics(
        [True, True, False, False], ["verified", "pending_verification", "pending_verification", "rejected"]
    )
    assert (m["tp"], m["fn"], m["fp"], m["tn"]) == (1, 1, 0, 2)
    assert (m["pending_total"], m["pending_among_positive"], m["pending_among_negative"]) == (2, 1, 1)
    with pytest.raises(ValueError):
        decision_metrics([True], ["aprovado"])


def test_confusion_table():
    assert confusion_table(["a", "a", "b"], ["x", "y", "x"]) == {"a": {"x": 1, "y": 1}, "b": {"x": 1}}


def test_cohen_kappa_reference_example():
    # exemplo clássico: 50 itens, concordância observada 0,70, esperada 0,50 → κ = 0,40
    a = ["s"] * 20 + ["s"] * 5 + ["n"] * 10 + ["n"] * 15
    b = ["s"] * 20 + ["n"] * 5 + ["s"] * 10 + ["n"] * 15
    k = cohen_kappa(a, b)
    assert k["observed_agreement"] == pytest.approx(0.70)
    assert k["expected_agreement"] == pytest.approx(0.50)
    assert k["kappa"] == pytest.approx(0.40)


def test_cohen_kappa_perfect_and_undefined():
    assert cohen_kappa(["a", "b"], ["a", "b"])["kappa"] == pytest.approx(1.0)
    assert cohen_kappa(["a", "a"], ["a", "a"])["kappa"] is None  # p_e = 1
    assert cohen_kappa([], [])["kappa"] is None


def test_wilson_interval():
    low, high = wilson_interval(8, 10)
    assert low == pytest.approx(0.490, abs=1e-3) and high == pytest.approx(0.943, abs=1e-3)
    assert wilson_interval(0, 0) is None


def test_gold_label_rules():
    assert gold_label({"rotulo_anotador_1": "confirma", "rotulo_anotador_2": "confirma"}) == "confirma"
    assert gold_label({"rotulo_anotador_1": "confirma", "rotulo_anotador_2": "nao_confirma"}) is None
    assert gold_label({"rotulo_anotador_1": "confirma", "rotulo_anotador_2": "nao_confirma",
                       "rotulo_adjudicado": "nao_confirma"}) == "nao_confirma"


def _row(status, a1, a2, peso="1"):
    return {"status_sistema": status, "rotulo_anotador_1": a1, "rotulo_anotador_2": a2,
            "rotulo_adjudicado": "", "peso_amostral": peso}


def test_evaluate_annotations_end_to_end(tmp_path):
    # linhas FICTÍCIAS, só para testar o cálculo
    rows = [
        _row("verified", "confirma", "confirma", "2"),
        _row("verified", "nao_confirma", "nao_confirma", "2"),
        _row("rejected", "confirma", "confirma", "5"),
        _row("rejected", "nao_confirma", "nao_confirma", "5"),
        _row("pending_verification", "indeterminado", "indeterminado", "3"),
        _row("rejected", "confirma", "nao_confirma", "5"),
    ]
    path = tmp_path / "anotado.csv"
    with open(path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    result = evaluate_annotations(load_annotation_csv(path))
    assert result["rows_used_for_metrics"] == 4
    assert result["rows_excluded"] == {"indeterminado": 1, "sem_rotulo_ou_discordante": 1}
    assert result["metrics_unweighted"]["precision"] == pytest.approx(0.5)
    assert result["metrics_unweighted"]["recall"] == pytest.approx(0.5)
    w = result["metrics_weighted_by_stratum"]
    assert (w["tp"], w["fp"], w["fn"], w["tn"]) == (2, 2, 5, 5)
    assert result["agreement"]["n"] == 6
    assert result["agreement"]["observed_agreement"] == pytest.approx(5 / 6)


def test_evaluate_annotations_rejects_unknown_labels():
    with pytest.raises(ValueError):
        evaluate_annotations([_row("verified", "sim", "confirma")])
