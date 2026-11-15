import type { Coropletico, Metrica, StatusValor, ValorMunicipio } from '../../data/analise'
import { ROTULO_PADRAO } from './cores'

export const ROTULO_STATUS: Record<StatusValor, string> = {
  ok: 'com dados',
  insuficiente: 'dados insuficientes',
  sem_eventos: 'sem eventos no período',
  sem_dados: 'sem dados válidos',
}

const num = (v: number, casas: number) => v.toLocaleString('pt-BR', { minimumFractionDigits: casas, maximumFractionDigits: casas })

export function formatarMetrica(v: number, metrica: Metrica): string {
  switch (metrica) {
    case 'participacao':
    case 'outono_inverno':
      return `${num(v, 1)}%`
    case 'contagem':
      return v.toLocaleString('pt-BR', { maximumFractionDigits: 0 })
    case 'concentracao':
      return num(v, 3)
    case 'razao_enso':
      return `${num(v, 2)}×`
    default:
      return num(v, 2)
  }
}

export function descreverValor(v: ValorMunicipio, d: Coropletico): string {
  if (v.status === 'insuficiente') return 'dados insuficientes'
  if (v.status === 'sem_eventos') return 'sem eventos'
  if (d.scale === 'categorical') return v.category ? ROTULO_PADRAO[v.category] : 'sem dados'
  if (v.value === null) return 'sem dados'
  const unidade = ['participacao', 'outono_inverno', 'razao_enso'].includes(d.metric) ? '' : ` ${d.unit}`
  return `${formatarMetrica(v.value, d.metric)}${unidade}`
}

export const pct = (v: number | null | undefined, casas = 1) => (v === null || v === undefined ? '—' : `${num(100 * v, casas)}%`)
export const dec = (v: number | null | undefined, casas = 2) => (v === null || v === undefined ? '—' : num(v, casas))

/** q-valor legível: valores muito pequenos em notação "< 0,001". */
export function formatarQ(q: number | null | undefined): string {
  if (q === null || q === undefined) return '—'
  if (q < 0.001) return '< 0,001'
  return num(q, 3)
}
