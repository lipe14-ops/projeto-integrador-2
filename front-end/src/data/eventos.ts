/**
 * Agrupa anomalias de chuva em "eventos" legíveis para o usuário.
 *
 * O backend registra anomalias de dois detectores (dia isolado — ARIMA + Z-Score —
 * e acumulado de 3/5 dias). Uma mesma tempestade costuma gerar as duas; para o
 * usuário isso é um evento só. Anomalias cujos períodos se tocam (até 2 dias de
 * intervalo) viram um evento, com as notícias de todas elas.
 */
import type { AnomaliaChuva, NoticiaVerificada } from './api'

export interface EventoChuva {
  id: string
  inicio: string // AAAA-MM-DD (início do período de chuva coberto)
  fim: string
  anomalias: AnomaliaChuva[]
  principal: AnomaliaChuva // a de maior volume relativo
  noticias: NoticiaVerificada[]
  faseEnso: AnomaliaChuva['faseEnso']
  oni: number | null
  /** a busca de notícias já foi feita para alguma anomalia do evento */
  pesquisado: boolean
  avaliacao: Rotulo
  impacto: Rotulo | null
}

export interface Rotulo {
  texto: string
  nivel: 'alto' | 'medio' | 'baixo'
  explicacao: string
}

const DIA_MS = 86_400_000
const paraDia = (iso: string) => Date.UTC(+iso.slice(0, 4), +iso.slice(5, 7) - 1, +iso.slice(8, 10)) / DIA_MS
const doDia = (dia: number) => new Date(dia * DIA_MS).toISOString().slice(0, 10)

// Vereditos do Climatologista → linguagem simples
const AVALIACAO_CLIMA: Record<string, Rotulo> = {
  record_accumulation: { texto: 'Maior acumulado da série', nivel: 'alto', explicacao: 'Nenhum período anterior de mesma duração teve tanta chuva neste local.' },
  exceptional_accumulation: { texto: 'Acumulado excepcional', nivel: 'alto', explicacao: 'Acima de 99% dos períodos de mesma duração nos anos anteriores.' },
  exceptional_for_location: { texto: 'Excepcional para o local', nivel: 'alto', explicacao: 'Mais chuva em um dia do que em 99% dos dias chuvosos dos anos anteriores.' },
  very_heavy_for_location: { texto: 'Muito forte para o local', nivel: 'medio', explicacao: 'Entre os 5% dias mais chuvosos dos anos anteriores.' },
  unusual_for_season: { texto: 'Incomum para a época', nivel: 'medio', explicacao: 'Volume comum no ano, mas raro para esta época do ano.' },
  within_normal_variability: { texto: 'Comum no local', nivel: 'baixo', explicacao: 'Volume dentro do habitual; só o salto em relação aos dias anteriores foi incomum.' },
}
// Vereditos do Meteorologista → impacto potencial
const IMPACTO: Record<string, Rotulo> = {
  plausible_extreme_event: { texto: 'Impacto potencial alto', nivel: 'alto', explicacao: '50 mm ou mais em um dia, ou 100 mm ou mais em 5 dias.' },
  plausible_significant_event: { texto: 'Impacto potencial moderado', nivel: 'medio', explicacao: '20 mm ou mais em um dia, ou 50 mm ou mais em 5 dias.' },
  low_meteorological_significance: { texto: 'Impacto potencial baixo', nivel: 'baixo', explicacao: 'Volume baixo para alagamentos ou deslizamentos.' },
}
const ORDEM_NIVEL = { alto: 0, medio: 1, baixo: 2 }

export function rotuloAvaliacao(veredito: string | null): Rotulo {
  return (veredito && AVALIACAO_CLIMA[veredito]) || { texto: 'Em avaliação', nivel: 'baixo', explicacao: 'Sem parecer climatológico.' }
}

export function rotuloImpacto(veredito: string | null): Rotulo | null {
  return (veredito && IMPACTO[veredito]) || null
}

/** Período de chuva coberto por uma anomalia (acumulados olham para trás). */
function periodo(a: AnomaliaChuva): [number, number] {
  const fim = paraDia(a.data)
  return [fim - (a.dias - 1), fim]
}

/** Intensidade relativa usada para escolher a anomalia principal do evento. */
const intensidade = (a: AnomaliaChuva) => a.observadoMm / Math.max(a.dias, 1)

