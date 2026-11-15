"""Métricas para validar a verificação automática de notícias (Fact-Checker).

Convenção usada em todo o módulo:

- **predição positiva** = o sistema marcou o vínculo anomalia × notícia como
  ``verified``; ``rejected`` e ``pending_verification`` são predições
  negativas (nenhuma das duas associa a notícia à anomalia). ``pending`` é
  contado à parte, para não esconder a parcela que o sistema não decidiu;
- **positivo verdadeiro** (rótulo de referência) = a notícia de fato relata o
  evento de chuva da anomalia, segundo a especificação (benchmark sintético)
  ou segundo os anotadores humanos (amostra real).

Nada aqui inventa valores: quando um denominador é zero, a métrica é ``None``.
"""

from __future__ import annotations

import csv
import math
from collections import Counter
from collections.abc import Iterable, Sequence
from pathlib import Path

SYSTEM_STATUSES = ("verified", "rejected", "pending_verification")

# Rótulos permitidos na anotação humana (amostra real)
ANNOTATION_POSITIVE = "confirma"
ANNOTATION_NEGATIVE = "nao_confirma"
ANNOTATION_UNDETERMINED = "indeterminado"
ANNOTATION_LABELS = (ANNOTATION_POSITIVE, ANNOTATION_NEGATIVE, ANNOTATION_UNDETERMINED)


def _ratio(num: float, den: float) -> float | None:
    return num / den if den else None


def binary_metrics(
    y_true: Iterable[bool], y_pred: Iterable[bool], weights: Iterable[float] | None = None
) -> dict:
    """Matriz de confusão 2×2 e métricas derivadas.

    ``weights`` (opcional) permite estimar a matriz da população a partir de
    uma amostra estratificada (peso = tamanho do estrato / tamanho da amostra
    do estrato). Sem pesos, cada caso vale 1.
    """
    y_true, y_pred = list(y_true), list(y_pred)
    if len(y_true) != len(y_pred):
        raise ValueError("y_true e y_pred precisam ter o mesmo tamanho")
    w = list(weights) if weights is not None else [1.0] * len(y_true)
    if len(w) != len(y_true):
        raise ValueError("weights precisa ter o mesmo tamanho de y_true")
    tp = fp = fn = tn = 0.0
    for t, p, weight in zip(y_true, y_pred, w):
        if t and p:
            tp += weight
        elif p:
            fp += weight
        elif t:
            fn += weight
        else:
            tn += weight
    precision = _ratio(tp, tp + fp)
    recall = _ratio(tp, tp + fn)
    f1 = (
        2 * precision * recall / (precision + recall)
        if precision is not None and recall is not None and (precision + recall) > 0
        else None
    )
    return {
        "n": len(y_true),
        "tp": tp, "fp": fp, "fn": fn, "tn": tn,
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "false_positive_rate": _ratio(fp, fp + tn),
        "false_negative_rate": _ratio(fn, fn + tp),
        "accuracy": _ratio(tp + tn, tp + fp + fn + tn),
    }


def decision_metrics(expected_positive: Sequence[bool], predicted_status: Sequence[str]) -> dict:
    """Métricas do Fact-Checker: ``verified`` é a predição positiva.

    Além da matriz binária, informa quantos casos ficaram ``pending`` entre
    os positivos e os negativos de referência.
    """
    unknown = set(predicted_status) - set(SYSTEM_STATUSES)
    if unknown:
        raise ValueError(f"status desconhecido: {sorted(unknown)}")
    metrics = binary_metrics(expected_positive, [s == "verified" for s in predicted_status])
    metrics["pending_total"] = sum(s == "pending_verification" for s in predicted_status)
    metrics["pending_among_positive"] = sum(
        t and s == "pending_verification" for t, s in zip(expected_positive, predicted_status)
    )
    metrics["pending_among_negative"] = sum(
        (not t) and s == "pending_verification" for t, s in zip(expected_positive, predicted_status)
    )
    return metrics


def confusion_table(expected: Sequence[str], predicted: Sequence[str]) -> dict[str, dict[str, int]]:
    """Tabela de contingência rótulo esperado × status previsto (contagens)."""
    table: dict[str, dict[str, int]] = {}
    for e, p in zip(expected, predicted):
        row = table.setdefault(e, {})
        row[p] = row.get(p, 0) + 1
    return table


