"""Tipos comuns aos agentes.

Cada agente é uma classe com responsabilidade única, identificada por
``name``. Toda decisão é devolvida como ``AgentReport`` com veredito,
justificativas e métricas, para que o orquestrador possa persistir a trilha de
auditoria completa (quem decidiu, o quê, com base em quê e quando).
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class AgentReport:
    agent: str
    verdict: str
    justification: list[str] = field(default_factory=list)
    metrics: dict = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: utcnow().isoformat())

    def to_dict(self) -> dict:
        return asdict(self)


AGENT_NAMES = {
    "orchestrator": "Orquestrador",
    "software_engineer": "Engenheiro de Software",
    "computer_scientist": "Cientista da Computação",
    "data_scientist": "Cientista de Dados",
    "climatologist": "Climatologista",
    "meteorologist": "Meteorologista",
    "news_researcher": "News Researcher",
    "fact_checker": "Fact-Checker",
}


@dataclass
class MunicipalityContext:
    """Contexto geográfico compartilhado entre os agentes."""

    name: str
    uf: str | None = None
    state: str | None = None
    region: str | None = None
    codigo_ibge: int | None = None
    neighbors: list[str] = field(default_factory=list)
    homonym: bool = False  # existe município homônimo (mesmo nome) em outra UF
    # outros municípios cujo nome contém este (ex.: "Lucas do Rio Verde" para "Rio Verde")
    colliding_names: list[str] = field(default_factory=list)

    def label(self) -> str:
        return f"{self.name}/{self.uf}" if self.uf else self.name