export function agruparEventos(anomalias: AnomaliaChuva[], noticias: NoticiaVerificada[], intervaloMaxDias = 2): EventoChuva[] {
  const ordenadas = [...anomalias].sort((a, b) => periodo(a)[0] - periodo(b)[0])
  const grupos: { inicio: number; fim: number; itens: AnomaliaChuva[] }[] = []
  for (const a of ordenadas) {
    const [ini, fim] = periodo(a)
    const atual = grupos[grupos.length - 1]
    if (atual && ini <= atual.fim + intervaloMaxDias) {
      atual.fim = Math.max(atual.fim, fim)
      atual.itens.push(a)
    } else {
      grupos.push({ inicio: ini, fim, itens: [a] })
    }
  }
  return grupos.map((g) => {
    const datas = new Set(g.itens.map((a) => a.data))
    const principal = g.itens.reduce((m, a) => {
      const na = ORDEM_NIVEL[rotuloAvaliacao(a.avaliacaoClima).nivel]
      const nm = ORDEM_NIVEL[rotuloAvaliacao(m.avaliacaoClima).nivel]
      return na < nm || (na === nm && intensidade(a) > intensidade(m)) ? a : m
    })
    const avaliacoes = g.itens.map((a) => rotuloAvaliacao(a.avaliacaoClima))
    const impactos = g.itens.map((a) => rotuloImpacto(a.avaliacaoTempo)).filter((r): r is Rotulo => r !== null)
    const maisAlto = (lista: Rotulo[]) => [...lista].sort((x, y) => ORDEM_NIVEL[x.nivel] - ORDEM_NIVEL[y.nivel])[0]
    return {
      id: g.itens.map((a) => a.id).join('+'),
      inicio: doDia(g.inicio),
      fim: doDia(g.fim),
      anomalias: g.itens,
      principal,
      noticias: noticias
        .filter((n) => n.datasAnomalia.some((d) => datas.has(d)))
        .sort((x, y) => (x.publicadaEm ?? '').localeCompare(y.publicadaEm ?? '')),
      pesquisado: g.itens.some((a) => a.noticiasPesquisadas),
      faseEnso: principal.faseEnso,
      oni: principal.oni,
      avaliacao: maisAlto(avaliacoes),
      impacto: impactos.length ? maisAlto(impactos) : null,
    }
  })
}

const MESES_CURTOS = ['jan', 'fev', 'mar', 'abr', 'mai', 'jun', 'jul', 'ago', 'set', 'out', 'nov', 'dez']

/** "12 mai 2024", "2–5 mai 2024", "29 abr – 5 mai 2024", "30 dez 2023 – 2 jan 2024". */
export function formatarPeriodo(inicio: string, fim: string): string {
  const [ai, mi, di] = [inicio.slice(0, 4), +inicio.slice(5, 7) - 1, +inicio.slice(8, 10)]
  const [af, mf, df] = [fim.slice(0, 4), +fim.slice(5, 7) - 1, +fim.slice(8, 10)]
  if (inicio === fim) return `${di} ${MESES_CURTOS[mi]} ${ai}`
  if (ai === af && mi === mf) return `${di}–${df} ${MESES_CURTOS[mf]} ${af}`
  if (ai === af) return `${di} ${MESES_CURTOS[mi]} – ${df} ${MESES_CURTOS[mf]} ${af}`
  return `${di} ${MESES_CURTOS[mi]} ${ai} – ${df} ${MESES_CURTOS[mf]} ${af}`
}

const mm = (v: number) => `${Math.round(v).toLocaleString('pt-BR')} mm`

/** Frase em linguagem simples para uma anomalia. */
export function descreverAnomalia(a: AnomaliaChuva): string {
  if (a.detector === 'accumulation_percentile') return `${mm(a.observadoMm)} acumulados em ${a.dias} dias`
  const esperado = a.previstoMm !== null && a.previstoMm >= 0.5 ? ` (esperado: cerca de ${mm(a.previstoMm)})` : ''
  return `${mm(a.observadoMm)} em um dia${esperado}`
}

/** Posição de um dia AAAA-MM-DD dentro de [inicioMes, fimMes) em meses desde jan/2015. */
export function mesDoDia(iso: string, anoInicio: number): number {
  return (+iso.slice(0, 4) - anoInicio) * 12 + (+iso.slice(5, 7) - 1)
}