def cohen_kappa(a: Sequence[str], b: Sequence[str]) -> dict:
    """Kappa de Cohen entre dois anotadores (rótulos nominais).

    κ = (p_o − p_e) / (1 − p_e). Se p_e = 1 (ambos usaram um único rótulo
    idêntico em todos os casos), κ é indefinido e devolvido como ``None``.
    """
    if len(a) != len(b):
        raise ValueError("as duas listas de rótulos precisam ter o mesmo tamanho")
    n = len(a)
    if n == 0:
        return {"n": 0, "observed_agreement": None, "expected_agreement": None, "kappa": None}
    observed = sum(x == y for x, y in zip(a, b)) / n
    ca, cb = Counter(a), Counter(b)
    expected = sum(ca[label] * cb[label] for label in set(ca) | set(cb)) / (n * n)
    kappa = (observed - expected) / (1 - expected) if expected < 1 else None
    return {"n": n, "observed_agreement": observed, "expected_agreement": expected, "kappa": kappa}


def wilson_interval(successes: float, total: float, z: float = 1.96) -> tuple[float, float] | None:
    """Intervalo de Wilson (95% por padrão) para uma proporção."""
    if total <= 0:
        return None
    p = successes / total
    den = 1 + z * z / total
    center = (p + z * z / (2 * total)) / den
    half = z * math.sqrt(p * (1 - p) / total + z * z / (4 * total * total)) / den
    return max(0.0, center - half), min(1.0, center + half)


# ---------------------------------------------------------------------------
# Anotação humana (amostra real)
# ---------------------------------------------------------------------------


def gold_label(row: dict) -> str | None:
    """Rótulo de referência de uma linha anotada.

    Usa ``rotulo_adjudicado`` se preenchido; senão, o rótulo comum aos dois
    anotadores. Discordância sem adjudicação → ``None`` (fica fora das métricas).
    """
    adjudicated = (row.get("rotulo_adjudicado") or "").strip()
    if adjudicated:
        return adjudicated
    a = (row.get("rotulo_anotador_1") or "").strip()
    b = (row.get("rotulo_anotador_2") or "").strip()
    return a if a and a == b else None


def evaluate_annotations(rows: Sequence[dict]) -> dict:
    """Métricas a partir do CSV de anotação preenchido.

    - concordância (κ) calculada nas linhas em que os dois anotadores preencheram;
    - métricas do sistema nas linhas com rótulo de referência ``confirma`` ou
      ``nao_confirma`` (``indeterminado`` e discordâncias sem adjudicação são
      contadas, mas excluídas);
    - versão ponderada pelo ``peso_amostral`` (estimativa para a população) e
      não ponderada (a amostra como está).
    """
    for i, row in enumerate(rows, start=2):
        for column in ("rotulo_anotador_1", "rotulo_anotador_2", "rotulo_adjudicado"):
            value = (row.get(column) or "").strip()
            if value and value not in ANNOTATION_LABELS:
                raise ValueError(f"linha {i}: {column}={value!r} fora de {ANNOTATION_LABELS}")

    both = [
        (r["rotulo_anotador_1"].strip(), r["rotulo_anotador_2"].strip())
        for r in rows
        if (r.get("rotulo_anotador_1") or "").strip() and (r.get("rotulo_anotador_2") or "").strip()
    ]
    kappa = cohen_kappa([a for a, _ in both], [b for _, b in both])

    usable, excluded = [], Counter()
    for r in rows:
        gold = gold_label(r)
        if gold in (ANNOTATION_POSITIVE, ANNOTATION_NEGATIVE):
            usable.append((r, gold == ANNOTATION_POSITIVE))
        else:
            excluded[gold or "sem_rotulo_ou_discordante"] += 1

    statuses = [r["status_sistema"] for r, _ in usable]
    truth = [t for _, t in usable]
    unweighted = decision_metrics(truth, statuses)
    weights = [float(r.get("peso_amostral") or 1.0) for r, _ in usable]
    weighted = binary_metrics(truth, [s == "verified" for s in statuses], weights)

    verified = [(r, t) for r, t in usable if r["status_sistema"] == "verified"]
    precision_ci = wilson_interval(sum(t for _, t in verified), len(verified))
    return {
        "rows": len(rows),
        "rows_with_both_annotations": len(both),
        "agreement": kappa,
        "rows_used_for_metrics": len(usable),
        "rows_excluded": dict(excluded),
        "metrics_unweighted": unweighted,
        "metrics_weighted_by_stratum": weighted,
        "precision_wilson_95_unweighted": precision_ci,
    }


def load_annotation_csv(path: str | Path) -> list[dict]:
    with open(path, newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))
