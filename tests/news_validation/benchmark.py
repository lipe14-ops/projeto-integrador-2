"""Executa o Fact-Checker REAL sobre o benchmark sintético e calcula as métricas.

Uso (gera o log da execução):

    uv run python -m tests.news_validation.benchmark [arquivo_de_log]
"""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from pathlib import Path

from app.climate_news.agents.fact_checker import FactCheckDecision, FactCheckerAgent
from app.climate_news.validation import confusion_table, decision_metrics
from tests.news_validation.cases import CASES, CONTEXTS, BenchmarkHttpClient, Case


@dataclass
class CaseResult:
    case: Case
    decision: FactCheckDecision

    @property
    def status(self) -> str:
        return self.decision.status

    @property
    def status_ok(self) -> bool:
        return self.status in self.case.acceptable

    @property
    def details_ok(self) -> bool:
        """Relevância e duplicata esperadas (só se o status esperado foi atingido)."""
        if not self.status_ok or self.case.category != "positivo":
            return self.status_ok
        relevance = self.case.expected_relevance is None or self.decision.relevance_status == self.case.expected_relevance
        return relevance and self.decision.duplicate_kind == self.case.expected_duplicate

    @property
    def first_failure(self) -> str | None:
        reasons = [r for r in self.decision.reasons if not r.startswith("claimed_date_differs")]
        return reasons[0] if reasons else None


def run_case(case: Case) -> CaseResult:
    agent = FactCheckerAgent(BenchmarkHttpClient(case.pages))
    ctx = CONTEXTS[case.ctx]
    for url, headline in case.preload:
        agent.verify(case.candidate(url, headline), ctx)
    return CaseResult(case, agent.verify(case.candidate(), ctx))


def run_benchmark(cases: list[Case] = CASES) -> dict:
    results = [run_case(c) for c in cases]
    metrics = decision_metrics([r.case.expected_positive for r in results], [r.status for r in results])
    table = confusion_table([r.case.expected for r in results], [r.status for r in results])
    by_category: dict[str, dict] = {}
    for r in results:
        row = by_category.setdefault(r.case.category, {"n": 0, "conforme": 0})
        row["n"] += 1
        row["conforme"] += r.status_ok
    return {
        "results": results,
        "metrics": metrics,
        "confusion": table,
        "by_category": by_category,
        "status_conformity": sum(r.status_ok for r in results) / len(results),
        "full_conformity": sum(r.details_ok for r in results) / len(results),
    }


def format_report(report: dict) -> str:
    lines = ["BENCHMARK SINTÉTICO DO FACT-CHECKER (dados fictícios; mede conformidade à especificação)", ""]
    m = report["metrics"]
    lines.append(f"casos: {m['n']}  por categoria: {json.dumps(report['by_category'], ensure_ascii=False)}")
    lines.append(f"matriz (positivo = verified): TP={m['tp']:.0f} FP={m['fp']:.0f} FN={m['fn']:.0f} TN={m['tn']:.0f}")
    fmt = lambda v: "n/d" if v is None else f"{v:.3f}"  # noqa: E731
    for key in ("precision", "recall", "f1", "false_positive_rate", "false_negative_rate", "accuracy"):
        lines.append(f"{key}: {fmt(m[key])}")
    lines.append(
        f"pending: total={m['pending_total']} entre positivos={m['pending_among_positive']} "
        f"entre negativos={m['pending_among_negative']}"
    )
    lines.append(f"conformidade de status (inclui pending vs rejected): {report['status_conformity']:.3f}")
    lines.append(f"conformidade completa (status + relevância + duplicata): {report['full_conformity']:.3f}")
    lines.append("tabela esperado × previsto: " + json.dumps(report["confusion"], ensure_ascii=False))
    lines.append("")
    lines.append("id | categoria | esperado | previsto | relevância | duplicata | ok | primeiro motivo")
    for r in report["results"]:
        d = r.decision
        lines.append(
            f"{r.case.id} | {r.case.category} | {r.case.expected} | {d.status} | {d.relevance_status} | "
            f"{d.duplicate_kind} | {'OK' if r.details_ok else 'DIVERGE'} | {r.first_failure or '-'}"
        )
    return "\n".join(lines)


if __name__ == "__main__":
    text = format_report(run_benchmark())
    print(text)
    if len(sys.argv) > 1:
        Path(sys.argv[1]).write_text(text + "\n", encoding="utf-8")
