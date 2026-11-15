// Paletas do mapa coroplético (as mesmas do relatório; seguras para daltonismo).
import type { Estacao } from '../../data/seasons'
import type { Coropletico, Escala, Metrica, Padrao, ValorMunicipio } from '../../data/analise'

export const COR_ESTACAO: Record<Estacao, string> = {
  verao: '#e34948',
  outono: '#eda100',
  inverno: '#2a78d6',
  primavera: '#1baf7a',
}
export const COR_SEM_PREDOMINIO = '#b9b8b2'
export const COR_SEM_DADOS = '#ffffff'
const COR_PONTO_SEM_DADOS = '#9a9994'
export const COR_INSUFICIENTE_LINHA = '#8d8c86'
export const COR_INSUFICIENTE_FUNDO = '#e4e3de'

/** Rampa sequencial (azul), do claro ao escuro. */
const SEQUENCIAL = ['#cde2fb', '#9ec5f4', '#6da7ec', '#3987e5', '#256abf', '#184f95', '#0d366b']
const DIV_BAIXO = '#e34948'
const DIV_NEUTRO = '#f0efec'
const DIV_ALTO = '#2a78d6'

/** Valor neutro das métricas divergentes (centro da escala). */
export const NEUTRO: Partial<Record<Metrica, number>> = { participacao: 25, outono_inverno: 50, razao_enso: 1 }

function hexParaRgb(hex: string): [number, number, number] {
  const n = parseInt(hex.slice(1), 16)
  return [(n >> 16) & 255, (n >> 8) & 255, n & 255]
}
function misturar(a: string, b: string, t: number): string {
  const [r1, g1, b1] = hexParaRgb(a)
  const [r2, g2, b2] = hexParaRgb(b)
  const c = (x: number, y: number) => Math.round(x + (y - x) * t).toString(16).padStart(2, '0')
  return `#${c(r1, r2)}${c(g1, g2)}${c(b1, b2)}`
}

export interface Classe {
  cor: string
  rotulo: string
  /** limites [min, max) da classe; null = aberto */
  min: number | null
  max: number | null
}

const fmt = (v: number) => v.toLocaleString('pt-BR', { maximumFractionDigits: 2 })

function rotulos(breaks: number[]): { min: number | null; max: number | null; rotulo: string }[] {
  const out = []
  for (let i = 0; i <= breaks.length; i++) {
    const min = i === 0 ? null : breaks[i - 1]
    const max = i === breaks.length ? null : breaks[i]
    const rotulo = min === null ? `< ${fmt(max!)}` : max === null ? `≥ ${fmt(min)}` : `${fmt(min)} – ${fmt(max)}`
    out.push({ min, max, rotulo })
  }
  return out
}

/**
 * Classes de cor a partir das quebras da API.
 * - sequencial: amostras igualmente espaçadas da rampa azul;
 * - divergente: vermelho abaixo do neutro, azul acima, passos iguais em cada braço,
 *   ficando mais claros (perto de #f0efec) junto ao valor neutro.
 */
export function classesDe(escala: Escala, breaks: number[], neutro?: number, rampa: string[] = SEQUENCIAL): Classe[] {
  if (escala === 'categorical') return []
  if (!breaks.length) return [{ min: null, max: null, rotulo: 'todos os valores', cor: rampa[3] }]
  const faixas = rotulos(breaks)
  if (escala === 'sequential') {
    const k = faixas.length
    return faixas.map((f, i) => ({ ...f, cor: rampa[k === 1 ? 3 : Math.round((i * (rampa.length - 1)) / (k - 1))] }))
  }
  if (escala === 'diverging') {
    const centro = neutro ?? 0
    const abaixo = faixas.filter((f) => f.max !== null && f.max <= centro).length
    const acima = faixas.length - abaixo
    return faixas.map((f, i) => {
      if (i < abaixo) {
        // i = 0 é a mais distante do neutro (cor cheia)
        const passo = (abaixo - i) / abaixo
        return { ...f, cor: misturar(DIV_NEUTRO, DIV_BAIXO, passo) }
      }
      const j = i - abaixo + 1
      return { ...f, cor: misturar(DIV_NEUTRO, DIV_ALTO, j / acima) }
    })
  }
  return []
}

