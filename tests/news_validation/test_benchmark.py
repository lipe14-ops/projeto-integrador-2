"""Benchmark rotulado (SINTÉTICO) do Fact-Checker real, com HTTP simulado.

Os rótulos esperados vêm da especificação em ``cases.py`` e foram fixados antes
da execução. Os casos em que o sistema diverge NÃO foram relabelados: estão em
``KNOWN_LIMITATIONS`` como ``xfail(strict=True)``. Se o Fact-Checker passar a
acertar um deles, o teste falha (XPASS) e a limitação deve ser removida daqui
e da documentação.
"""

from __future__ import annotations

import pytest

from tests.news_validation.benchmark import run_benchmark, run_case
from tests.news_validation.cases import CASES

KNOWN_LIMITATIONS = {
    "P17": "número de 4 dígitos na manchete ('2000 casas') é lido como ano → rejeitada como retrospectiva (falso negativo)",
    "P23": "manchete em caixa alta: menção ao município é sensível a maiúsculas e, com nomes colidentes, a menção "
           "só no corpo exige estado/vizinho → rejeitada (falso negativo)",
    "N19": "não há verificação de polaridade/variável: 'falta de chuva' (estiagem) passa no tema → verificada (falso positivo)",
    "N21": "onda de calor com 'chuva' na manchete (previsão de retorno) → verificada (falso positivo)",
    "N26": "alerta/previsão não é distinguido de ocorrência → verificada (falso positivo)",
    "N27": "política pública com 'enchentes' na manchete → verificada (falso positivo)",
    "N28": "'cheia' é termo forte: 'casa cheia' passa no tema → verificada (falso positivo)",
    "N34": "menção incidental ao município-alvo ('a 260 km de Porto Alegre') conta como local do evento (falso positivo)",
    "N35": "menção incidental a vizinho ('em direção a Canoas') vira vínculo regional (falso positivo)",
    "A03": "vendaval sem chuva passa no tema ('vendava' é termo forte); variável da anomalia não é conferida (falso positivo)",
}


def _param(case):
    marks = []
    if case.id in KNOWN_LIMITATIONS:
        marks.append(pytest.mark.xfail(strict=True, reason=KNOWN_LIMITATIONS[case.id]))
    return pytest.param(case, id=case.id, marks=marks)


@pytest.mark.parametrize("case", [_param(c) for c in CASES])
def test_case_matches_specification(case):
    result = run_case(case)
    assert result.status in case.acceptable, (case.description, result.decision.reasons)
    if case.category == "positivo":
        if case.expected_relevance:
            assert result.decision.relevance_status == case.expected_relevance
        assert result.decision.duplicate_kind == case.expected_duplicate


def test_benchmark_is_large_and_balanced_enough():
    categories = {c.category for c in CASES}
    assert len(CASES) >= 40
    assert categories == {"positivo", "negativo", "pendente", "ambiguo"}
    assert sum(c.category == "positivo" for c in CASES) >= 15
    assert sum(c.category != "positivo" for c in CASES) >= 25


def test_benchmark_report_is_consistent_with_case_results():
    report = run_benchmark()
    m = report["metrics"]
    assert m["tp"] + m["fp"] + m["fn"] + m["tn"] == len(CASES)
    wrong = {r.case.id for r in report["results"] if not r.details_ok}
    # toda divergência é um achado documentado — nenhuma fica escondida
    assert wrong == set(KNOWN_LIMITATIONS)
    # nenhuma página inacessível ou sem data é aprovada
    assert all(r.status != "verified" for r in report["results"] if r.case.category == "pendente")
