"""Definições operacionais: anomalia estatística × evento extremo × impacto.

Os conceitos ficam em **eixos independentes** e nunca são sinônimos:

1. **Anomalia estatística** (eixo da detecção): o valor observado se afasta do
   que um modelo estatístico esperava (|Z| > 3 no resíduo de previsão de um
   passo). Mede *surpresa* em relação ao passado recente, não magnitude. Uma
   chuva de 12 mm depois de semanas secas pode ser anomalia; 40 mm durante uma
   semana chuvosa pode não ser.
2. **Evento meteorológico extremo** (eixo climatológico): o valor é *raro para
   o lugar e a época do ano*, medido contra a climatologia local dos anos
   anteriores (percentis). Segue a definição do glossário do IPCC (evento tão
   raro quanto ou mais raro que o percentil 10 ou 90 da distribuição observada)
   e a lógica dos índices ETCCDI (R95p/R99p, TX90p). Usamos limiares mais
   estritos que o P90 do IPCC: P95/P99 para chuva e P90/P99 (ou P10/P1) para
   temperatura e umidade.
3. **Intensidade absoluta** (eixo meteorológico): volume capaz de causar
   impacto em qualquer lugar (≥ 50 mm/dia ou ≥ 100 mm/5 dias, faixas de
   referência do INMET). Independe do clima local.
4. **Impacto documentado** (eixo social): há notícia verificada na página
   original. Notícia **não** confirma o fenômeno meteorológico: confirma que
   houve cobertura de uma ocorrência na região e na época.

**Evento climático extremo** (escala de estação, meses ou anos: seca
prolongada, estação chuvosa anômala) não é detectado por estes detectores
diários. Com 11 anos de dados, percentis de totais sazonais teriam ~10 valores
por município, insuficientes; fica registrado como limitação.

A ``classify_*`` devolve uma classe **mutuamente exclusiva** (para mapas e
contagens) e os eixos ortogonais como atributos booleanos.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass

# classe → (rótulo, definição operacional, é extremo meteorológico?)
CLASS_DEFINITIONS: dict[str, dict] = {
    "artefato_provavel": {
        "label": "Provável artefato de dado",
        "definition": "Sinalizada pelo detector, mas o Cientista de Dados apontou traço de chuva (< 1 mm) "
        "ou base próxima de zero. Excluída de todas as contagens.",
        "is_extreme": False,
        "counted": False,
    },
    "anomalia_estatistica": {
        "label": "Anomalia apenas estatística",
        "definition": "Z > 3 no resíduo do ARIMA, mas o volume está dentro da variabilidade local "
        "(abaixo do P95 dos dias chuvosos e do P95 da época). Surpresa em relação aos dias anteriores, "
        "não raridade climatológica.",
        "is_extreme": False,
        "counted": True,
    },
    "extremo_sazonal": {
        "label": "Extremo para a época do ano",
        "definition": "Volume comum no ano, mas ≥ P95 dos dias chuvosos da mesma época (±15 dias) nos anos "
        "anteriores, ou ≥ P99 de todos os dias da época na estação seca (com pelo menos 10 mm).",
        "is_extreme": True,
        "counted": True,
    },
    "extremo_local": {
        "label": "Extremo diário para o local",
        "definition": "Chuva diária ≥ P95 dos dias chuvosos (≥ 1 mm) do município nos anos anteriores "
        "(nível 'p99' quando ≥ P99).",
        "is_extreme": True,
        "counted": True,
    },
    "extremo_acumulado": {
        "label": "Extremo de chuva persistente",
        "definition": "Soma de 3 ou 5 dias ≥ P99 das somas de mesma duração dos anos anteriores "
        "(nível 'recorde' quando supera o máximo anterior).",
        "is_extreme": True,
        "counted": True,
    },
    "dado_incompleto": {
        "label": "Calculado sobre dado incompleto",
        "definition": "Anomalia diária cujo dia anterior está ausente (a previsão vira de dois passos) ou acumulado "
        "cuja janela contém dia ausente (a soma é extrapolada). Os dados ERA5-Land do projeto não têm o registro "
        "das 00 UTC do dia 1º de cada mês, então o último dia de cada mês fica ausente. Excluída das contagens.",
        "is_extreme": False,
        "counted": False,
    },
    "anomalia_negativa": {
        "label": "Chuva abaixo do previsto",
        "definition": "Z < −3: choveu bem menos que o previsto para o dia. Não é tratada como evento de chuva.",
        "is_extreme": False,
        "counted": False,
    },
}

# temperatura e umidade (detector ``thermal``)
THERMAL_CLASS_DEFINITIONS: dict[str, dict] = {
    "anomalia_estatistica": {
        "label": "Anomalia apenas estatística",
        "definition": "|Z| > 3 no resíduo do modelo AR, mas o valor fica entre P10 e P90 da mesma época "
        "(±15 dias) nos anos anteriores: mudança brusca, não valor raro.",
        "is_extreme": False,
        "counted": True,
    },
    "extremo_local": {
        "label": "Extremo para o local e a época",
        "definition": "Valor ≥ P90 (anomalia positiva) ou ≤ P10 (negativa) da mesma época (±15 dias) nos anos "
        "anteriores; limiar análogo ao dos índices TX90p/TN10p do ETCCDI, mas com referência curta (a partir de "
        "~60 dias no primeiro ano pontuado). Nível 'p99' quando ≥ P99 ou ≤ P1.",
        "is_extreme": True,
        "counted": True,
    },
}

CLIMATE_VERDICT_TO_CLASS = {
    "within_normal_variability": "anomalia_estatistica",
    "unusual_for_season": "extremo_sazonal",
    "very_heavy_for_location": "extremo_local",
    "exceptional_for_location": "extremo_local",
    "exceptional_accumulation": "extremo_acumulado",
    "record_accumulation": "extremo_acumulado",
}


@dataclass(frozen=True)
class EventClassification:
    event_class: str
    level: str | None  # p95 | p99 | recorde | p90 | None
    is_extreme: bool
    high_absolute_intensity: bool  # Meteorologista: ≥ 50 mm/dia ou ≥ 100 mm/5 dias
    documented_impact: bool  # ≥ 1 notícia verificada
    counted: bool

    def to_dict(self) -> dict:
        return asdict(self)


def classify_precipitation(
    detector: str,
    direction: str,
    data_verdict: str | None,
    climate_verdict: str | None,
    weather_verdict: str | None,
    verified_news: int = 0,
    complete_input: bool = True,
) -> EventClassification:
    """Classe operacional de uma anomalia de chuva já revisada pelos agentes.

    A ordem importa: artefato e direção negativa vêm antes da climatologia.
    Veredito climatológico ausente ou desconhecido cai em ``anomalia_estatistica``
    (a hipótese conservadora: não chamar de extremo sem evidência).
    """
    if detector not in {"arima_zscore", "accumulation_percentile"}:
        raise ValueError(f"detector desconhecido: {detector!r}")
    if direction not in {"positive", "negative"}:
        raise ValueError(f"direção desconhecida: {direction!r}")
    impact = bool(verified_news and verified_news > 0)
    intense = weather_verdict == "plausible_extreme_event"

    def make(event_class: str, level: str | None = None) -> EventClassification:
        definition = CLASS_DEFINITIONS[event_class]
        return EventClassification(
            event_class, level, definition["is_extreme"], intense, impact, definition["counted"]
        )

    if not complete_input:
        return make("dado_incompleto")
    if data_verdict == "possible_artifact":
        return make("artefato_provavel")
    if direction == "negative":
        return make("anomalia_negativa")
    if detector == "accumulation_percentile":
        # o próprio detector já exige ≥ P99 dos acumulados anteriores
        return make("extremo_acumulado", "recorde" if climate_verdict == "record_accumulation" else "p99")
    event_class = CLIMATE_VERDICT_TO_CLASS.get(climate_verdict or "", "anomalia_estatistica")
    if event_class == "extremo_acumulado":  # veredito incoerente com o detector diário
        event_class = "anomalia_estatistica"
    level = {"exceptional_for_location": "p99", "very_heavy_for_location": "p95"}.get(climate_verdict or "")
    return make(event_class, level)


def classify_thermal(climate_percentile: float | None, direction: str | None = None) -> EventClassification:
    """Classe de uma anomalia de temperatura/umidade pelo percentil da época.

    ``climate_percentile`` (0–100) é a posição do valor entre os dias da mesma
    época (±15 dias) dos anos anteriores. Sem percentil → anomalia estatística.
    Com ``direction``, só conta a cauda do mesmo lado: uma anomalia positiva
    (mais quente que o previsto) num valor baixo para a época não é extremo.
    """
    if climate_percentile is None or climate_percentile != climate_percentile:  # NaN
        return EventClassification("anomalia_estatistica", None, False, False, False, True)
    if not 0 <= climate_percentile <= 100:
        raise ValueError("percentil deve estar entre 0 e 100")
    if direction not in (None, "positive", "negative"):
        raise ValueError(f"direção desconhecida: {direction!r}")
    if direction == "positive":
        tail = climate_percentile
    elif direction == "negative":
        tail = 100 - climate_percentile
    else:
        tail = max(climate_percentile, 100 - climate_percentile)
    if tail >= 99:
        return EventClassification("extremo_local", "p99", True, False, False, True)
    if tail >= 90:
        return EventClassification("extremo_local", "p90", True, False, False, True)
    return EventClassification("anomalia_estatistica", None, False, False, False, True)