export const ROTULO_PADRAO: Record<Padrao, string> = {
  predominio_verao: 'Predomínio no verão',
  predominio_outono: 'Predomínio no outono',
  predominio_inverno: 'Predomínio no inverno',
  predominio_primavera: 'Predomínio na primavera',
  sem_predominio: 'Sem predomínio significativo',
  insuficiente: 'Dados insuficientes',
}

export function corCategoria(c: Padrao | null): string {
  if (!c || c === 'insuficiente') return COR_INSUFICIENTE_FUNDO
  if (c === 'sem_predominio') return COR_SEM_PREDOMINIO
  return COR_ESTACAO[c.replace('predominio_', '') as Estacao] ?? COR_SEM_PREDOMINIO
}

export function corDoValor(v: number, classes: Classe[]): string {
  for (const c of classes) {
    if ((c.min === null || v >= c.min) && (c.max === null || v < c.max)) return c.cor
  }
  return classes[classes.length - 1]?.cor ?? COR_SEM_DADOS
}

/** Tipo do preenchimento de um município no mapa. */
export type Situacao = 'valor' | 'insuficiente' | 'sem_dados'

export function situacaoDe(v: ValorMunicipio | undefined, dados: Pick<Coropletico, 'scale'>): Situacao {
  if (!v) return 'sem_dados'
  if (v.status === 'insuficiente') return 'insuficiente'
  if (v.status === 'sem_eventos' || v.status === 'sem_dados') return 'sem_dados'
  if (dados.scale === 'categorical') return v.category ? 'valor' : 'sem_dados'
  return v.value === null ? 'sem_dados' : 'valor'
}

const padroes = new Map<string, CanvasPattern | null>()
function padrao(nome: string, fundo: string, desenhar: (ctx: CanvasRenderingContext2D) => void): CanvasPattern | string {
  if (!padroes.has(nome)) {
    const tela = document.createElement('canvas')
    tela.width = 8
    tela.height = 8
    const ctx = tela.getContext('2d')
    if (ctx) {
      ctx.fillStyle = fundo
      ctx.fillRect(0, 0, 8, 8)
      desenhar(ctx)
    }
    padroes.set(nome, ctx ? ctx.createPattern(tela, 'repeat') : null)
  }
  return padroes.get(nome) ?? fundo
}

/** Hachura diagonal cinza (canvas) para "dados insuficientes". */
export function hachuraInsuficiente(): CanvasPattern | string {
  return padrao('insuficiente', COR_INSUFICIENTE_FUNDO, (ctx) => {
    ctx.strokeStyle = COR_INSUFICIENTE_LINHA
    ctx.lineWidth = 1.5
    ctx.beginPath()
    ctx.moveTo(-2, 10); ctx.lineTo(10, -2)
    ctx.moveTo(-2, 2); ctx.lineTo(2, -2)
    ctx.moveTo(6, 10); ctx.lineTo(10, 6)
    ctx.stroke()
  })
}

/** Pontilhado claro para "sem detecção / sem dados" (nunca confundido com zero). */
export function pontilhadoSemDados(): CanvasPattern | string {
  return padrao('sem_dados', COR_SEM_DADOS, (ctx) => {
    ctx.fillStyle = COR_PONTO_SEM_DADOS
    ctx.fillRect(1, 1, 1.6, 1.6)
    ctx.fillRect(5, 5, 1.6, 1.6)
  })
}

/** Fundos CSS equivalentes, para a legenda. */
export const HACHURA_CSS = `repeating-linear-gradient(135deg, ${COR_INSUFICIENTE_FUNDO} 0 3px, ${COR_INSUFICIENTE_LINHA} 3px 4.5px)`
export const PONTILHADO_CSS = `radial-gradient(${COR_PONTO_SEM_DADOS} 0.8px, ${COR_SEM_DADOS} 1px) 0 0 / 4px 4px`
