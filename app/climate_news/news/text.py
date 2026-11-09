"""Normalização de texto, URLs e vocabulário temático."""

from __future__ import annotations

import re
import unicodedata
from datetime import date, datetime, timedelta
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

TRACKING_PARAMS = re.compile(r"^(utm_|gclid$|fbclid$|mc_|ref$|ref_src$|origin$|xtor$|cmpid$|_ga$)")

# Radicais (texto já normalizado, sem acento e minúsculo)
STRONG_THEME = [
    r"chuva", r"chuvarada", r"temporal", r"temporais", r"tempestade", r"enchente", r"inundac", r"inundad",
    r"alagament", r"alagad", r"deslizament", r"desmoronament", r"granizo", r"vendava", r"transbord",
    r"enxurrada", r"cheia", r"ciclone", r"aguaceiro",
]
WEAK_THEME = [
    r"defesa civil", r"desabrigad", r"desalojad", r"precipitac", r"milimetros", r"\bmm\b", r"alerta",
    r"inmet", r"cemaden", r"metsul", r"meteorolog", r"nivel do rio", r"rio .{0,20}subiu",
]

# Usos de "temporal"/"chuva" que não são meteorológicos (removidos antes da busca de termos)
NON_WEATHER = re.compile(
    r"\b(marco|serie|janela|limite|recorte|escala|linha|lobo|sequencia|ordem|dimensao|questao) temporal\b"
    r"|\bchuva de (gols?|criticas?|elogios?|pedidos?|likes|memes|reclamacoes|ofertas|estrelas|meteoros|dinheiro|votos|ataques)\b"
    r"|\bchuvas? e trovoadas de (gols?|criticas?)\b"
)
# Pistas de matéria retrospectiva / de aniversário de evento passado
RETROSPECTIVE_CUES = re.compile(
    r"\b(\d+|um|uma|dois|duas|tres|quatro|cinco|seis|sete|oito|nove|dez|onze|doze) (anos?|mes|meses|semanas?) (apos|depois|da|desde)\b"
    r"|\bha (\d+|um|uma|dois|duas|tres|seis) (anos?|meses|semanas)\b|\brelembre\b"
    r"|\baniversario\b|\bretrospectiva\b|\bcomo foi a\b|\bo que mudou\b|\bmemoria da\b"
)

MONTHS = {
    "janeiro": 1, "fevereiro": 2, "marco": 3, "abril": 4, "maio": 5, "junho": 6, "julho": 7,
    "agosto": 8, "setembro": 9, "outubro": 10, "novembro": 11, "dezembro": 12,
}
WEEKDAYS = {"segunda": 0, "terca": 1, "quarta": 2, "quinta": 3, "sexta": 4, "sabado": 5, "domingo": 6}

NON_ARTICLE_PATH = re.compile(
    r"(^/?$|/(busca|search|pesquisa|buscar|tag|tags|topico|topicos|assunto|categoria|category|"
    r"autor|author|editoria|secao|page|pagina|feed|rss|index\.html?|home)(/|$|\?))",
    re.IGNORECASE,
)
SEARCH_QUERY_KEYS = {"q", "s", "query", "busca", "search", "termo"}
AGGREGATOR_HOSTS = ("news.google.", "google.com", "bing.com", "msn.com", "yahoo.com", "duckduckgo.com")


