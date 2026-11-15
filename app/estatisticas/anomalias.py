"""Panorama nacional das anomalias detectadas (reaproveita o snapshot de ``/api/analysis``).

Usa exatamente os mesmos filtros e o mesmo desagrupamento do mapa coroplético
(``AnalysisService.filtered_events``/``filtered_exposure``): um evento é uma
sequência de dias anômalos consecutivos do município; a taxa é eventos por
1.000 dias válidos (município-dia).

Anomalia estatística ≠ evento extremo: a anomalia é um resíduo grande do
modelo (|Z| > 3, o valor fugiu do esperado para aquele dia); o extremo exige,
além disso, um valor raro para o local e a época (percentis da climatologia
local). Por isso as duas contagens são apresentadas separadamente e não somam
o total (há classes intermediárias, como os acumulados de vários dias).
"""

from __future__ import annotations

import pandas as pd

from app.climate_news.analysis.seasonal import MIN_EVENTS
from app.climate_news.analysis.service import VARIABLES, AnalysisService, Filters
from app.estatisticas.calculos import ESTACOES, MESES_DA_ESTACAO, REGIAO_DA_UF, REGIOES, Recorte

INICIO_PONTUADO = 2017
FIM_PONTUADO = 2025
CLASSES = {"todas": "Todas as anomalias válidas", "estatisticas": "Anomalias estatísticas (não extremas)",
           "extremos": "Extremos para o local e a época"}


def _taxa(n: int, dias: float) -> float | None:
    return round(1000 * n / dias, 4) if dias else None


def panorama(service: AnalysisService, r: Recorte, top: int = 10) -> dict:
    service.ensure_loaded()
    inicio = max(r.inicio, INICIO_PONTUADO)
    fim = max(r.fim, INICIO_PONTUADO)
    municipios = service.municipalities[["codigo_ibge", "nome", "uf", "regiao"]].copy()
    municipios["regiao"] = municipios["regiao"].fillna(municipios["uf"].map(REGIAO_DA_UF))
    no_recorte = set(municipios.loc[municipios["regiao"] == r.regiao, "codigo_ibge"]) if r.regiao else None
    regiao_de = municipios.set_index("codigo_ibge")["regiao"]

    variaveis = []
    for var in service.available_variables():
        exposicao = service.filtered_exposure(Filters(var, "todas", INICIO_PONTUADO, FIM_PONTUADO, None, None))
        exposicao = exposicao[exposicao["year"].between(inicio, fim)]
        if r.enso:
            exposicao = exposicao[exposicao["enso_phase"] == r.enso]
        if r.estacao:
            exposicao = exposicao[exposicao["month"].isin(MESES_DA_ESTACAO[r.estacao])]
        if no_recorte is not None:
            exposicao = exposicao[exposicao["codigo_ibge"].isin(no_recorte)]
        dias_total = float(exposicao["days"].sum())
        dias_ano = exposicao.groupby("year")["days"].sum()
        estacao_mes = {m: e for e, ms in MESES_DA_ESTACAO.items() for m in ms}
        dias_estacao = exposicao.assign(est=exposicao["month"].map(estacao_mes)).groupby("est")["days"].sum()
        dias_regiao = exposicao.assign(reg=exposicao["codigo_ibge"].map(regiao_de)).groupby("reg")["days"].sum()
        dias_mun = exposicao.groupby("codigo_ibge")["days"].sum()

        por_classe = {}
        for classe in CLASSES:
            # desagrupa uma vez no período pontuado inteiro (em cache) e recorta depois: o evento
            # fica no ano/estação/fase do seu dia de pico, como no filtro de estação do mapa
            ev = service.filtered_events(Filters(var, classe, INICIO_PONTUADO, FIM_PONTUADO, None, None))
            ev = ev[ev["year"].between(inicio, fim)]
            if r.estacao:
                ev = ev[ev["season"] == r.estacao]
            if r.enso:
                ev = ev[ev["enso_phase"] == r.enso]
            if no_recorte is not None:
                ev = ev[ev["codigo_ibge"].isin(no_recorte)]
            por_classe[classe] = ev

        def contagens(chave: str, valores) -> dict:
            return {c: por_classe[c].groupby(chave).size().reindex(valores, fill_value=0) for c in CLASSES}

        anos = list(range(inicio, fim + 1))
        c_ano = contagens("year", anos)
        c_est = contagens("season", list(ESTACOES))
        ev_reg = {c: por_classe[c].assign(reg=por_classe[c]["codigo_ibge"].map(regiao_de)) for c in CLASSES}
        c_reg = {c: ev_reg[c].groupby("reg").size().reindex(list(REGIOES), fill_value=0) for c in CLASSES}

        n_mun = por_classe["todas"].groupby("codigo_ibge").size()
        ranking = pd.DataFrame({"n": n_mun}).join(dias_mun.rename("dias"), how="inner")
        ranking = ranking[ranking["n"] >= MIN_EVENTS]
        ranking["taxa"] = 1000 * ranking["n"] / ranking["dias"]
        ranking = ranking.sort_values(["taxa", "n"], ascending=False).head(top)
        ranking = ranking.join(municipios.set_index("codigo_ibge")[["nome", "uf", "regiao"]], how="left")

        variaveis.append({
            "variavel": var,
            "rotulo": VARIABLES[var]["label"],
            "familia": VARIABLES[var]["family"],
            "dias_validos": int(dias_total),
            "totais": {c: {"eventos": int(len(por_classe[c])), "taxa": _taxa(len(por_classe[c]), dias_total)}
                       for c in CLASSES},
            "por_ano": [{"ano": a, "dias": int(dias_ano.get(a, 0)),
                         **{c: int(c_ano[c][a]) for c in CLASSES},
                         **{f"taxa_{c}": _taxa(int(c_ano[c][a]), float(dias_ano.get(a, 0))) for c in CLASSES}}
                        for a in anos],
            "por_estacao": [{"estacao": e, "dias": int(dias_estacao.get(e, 0)),
                             **{c: int(c_est[c][e]) for c in CLASSES},
                             **{f"taxa_{c}": _taxa(int(c_est[c][e]), float(dias_estacao.get(e, 0))) for c in CLASSES}}
                            for e in ESTACOES],
            "por_regiao": [{"regiao": g, "dias": int(dias_regiao.get(g, 0)),
                            **{c: int(c_reg[c][g]) for c in CLASSES},
                            **{f"taxa_{c}": _taxa(int(c_reg[c][g]), float(dias_regiao.get(g, 0))) for c in CLASSES}}
                           for g in REGIOES],
            "ranking": [{"codigo_ibge": int(code), "municipio": x.nome, "uf": x.uf, "regiao": x.regiao,
                         "eventos": int(x.n), "dias": int(x.dias), "taxa": round(float(x.taxa), 3)}
                        for code, x in ranking.iterrows()],
        })
    return {
        "recorte": {**r.__dict__, "inicio": inicio, "fim": fim},
        "inicio_pontuado": INICIO_PONTUADO,
        "classes": CLASSES,
        "min_eventos_ranking": MIN_EVENTS,
        "variaveis": variaveis,
        "definicao": "Evento = sequência de dias anômalos consecutivos no município. Taxa = eventos ÷ dias válidos "
        "(município-dia) × 1.000. Anomalia estatística: |Z| do resíduo > 3. Extremo: além disso, valor acima do "
        "percentil da climatologia local. As classes não somam o total (há outras classes, como acumulados).",
        "atualizado_em": {k: v.get("generated_at") for k, v in service.metadata.items() if isinstance(v, dict)},
    }
