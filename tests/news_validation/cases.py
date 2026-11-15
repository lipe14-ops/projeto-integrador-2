"""Benchmark rotulado do Fact-Checker — DADOS SINTÉTICOS.

ATENÇÃO: todas as páginas, manchetes, veículos e URLs deste módulo são
**fictícios**, escritos à mão para exercitar a especificação. Não representam
notícias reais nem eventos meteorológicos reais. As datas de anomalia são
apenas parâmetros de teste.

Cada caso traz o rótulo esperado, decidido a partir da ESPECIFICAÇÃO DE
REFERÊNCIA abaixo **antes** de rodar o Fact-Checker. Divergências entre o
sistema e o rótulo NÃO são corrigidas mudando o rótulo: são achados e ficam
documentados (``KNOWN_LIMITATIONS`` em ``test_benchmark.py``) e em ``docs/avaliacao_professor/VALIDACAO_NOTICIAS.md``.

ESPECIFICAÇÃO DE REFERÊNCIA (vínculo anomalia D × notícia)
-----------------------------------------------------------
``verified`` somente se TODOS valem:
  E1. a URL é de uma matéria específica, acessível (HTTP 2xx) e não
      redireciona para página que não é matéria;
  E2. a manchete informada pelo buscador corresponde ao título da página;
  E3. a data de publicação está na própria página e a data local (BRT) está
      em [D−3, D+7];
  E4. a matéria relata a OCORRÊNCIA de precipitação ou de seus impactos
      hidrológicos diretos (chuva, temporal com chuva, alagamento, enchente,
      inundação, enxurrada, deslizamento por chuva, granizo). Previsão,
      alerta, política pública/prevenção, estiagem, calor, frio, vento sem
      chuva e usos figurados ("chuva de gols", "casa cheia") NÃO contam;
  E5. o local do evento é o município-alvo (``relevant``) ou um município
      limítrofe (``regional``). Menção incidental (distância, rota, outro
      município de nome parecido, rio homônimo) não conta; município homônimo
      exige o estado no texto;
  E6. a data do evento, quando o texto a indica, está em [D−2, D+3] (ou no
      período do acumulado com a mesma tolerância) e a matéria não é
      retrospectiva de evento anterior.
``rejected`` quando algum critério falha de forma conclusiva.
``pending_verification`` quando um critério não pode ser avaliado (rede,
timeout, 403/429/5xx, página sem data ou sem título).
Republicação/mesma matéria continua ``verified``, mas deve ser marcada como
duplicata (não é evidência independente).

Categorias: ``positivo`` (deve verificar), ``negativo`` (deve rejeitar),
``pendente`` (deve ficar pendente), ``ambiguo`` (não deve verificar; rejeitar
ou deixar pendente são ambos aceitáveis).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timezone

from app.climate_news.agents.base import MunicipalityContext
from app.climate_news.agents.fact_checker import VerificationContext
from app.climate_news.agents.news_researcher import NewsCandidate
from app.climate_news.news.http import FetchResult
from tests.conftest import article_html

# ---------------------------------------------------------------------------
# Contextos (municípios reais, resolvidos com data_source.resolve_municipality;
# as anomalias são fictícias)
# ---------------------------------------------------------------------------

POA = MunicipalityContext(
    name="Porto Alegre", uf="RS", state="Rio Grande do Sul", region="Sul", codigo_ibge=4314902,
    neighbors=["Canoas", "Viamão", "Alvorada"],
    colliding_names=["Porto Alegre do Norte", "Porto Alegre do Piauí", "Porto Alegre do Tocantins"],
)
RV = MunicipalityContext(
    name="Rio Verde", uf="GO", state="Goiás", region="Centro-Oeste", codigo_ibge=5218805,
    neighbors=["Jataí", "Quirinópolis", "Santa Helena de Goiás"],
    colliding_names=["Carmo do Rio Verde", "Conceição do Rio Verde", "Lucas do Rio Verde",
                     "Rio Verde de Mato Grosso", "São Sebastião do Rio Verde"],
)
BJ = MunicipalityContext(
    name="Bom Jesus", uf="RS", state="Rio Grande do Sul", region="Sul", codigo_ibge=4302303,
    neighbors=["Lages", "Vacaria", "São Joaquim"], homonym=True,
    colliding_names=["Bom Jesus da Lapa", "Bom Jesus de Goiás", "Bom Jesus do Itabapoana", "Bom Jesus do Norte"],
)

# Anomalia fictícia D = 2024-05-01 (quarta-feira): janela de publicação
# 28/04..08/05; faixa do evento 29/04..04/05.
D = date(2024, 5, 1)
CONTEXTS = {
    "poa": VerificationContext(D, date(2024, 4, 28), date(2024, 5, 8), POA),
    "rv": VerificationContext(D, date(2024, 4, 28), date(2024, 5, 8), RV),
    "bj": VerificationContext(D, date(2024, 4, 28), date(2024, 5, 8), BJ),
    # anomalia de acumulado em 04/05 cobrindo o período 27/04..05/05
    "poa_acc": VerificationContext(
        date(2024, 5, 4), date(2024, 5, 1), date(2024, 5, 11), POA,
        event_start=date(2024, 4, 27), event_end=date(2024, 5, 5),
    ),
}

# ---------------------------------------------------------------------------
# HTML sintético
# ---------------------------------------------------------------------------


def html_jsonld_date(title: str, body: str, published: str, site: str = "Correio Fictício") -> str:
    paragraphs = "".join(f"<p>{p}</p>" for p in body.split("\n"))
    return (
        f'<html><head><title>{title}</title><meta property="og:site_name" content="{site}">'
        f'<script type="application/ld+json">{{"@type": "NewsArticle", "headline": "{title}", '
        f'"datePublished": "{published}", "publisher": {{"name": "{site}"}}}}</script></head>'
        f"<body><article><h1>{title}</h1>{paragraphs}</article></body></html>"
    )


def html_time_tag(title: str, body: str, published: str) -> str:
    paragraphs = "".join(f"<p>{p}</p>" for p in body.split("\n"))
    return (
        f"<html><head><title>{title}</title></head><body><article><h1>{title}</h1>"
        f'<time datetime="{published}">publicado</time>{paragraphs}</article></body></html>'
    )


def html_visible_date(title: str, body: str, visible: str) -> str:
    paragraphs = "".join(f"<p>{p}</p>" for p in body.split("\n"))
    return (
        f"<html><head><title>{title}</title></head><body><article><h1>{title}</h1>"
        f'<span class="data-publicacao">{visible}</span>{paragraphs}</article></body></html>'
    )


def html_without_title(body: str) -> str:
    return f"<html><head></head><body><div><p>{body}</p></div></body></html>"


class BenchmarkHttpClient:
    """HTTP falso: url -> (status, html[, url_final]); status None = falha de rede/timeout."""

    def __init__(self, pages: dict):
        self.pages = pages
        self.calls: list[str] = []

    def get(self, url: str, **_) -> FetchResult:
        self.calls.append(url)
        entry = self.pages.get(url, (404, "not found"))
        status, content = entry[0], entry[1]
        final_url = entry[2] if len(entry) > 2 else url
        if status is None:
            return FetchResult(url, None, None, None, "ReadTimeout: timed out", 10.0, 3)
        return FetchResult(url, final_url, status, content, None, 0.01, 1)


# ---------------------------------------------------------------------------
# Casos
# ---------------------------------------------------------------------------


@dataclass
class Case:
    id: str
    category: str  # positivo | negativo | pendente | ambiguo
    description: str
    url: str
    headline: str
    pages: dict
    ctx: str = "poa"
    claimed: datetime | None = datetime(2024, 5, 2, 12, tzinfo=timezone.utc)
    expected_relevance: str | None = None  # relevant | regional (só positivos)
    expected_duplicate: str | None = None  # same_article | republication
    preload: list[tuple[str, str]] = field(default_factory=list)  # (url, manchete) verificados antes

    @property
    def expected(self) -> str:
        return {"positivo": "verified", "negativo": "rejected", "pendente": "pending_verification",
                "ambiguo": "not_verified"}[self.category]

    @property
    def acceptable(self) -> set[str]:
        if self.category == "ambiguo":
            return {"rejected", "pending_verification"}
        return {self.expected}

    @property
    def expected_positive(self) -> bool:
        return self.category == "positivo"

    def candidate(self, url: str | None = None, headline: str | None = None) -> NewsCandidate:
        return NewsCandidate(
            url or self.url, headline or self.headline, None, self.claimed, "q", "benchmark-sintetico",
            "https://news.google.com/rss/articles/sintetico",
        )


def _u(host: str, slug: str, day: str = "2024/05/02") -> str:
    return f"https://{host}/noticia/{day}/{slug}.html"


G1 = "g1.globo.com"
GZH = "gauchazh.clicrbs.com.br"
LOCAL = "jornaldobairro-ficticio.com.br"
REG = "folharegional-ficticia.com.br"
GO = "diariodosudoeste-ficticio.com.br"

T = "2024-05-02T10:00:00-03:00"


def _case(id, category, description, title, body, *, host=G1, slug=None, published=T, site="G1",
          ctx="poa", headline=None, html=None, **kwargs) -> Case:
    url = kwargs.pop("url", None) or _u(host, slug or id.lower())
    page = html if html is not None else article_html(title, body, published=published, site=site)
    return Case(id, category, description, url, headline or title, {url: (200, page)}, ctx=ctx, **kwargs)


POA_BODY = (
    "A chuva intensa desta quarta-feira provocou alagamentos em vários bairros de Porto Alegre, segundo a Defesa Civil.\n"
    "O temporal derrubou árvores e o nível do Guaíba subiu, com risco de enchente nas áreas ribeirinhas da capital."
)

CASES: list[Case] = []
add = CASES.append

# ---- POSITIVOS -------------------------------------------------------------
add(_case("P01", "positivo", "matéria típica: chuva alaga bairros do município-alvo, publicada D+1",
          "Chuva alaga bairros de Porto Alegre e Defesa Civil emite alerta", POA_BODY,
          expected_relevance="relevant"))
add(_case("P02", "positivo", "evento em município limítrofe (Canoas) → regional",
          "Temporal causa alagamentos em Canoas",
          "A chuva forte desta quarta-feira provocou alagamentos e deslizamentos em Canoas, na Região Metropolitana.",
          expected_relevance="regional"))
add(_case("P03", "positivo", "fonte oficial (Defesa Civil, .gov.br)",
          "Defesa Civil registra alagamentos em Porto Alegre após chuva forte",
          "A chuva forte registrada nesta quarta-feira causou alagamentos em ruas de Porto Alegre, informou a Defesa Civil estadual.",
          host="defesacivil.rs.gov.br", site="Defesa Civil RS", published="2024-05-01T18:00:00-03:00",
          expected_relevance="relevant"))
add(_case("P04", "positivo", "veículo regional pequeno, data só em elemento visível (confiabilidade baixa)",
          "Temporal deixa ruas alagadas no bairro Sarandi, em Porto Alegre", "",
          host=LOCAL, expected_relevance="relevant",
          html=html_visible_date(
              "Temporal deixa ruas alagadas no bairro Sarandi, em Porto Alegre",
              "Moradores do Sarandi, na zona norte de Porto Alegre, enfrentaram ruas alagadas depois do temporal desta quinta-feira.",
              "02/05/2024 - 10h20")))
add(_case("P05", "positivo", "data de publicação só no JSON-LD",
          "Enxurrada arrasta carros em rua de Porto Alegre", "",
          host=REG, expected_relevance="relevant",
          html=html_jsonld_date(
              "Enxurrada arrasta carros em rua de Porto Alegre",
              "A enxurrada provocada pela chuva forte desta quinta-feira arrastou carros em uma rua do bairro Partenon, em Porto Alegre.",
              "2024-05-02T09:30:00-03:00")))
add(_case("P06", "positivo", "data de publicação só em <time datetime>",
          "Chuva provoca deslizamento de terra em encosta de Porto Alegre", "",
          host=REG, expected_relevance="relevant",
          html=html_time_tag(
              "Chuva provoca deslizamento de terra em encosta de Porto Alegre",
              "Um deslizamento de terra atingiu casas no Morro da Cruz, em Porto Alegre, após a chuva desta quinta-feira.",
              "2024-05-02T08:00:00-03:00")))
add(_case("P07", "positivo", "anomalia de acumulado: evento datado dentro do período acumulado",
          "Temporal alaga bairros de Porto Alegre",
          "O temporal de 29 de abril provocou alagamentos e enchente em Porto Alegre, segundo a Defesa Civil.",
          ctx="poa_acc", claimed=None, expected_relevance="relevant"))
add(_case("P08", "positivo", "publicada antes da anomalia, dentro da janela (D−1)",
          "Chuva forte atinge Porto Alegre nesta terça-feira",
          "A chuva forte desta terça-feira provocou pontos de alagamento em avenidas de Porto Alegre, segundo a EPTC.",
          published="2024-04-30T19:00:00-03:00", claimed=datetime(2024, 4, 30, 22, tzinfo=timezone.utc),
          expected_relevance="relevant"))
add(_case("P09", "positivo", "publicada em D+6 relatando o evento datado de D",
          "Moradores de Porto Alegre limpam casas atingidas pela enchente",
          "A enchente provocada pela chuva de 1º de maio deixou lama em casas da zona norte de Porto Alegre, e moradores seguem na limpeza.",
          published="2024-05-07T11:00:00-03:00", claimed=datetime(2024, 5, 7, 14, tzinfo=timezone.utc),
          expected_relevance="relevant"))
add(_case("P10", "positivo", "outro município (Rio Verde/GO) com nomes que colidem mascarados",
          "Chuva forte causa alagamentos em Rio Verde",
          "O temporal desta quarta-feira provocou alagamentos em Rio Verde, no sudoeste goiano, segundo a Defesa Civil.",
          host=GO, site="Diário do Sudoeste", ctx="rv", expected_relevance="relevant"))
add(_case("P11", "positivo", "município homônimo com o estado no texto (Bom Jesus/RS, 'Serra gaúcha')",
          "Chuva causa alagamentos e queda de barreira em Bom Jesus",
          "A chuva forte desta quarta-feira provocou alagamentos e queda de barreira em Bom Jesus, nos Campos de Cima da Serra gaúcha.",
          host=REG, site="Folha Regional", ctx="bj", expected_relevance="relevant"))
add(_case("P12", "positivo", "manchete truncada pelo buscador ('...')",
          "Chuva alaga bairros de Porto Alegre e Defesa Civil emite alerta para áreas ribeirinhas do Guaíba",
          POA_BODY, headline="Chuva alaga bairros de Porto Alegre e Defesa Civil emite alerta para...",
          expected_relevance="relevant"))
add(_case("P13", "positivo", "URL com parâmetros de rastreamento (utm_*)",
          "Temporal derruba árvores e alaga ruas em Porto Alegre", POA_BODY,
          url=_u(G1, "p13") + "?utm_source=twitter&utm_medium=social", expected_relevance="relevant"))
add(_case("P14", "positivo", "ciclone extratropical com chuva forte",
          "Ciclone extratropical traz chuva forte e alagamentos a Porto Alegre",
          "O ciclone extratropical provocou chuva forte nesta quarta-feira e alagamentos em diversos bairros de Porto Alegre.",
          expected_relevance="relevant"))
add(_case("P15", "positivo", "manchete sem termo de chuva; corpo relata evento datado com vários termos",
          "Defesa Civil retira 200 famílias de áreas de risco em Porto Alegre nesta quinta-feira",
          "A chuva forte provocou alagamentos, um deslizamento no Morro Santana e risco de enchente em Porto Alegre.\n"
          "Desde a madrugada, as equipes atendem moradores atingidos pela inundação nas ilhas do Guaíba.",
          expected_relevance="relevant"))
add(_case("P16", "positivo", "fuso horário: 2024-05-09T01:00Z = 08/05 22h BRT (último dia da janela)",
          "Chuva continua a causar alagamentos em Porto Alegre",
          "A chuva persistente segue provocando alagamentos em vias da zona sul de Porto Alegre, segundo a prefeitura.",
          published="2024-05-09T01:00:00Z", claimed=datetime(2024, 5, 9, 1, tzinfo=timezone.utc),
          expected_relevance="relevant"))
add(_case("P17", "positivo", "número de 4 dígitos que parece ano na manchete ('2000 casas')",
          "Temporal danifica mais de 2000 casas em Porto Alegre",
          "O temporal desta quarta-feira, com chuva forte e granizo, danificou telhados de mais de 2000 casas em Porto Alegre.",
          expected_relevance="relevant"))
add(_case("P18", "positivo", "mesmo evento, veículo A (não é duplicata de B)",
          "Chuva intensa provoca alagamentos na zona norte de Porto Alegre",
          "A chuva intensa desta quarta-feira provocou alagamentos na zona norte de Porto Alegre, segundo a Defesa Civil.",
          expected_relevance="relevant"))
add(_case("P19", "positivo", "mesmo evento, veículo B, manchete diferente → independente (não duplicata)",
          "Enchente atinge moradores do bairro Humaitá, em Porto Alegre",
          "A enchente causada pela chuva desta quarta-feira atingiu moradores do bairro Humaitá, em Porto Alegre.",
          host=GZH, site="GZH", expected_relevance="relevant", preload=[(CASES[-1].url, CASES[-1].headline)]))
_P19_PAGES = dict(CASES[-2].pages)
CASES[-1].pages.update(_P19_PAGES)

_AB_URL = _u("agenciabrasil.ebc.com.br", "chuva-provoca-alagamentos-poa")
_AB_TITLE = "Chuva provoca alagamentos e deixa desalojados em Porto Alegre"
_AB_BODY = "A chuva forte desta quarta-feira provocou alagamentos e deixou famílias desalojadas em Porto Alegre, segundo a Defesa Civil."
add(_case("P20", "positivo", "cópia sindicada (mesma manchete e data em outro veículo) → verified + republication",
          _AB_TITLE, _AB_BODY, host=REG, site="Folha Regional", slug="copia-agencia",
          expected_relevance="relevant", expected_duplicate="republication", preload=[(_AB_URL, _AB_TITLE)]))
CASES[-1].pages[_AB_URL] = (200, article_html(_AB_TITLE, _AB_BODY, published=T, site="Agência Brasil"))

_CAN_URL = _u(G1, "chuva-forte-poa-canonica")
_CAN_TITLE = "Chuva forte deixa ruas alagadas em Porto Alegre"
_CAN_PAGE = article_html(_CAN_TITLE, POA_BODY, published=T, canonical=_CAN_URL)
_AMP_URL = _CAN_URL.replace("/noticia/", "/amp/noticia/")
add(Case("P21", "positivo", "versão AMP da mesma matéria (mesmo canonical) → verified + same_article",
         _AMP_URL, _CAN_TITLE, {_CAN_URL: (200, _CAN_PAGE), _AMP_URL: (200, _CAN_PAGE)},
         expected_relevance="relevant", expected_duplicate="same_article", preload=[(_CAN_URL, _CAN_TITLE)]))
add(_case("P22", "positivo", "chuva de granizo (precipitação)",
          "Chuva de granizo atinge bairros de Porto Alegre",
          "A chuva de granizo desta quarta-feira danificou carros e telhados em bairros de Porto Alegre, informou a Defesa Civil.",
          expected_relevance="relevant"))
add(_case("P23", "positivo", "manchete em CAIXA ALTA; corpo cita o município normalmente",
          "CHUVA FORTE ALAGA RUAS DE PORTO ALEGRE",
          "A chuva forte desta quarta-feira alagou ruas do centro de Porto Alegre e interrompeu o trânsito em avenidas.",
          host=LOCAL, site="Jornal do Bairro", expected_relevance="relevant"))

# ---- NEGATIVOS -------------------------------------------------------------
add(Case("N01", "negativo", "HTTP 404 (página inexistente)", _u(G1, "n01"),
         "Chuva alaga bairros de Porto Alegre", {}))
add(Case("N02", "negativo", "HTTP 410 (removida)", _u(G1, "n02"),
         "Chuva alaga bairros de Porto Alegre", {_u(G1, "n02"): (410, "gone")}))
add(Case("N03", "negativo", "página inicial do veículo", "https://g1.globo.com/",
         "Chuva alaga bairros de Porto Alegre", {}))
add(Case("N04", "negativo", "link do agregador (Google News), não a matéria",
         "https://news.google.com/rss/articles/CBMiabc123", "Chuva alaga bairros de Porto Alegre", {}))
add(Case("N05", "negativo", "página de tag/listagem", "https://gauchazh.clicrbs.com.br/tag/chuva",
         "Chuva alaga bairros de Porto Alegre", {}))
add(Case("N06", "negativo", "página de busca do veículo", "https://www.folharegional-ficticia.com.br/?s=chuva+porto+alegre",
         "Chuva alaga bairros de Porto Alegre", {}))
_N07 = _u(REG, "n07-materia-removida")
add(Case("N07", "negativo", "URL de matéria que redireciona para a página inicial",
         _N07, "Chuva alaga bairros de Porto Alegre",
         {_N07: (200, article_html("Folha Regional — notícias", "Capa do portal."), "https://folharegional-ficticia.com.br/")}))
add(_case("N08", "negativo", "manchete alegada não corresponde ao conteúdo da página",
          "Prefeitura anuncia nova linha de ônibus no centro",
          "Texto sobre transporte público em Porto Alegre, com novos horários a partir de segunda.",
          headline="Chuva alaga bairros de Porto Alegre e Defesa Civil emite alerta"))
add(_case("N09", "negativo", "cidade certa, data errada (publicada 20/06, fora da janela)",
          "Chuva alaga bairros de Porto Alegre e Defesa Civil emite alerta", POA_BODY,
          published="2024-06-20T09:00:00-03:00", claimed=datetime(2024, 6, 20, tzinfo=timezone.utc)))
add(_case("N10", "negativo", "cidade certa, publicada antes da janela (26/04)",
          "Temporal provoca alagamentos em Porto Alegre", POA_BODY,
          published="2024-04-26T09:00:00-03:00", claimed=datetime(2024, 4, 26, tzinfo=timezone.utc)))
add(_case("N11", "negativo", "fuso horário: 2024-04-28T02:00Z = 27/04 23h BRT (fora da janela)",
          "Chuva causa alagamentos em Porto Alegre",
          "A chuva causou alagamentos em ruas de Porto Alegre e a Defesa Civil monitora o nível do Guaíba.",
          published="2024-04-28T02:00:00Z", claimed=datetime(2024, 4, 28, 2, tzinfo=timezone.utc)))
add(_case("N12", "negativo", "buscador alega 02/05/2024, página diz 02/05/2023 (ano anterior)",
          "Chuva alaga bairros de Porto Alegre e Defesa Civil emite alerta", POA_BODY,
          published="2023-05-02T10:00:00-03:00"))
add(_case("N13", "negativo", "publicada na janela, mas relata outro evento (08/05, fora de 29/04..04/05)",
          "Temporal desta quarta-feira derruba árvores em Porto Alegre",
          "O temporal desta quarta-feira (8) derrubou árvores e causou alagamentos em Porto Alegre.",
          published="2024-05-08T20:00:00-03:00", claimed=datetime(2024, 5, 8, 23, tzinfo=timezone.utc)))
add(_case("N14", "negativo", "outro município sem relação (Goiânia)",
          "Chuva alaga bairros de Goiânia e Defesa Civil emite alerta",
          POA_BODY.replace("Porto Alegre", "Goiânia").replace("Guaíba", "Meia Ponte")))
add(_case("N15", "negativo", "homônimo em outra UF: Bom Jesus (PI) para anomalia de Bom Jesus/RS",
          "Chuva alaga ruas de Bom Jesus, no sul do Piauí",
          "A chuva forte desta quarta-feira alagou ruas e casas em Bom Jesus, no sul do Piauí, segundo a prefeitura local.",
          host=REG, site="Folha Regional", ctx="bj"))
add(_case("N16", "negativo", "município de nome que contém o alvo (Porto Alegre do Norte/MT)",
          "Temporal provoca alagamentos em Porto Alegre do Norte",
          "A chuva forte desta quarta-feira causou alagamentos em Porto Alegre do Norte, no nordeste de Mato Grosso.",
          host=REG, site="Folha Regional"))
add(_case("N17", "negativo", "município de nome que contém o alvo (Lucas do Rio Verde/MT)",
          "Fortes chuvas causam inundações em Lucas do Rio Verde",
          "A chuva forte desta quarta-feira provocou alagamentos e inundações em Lucas do Rio Verde, no norte de Mato Grosso.",
          host=GO, site="Diário do Sudoeste", ctx="rv"))
add(_case("N18", "negativo", "rio homônimo ('rio Verde') em outra cidade",
          "Temporal causa alagamentos na região de Sorocaba",
          "A chuva forte fez o rio Verde transbordar e causou alagamentos e enchente em bairros de Sorocaba.",
          host=REG, site="Folha Regional", ctx="rv"))
add(_case("N19", "negativo", "estiagem com 'chuva' na manchete ('falta de chuva') — variável/tema oposto",
          "Falta de chuva castiga lavouras de soja em Rio Verde",
          "A estiagem prolongada preocupa produtores de Rio Verde, no sudoeste goiano: a região está há 40 dias sem chuva.\n"
          "Segundo o sindicato rural, a seca já reduziu a produtividade das lavouras de soja do município.",
          host=GO, site="Diário do Sudoeste", ctx="rv"))
add(_case("N20", "negativo", "estiagem sem termo de chuva na manchete",
          "Seca prolongada afeta lavouras em Rio Verde",
          "A seca prolongada e a falta de chuva afetam as lavouras de Rio Verde, no sudoeste goiano, segundo produtores.",
          host=GO, site="Diário do Sudoeste", ctx="rv"))
add(_case("N21", "negativo", "onda de calor; 'chuva' aparece só como previsão de retorno",
          "Onda de calor eleva temperatura em Porto Alegre; chuva só deve voltar na próxima semana",
          "Porto Alegre registrou 35 °C nesta quarta-feira, em meio a uma onda de calor que atinge o Rio Grande do Sul.\n"
          "Segundo a meteorologia, o tempo seco deve continuar e a chuva só retorna na próxima semana."))
add(_case("N22", "negativo", "onda de calor sem termo de chuva (outra variável)",
          "Porto Alegre registra 37 °C, a maior temperatura do ano",
          "A capital gaúcha teve nesta quarta-feira a tarde mais quente do ano, com 37 °C registrados em Porto Alegre."))
add(_case("N23", "negativo", "frio/geada (outra variável)",
          "Frente fria derruba temperaturas e traz geada a Porto Alegre",
          "O tempo seco e a massa de ar polar trouxeram geada à região de Porto Alegre nesta quarta-feira."))
add(_case("N24", "negativo", "incêndio (fora do tema)",
          "Incêndio atinge depósito na zona norte de Porto Alegre",
          "O Corpo de Bombeiros controlou um incêndio em um depósito na zona norte de Porto Alegre nesta quarta-feira."))
add(_case("N25", "negativo", "previsão (não relata ocorrência)",
          "Previsão indica chuva forte em Porto Alegre no fim de semana",
          "A meteorologia prevê chuva forte para Porto Alegre no sábado e no domingo, com acumulados que podem passar de 50 milímetros.",
          published="2024-05-01T08:00:00-03:00"))
add(_case("N26", "negativo", "alerta meteorológico (não relata ocorrência)",
          "Inmet emite alerta de tempestade para Porto Alegre",
          "O Inmet emitiu alerta amarelo de tempestade para Porto Alegre, válido até a noite de quinta-feira, com risco de ventos e chuva.",
          published="2024-05-01T08:00:00-03:00"))
add(_case("N27", "negativo", "política pública/prevenção com 'enchentes' na manchete",
          "Câmara de Porto Alegre aprova projeto de prevenção a enchentes",
          "Os vereadores de Porto Alegre aprovaram projeto que cria um fundo municipal para obras de drenagem e prevenção."))
add(_case("N28", "negativo", "uso figurado de 'cheia' ('casa cheia')",
          "Grêmio espera casa cheia na Arena em Porto Alegre nesta quarta-feira",
          "O Grêmio espera mais de 50 mil torcedores na Arena, em Porto Alegre, para o jogo decisivo desta quarta-feira."))
add(_case("N29", "negativo", "uso figurado de 'chuva' ('chuva de gols')",
          "Inter vence com chuva de gols no Beira-Rio, em Porto Alegre",
          "O Internacional goleou por 5 a 1 no estádio Beira-Rio, em Porto Alegre, nesta quarta-feira."))
add(_case("N30", "negativo", "'marco temporal' (não meteorológico)",
          "Indígenas protestam contra o Marco Temporal no centro de Porto Alegre",
          "Lideranças protestaram contra o marco temporal em Porto Alegre nesta quarta-feira, em frente ao Palácio Piratini."))
add(_case("N31", "negativo", "prevenção/serviço, chuva só como contexto",
          "Secretaria de Obras limpa calha de macrodrenagem em Porto Alegre",
          "O serviço previne alagamentos e enchentes em dias de chuva, informou a prefeitura de Porto Alegre."))
add(_case("N32", "negativo", "retrospectiva de aniversário ('um ano após')",
          "Porto Alegre: como a fauna foi afetada pela enchente",
          "Um ano após a enchente que atingiu Porto Alegre, pesquisadores avaliam os efeitos da cheia sobre a fauna."))
add(_case("N33", "negativo", "retrospectiva de evento histórico (ano na manchete)",
          "Chuva em Porto Alegre: como foi a histórica enchente de 1941",
          "Relembre a enchente de 1941 em Porto Alegre, quando a chuva e a cheia do Guaíba inundaram o centro."))
add(_case("N34", "negativo", "menção incidental ao alvo (distância); evento em Pelotas",
          "Chuva alaga ruas de Pelotas, a 260 km de Porto Alegre",
          "A chuva forte desta quarta-feira alagou ruas do centro de Pelotas, no sul do estado, segundo a Defesa Civil local."))
add(_case("N35", "negativo", "menção incidental a vizinho (rota para Canoas); evento em Caxias do Sul",
          "Temporal causa estragos em Caxias do Sul",
          "O temporal desta quarta-feira destelhou casas e alagou ruas em Caxias do Sul, na Serra.\n"
          "Na BR-116, motoristas que seguiam em direção a Canoas enfrentaram lentidão por causa da chuva."))

# ---- PENDENTES -------------------------------------------------------------
_TIMEOUT = _u(G1, "pd01")
add(Case("PD01", "pendente", "timeout/falha de rede", _TIMEOUT, "Chuva alaga bairros de Porto Alegre", {_TIMEOUT: (None, None)}))
for _id, _status, _desc in (("PD02", 503, "HTTP 503 (servidor indisponível)"),
                            ("PD03", 403, "HTTP 403 (bloqueio/paywall)"),
                            ("PD04", 429, "HTTP 429 (limite de requisições)")):
    _url = _u(G1, _id.lower())
    add(Case(_id, "pendente", _desc, _url, "Chuva alaga bairros de Porto Alegre", {_url: (_status, "erro")}))
add(_case("PD05", "pendente", "página sem data de publicação",
          "Chuva alaga bairros de Porto Alegre e Defesa Civil emite alerta", POA_BODY, published=None))
add(_case("PD06", "pendente", "página sem título identificável", "", "",
          html=html_without_title("A chuva intensa desta quarta-feira provocou alagamentos em vários bairros de Porto Alegre."),
          headline="Chuva alaga bairros de Porto Alegre"))

# ---- AMBÍGUOS (não deve verificar) ------------------------------------------
add(_case("A01", "ambiguo", "matéria estadual sem citar o município nem vizinhos",
          "Chuvas causam estragos em várias cidades do Rio Grande do Sul",
          "A chuva forte desta quarta-feira provocou alagamentos e deslizamentos em diversas cidades gaúchas, segundo a Defesa Civil estadual."))
add(_case("A02", "ambiguo", "homônimo sem o estado no texto (qual Bom Jesus?)",
          "Chuva alaga ruas de Bom Jesus",
          "A chuva forte desta quarta-feira alagou ruas e casas em Bom Jesus, segundo a prefeitura.",
          host=REG, site="Folha Regional", ctx="bj"))
add(_case("A03", "ambiguo", "vendaval sem chuva (vento é outra variável)",
          "Vendaval derruba árvores e destelha casas em Porto Alegre",
          "Rajadas de vento de até 90 km/h derrubaram árvores e destelharam casas em Porto Alegre nesta quarta-feira, sem registro de chuva."))

CASES_BY_ID = {c.id: c for c in CASES}
assert len(CASES_BY_ID) == len(CASES), "ids duplicados no benchmark"