def strip_accents(text: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFKD", text) if not unicodedata.combining(c))


def normalize_text(text: str | None) -> str:
    if not text:
        return ""
    text = strip_accents(text).lower()
    return re.sub(r"\s+", " ", text).strip()


def contains_phrase(normalized_text: str, phrase: str) -> bool:
    """Busca ``phrase`` com fronteira de palavra (ambos normalizados)."""
    needle = normalize_text(phrase)
    if not needle:
        return False
    return re.search(rf"(?<![\w-]){re.escape(needle)}(?![\w-])", normalized_text) is not None


# Gentílicos por UF, para confirmar o estado quando o nome do município é ambíguo
DEMONYMS = {
    "AC": ["acreano"], "AL": ["alagoano"], "AP": ["amapaense"], "AM": ["amazonense"], "BA": ["baiano"],
    "CE": ["cearense"], "DF": ["brasiliense", "candango"], "ES": ["capixaba"], "GO": ["goiano"],
    "MA": ["maranhense"], "MT": ["mato-grossense", "matogrossense"], "MS": ["sul-mato-grossense"],
    "MG": ["mineiro"], "PA": ["paraense"], "PB": ["paraibano"], "PR": ["paranaense"], "PE": ["pernambucano"],
    "PI": ["piauiense"], "RJ": ["fluminense", "carioca"], "RN": ["potiguar"], "RS": ["gaucho"],
    "RO": ["rondoniense"], "RR": ["roraimense"], "SC": ["catarinense"], "SP": ["paulista"],
    "SE": ["sergipano"], "TO": ["tocantinense"],
}


def mentions_state(text: str | None, state: str | None, uf: str | None) -> bool:
    """O texto cita o estado: nome ("Goiás"), sigla em maiúsculas ("GO") ou gentílico ("goiano/a/os/as")."""
    if not text:
        return False
    if (state and mentions_place(text, state)) or (uf and mentions_place(text, uf.upper())):
        return True
    normalized = normalize_text(text)
    return any(
        re.search(rf"(?<![\w-]){re.escape(d)}(a|o|as|os)?(?![\w-])".replace("o(a|o", "(o|a"), normalized)
        for d in DEMONYMS.get((uf or "").upper(), [])
    )


def mentions_place(text: str | None, name: str, masked: list[str] | tuple[str, ...] = ()) -> bool:
    """Menção a um nome próprio de lugar, sensível a maiúsculas.

    - Compara sem acentos, mas preserva maiúsculas: "Rio Verde" (cidade) não
      casa com "rio Verde" (curso d'água).
    - Remove antes os nomes em ``masked`` (outros municípios que contêm o nome
      alvo, como "Lucas do Rio Verde"), para que não contem como menção.
    """
    if not text or not name:
        return False
    haystack = re.sub(r"\s+", " ", strip_accents(text))
    for other in sorted(masked, key=len, reverse=True):
        haystack = re.sub(rf"(?<![\w-]){re.escape(strip_accents(other))}(?![\w-])", " ", haystack, flags=re.IGNORECASE)
    return re.search(rf"(?<![\w-]){re.escape(strip_accents(name))}(?![\w-])", haystack) is not None


def theme_terms(normalized_text: str) -> tuple[set[str], set[str]]:
    normalized_text = NON_WEATHER.sub(" ", normalized_text)
    strong = {p for p in STRONG_THEME if re.search(p, normalized_text)}
    weak = {p for p in WEAK_THEME if re.search(p, normalized_text)}
    return strong, weak


def normalize_url(url: str) -> str:
    """URL canônica para deduplicação: host minúsculo, sem www, sem
    fragmento, sem parâmetros de rastreamento, sem barra final."""
    parts = urlsplit(url.strip())
    scheme = "https" if parts.scheme in ("http", "https") else parts.scheme
    host = (parts.hostname or "").lower()
    if host.startswith("www."):
        host = host[4:]
    if parts.port and parts.port not in (80, 443):
        host = f"{host}:{parts.port}"
    query = urlencode(sorted((k, v) for k, v in parse_qsl(parts.query) if not TRACKING_PARAMS.match(k.lower())))
    path = re.sub(r"/+", "/", parts.path or "/")
    if len(path) > 1:
        path = path.rstrip("/")
    return urlunsplit((scheme, host, path, query, ""))


def domain_of(url: str) -> str:
    host = (urlsplit(url).hostname or "").lower()
    return host[4:] if host.startswith("www.") else host


def non_article_reason(url: str) -> str | None:
    """Retorna o motivo se a URL não é de uma matéria específica."""
    parts = urlsplit(url)
    host = (parts.hostname or "").lower()
    if parts.scheme not in ("http", "https") or not host:
        return "url_invalida"
    if any(h in host for h in AGGREGATOR_HOSTS):
        return "url_de_agregador_ou_buscador"
    if NON_ARTICLE_PATH.search(parts.path or "/"):
        return "pagina_inicial_listagem_ou_busca"
    if SEARCH_QUERY_KEYS & {k.lower() for k, _ in parse_qsl(parts.query)}:
        return "pagina_de_busca"
    segments = [s for s in (parts.path or "").split("/") if s]
    if not segments or (len(segments) == 1 and len(segments[0]) < 12 and "-" not in segments[0]):
        return "caminho_curto_demais_para_materia"
    return None


def title_similarity(a: str, b: str) -> float:
    """Similaridade por sobreposição de tokens significativos (0–1)."""
    def tokens(s: str) -> set[str]:
        return {t for t in re.findall(r"[a-z0-9]+", normalize_text(s)) if len(t) > 2}

    ta, tb = tokens(a), tokens(b)
    if not ta or not tb:
        return 0.0
    return len(ta & tb) / min(len(ta), len(tb))


def strip_site_suffix(title: str, site: str | None = None) -> str:
    """Remove sufixos como ' | GZH' ou ' - G1' do título.

    Sem ``site``, remove qualquer sufixo curto; com ``site``, só remove se o
    sufixo corresponder ao nome do veículo.
    """
    title = title.strip()
    match = re.match(r"^(.*\S)\s+[|\-–—]\s+([^|\-–—]{1,40})$", title)
    if match:
        head, tail = match.groups()
        if site is None:
            return head.strip()
        site_n, tail_n = normalize_text(site), normalize_text(tail)
        if site_n and (site_n in tail_n or tail_n in site_n):
            return head.strip()
    return title


def years_mentioned(normalized_text: str) -> set[int]:
    return {int(y) for y in re.findall(r"(?<!\d)(19\d{2}|20\d{2})(?!\d)", normalized_text)}


def estimate_event_date(normalized_text: str, published: date, earliest: date) -> tuple[date | None, str | None]:
    """Estima a data de ocorrência mencionada no texto (título + abertura).

    Considera menções explícitas ("dia 3 de maio", "3 de maio"), dias da
    semana ("nesta segunda-feira", "no sábado") e "ontem"/"hoje". Só aceita
    datas entre ``earliest`` e a data de publicação.
    """
    candidates: list[tuple[date, str]] = []
    for match in re.finditer(r"(?:dia\s+)?(\d{1,2})(?:o)?\s+de\s+(" + "|".join(MONTHS) + r")(?:\s+de\s+(\d{4}))?", normalized_text):
        day, month = int(match.group(1)), MONTHS[match.group(2)]
        year = int(match.group(3)) if match.group(3) else published.year
        if not match.group(3) and month > published.month:
            year -= 1
        try:
            candidates.append((date(year, month, day), match.group(0)))
        except ValueError:
            continue
    for match in re.finditer(r"\b(ontem|hoje|anteontem)\b", normalized_text):
        offset = {"hoje": 0, "ontem": 1, "anteontem": 2}[match.group(1)]
        candidates.append((published - timedelta(days=offset), match.group(0)))
    for match in re.finditer(r"\b(?:[nd]est[ae]|na|no|ultim[ao])\s+(segunda|terca|quarta|quinta|sexta|sabado|domingo)", normalized_text):
        weekday = WEEKDAYS[match.group(1)]
        delta = (published.weekday() - weekday) % 7
        candidates.append((published - timedelta(days=delta), match.group(0)))
    for value, evidence in candidates:
        if earliest <= value <= published:
            return value, evidence
    return None, None


def parse_datetime(value: str | None) -> datetime | None:
    """Interpreta datas ISO 8601 e RFC 2822 (meta tags, JSON-LD, RSS)."""
    if not value:
        return None
    value = value.strip()
    from email.utils import parsedate_to_datetime

    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        pass
    try:
        return parsedate_to_datetime(value)
    except (TypeError, ValueError, IndexError):
        pass
    match = re.match(r"(\d{2})/(\d{2})/(\d{4})(?:\s+(\d{2})[:h](\d{2}))?", value)
    if match:
        d, m, y, hh, mm = match.groups()
        return datetime(int(y), int(m), int(d), int(hh or 0), int(mm or 0))
    return None
