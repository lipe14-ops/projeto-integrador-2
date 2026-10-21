import { useEffect, useMemo, useRef, useState } from 'react'
import type { EpisodioEnso, Ponto } from '../data/climate'
import { IconDownload } from './Icons'

export interface SerieGrafico {
  nome: string
  cor: string
  pontos: Ponto[]
}

interface Props {
  titulo: string
  subtitulo: string
  unidade: string
  tipo: 'linha' | 'barra'
  series: SerieGrafico[]
  episodios: EpisodioEnso[]
  decimais: number
  arquivo: string
  altura: number
  passoY: number // múltiplo usado para arredondar os rótulos do eixo Y
  dominioZero?: boolean
  className?: string
}

const MARGEM = { esq: 56, dir: 24, topo: 14, base: 34 }
const COR_EL_NINO = '#f6dfd2'
const COR_LA_NINA = '#d5e5f2'

function useLargura<T extends HTMLElement>() {
  const ref = useRef<T>(null)
  const [largura, setLargura] = useState(640)
  useEffect(() => {
    const el = ref.current
    if (!el) return
    const ro = new ResizeObserver(([e]) => setLargura(Math.max(260, Math.round(e.contentRect.width))))
    ro.observe(el)
    return () => ro.disconnect()
  }, [])
  return [ref, largura] as const
}

function dominioY(min: number, max: number, passo: number, zero: boolean): { lo: number; hi: number; ticks: number[] } {
  let lo = zero ? 0 : Math.floor(min / passo) * passo
  let step = Math.max(passo, Math.ceil((max - lo) / 4 / passo) * passo)
  while (lo + step * 4 < max) step += passo
  if (!zero && lo + step * 4 - max > step * 2) lo += step // evita grande espaço vazio no topo
  const hi = lo + step * 4
  return { lo, hi, ticks: [0, 1, 2, 3, 4].map((k) => lo + k * step) }
}

const fmtNum = (v: number, d: number) => v.toLocaleString('pt-BR', { minimumFractionDigits: d, maximumFractionDigits: d })

export function TimeSeriesChart(props: Props) {
  const { titulo, subtitulo, unidade, tipo, series, episodios, decimais, arquivo, altura, passoY, dominioZero, className } = props
  const [wrapRef, largura] = useLargura<HTMLDivElement>()
  const base = series[0].pontos
  const n = base.length
  const [faixa, setFaixa] = useState<[number, number]>([0, n - 1])
  const [b0, b1] = [Math.min(faixa[0], n - 1), Math.min(faixa[1], n - 1)]
  const [hover, setHover] = useState<number | null>(null)

  const iw = largura - MARGEM.esq - MARGEM.dir
  const ih = altura - MARGEM.topo - MARGEM.base
  const visiveis = b1 - b0 + 1
  const mesIni = base[b0].inicio
  const mesFim = base[b1].fim
  const px = (m: number) => MARGEM.esq + ((m - mesIni) / (mesFim - mesIni)) * iw
  const larguraSlot = iw / visiveis

  const { lo, hi, ticks } = useMemo(() => {
    const vals = series.flatMap((s) => s.pontos.slice(b0, b1 + 1).map((p) => p.valor))
    return dominioY(Math.min(...vals), Math.max(...vals), passoY, !!dominioZero)
  }, [series, b0, b1, passoY, dominioZero])
  const py = (v: number) => MARGEM.topo + ih - ((v - lo) / (hi - lo)) * ih

  const nTicksX = Math.max(3, Math.min(12, Math.floor(iw / 92)))
  const ticksX = Array.from(new Set(Array.from({ length: nTicksX }, (_, k) => b0 + Math.round((k * (visiveis - 1)) / (nTicksX - 1)))))

  function baixar() {
    const linhas = [['periodo', ...series.map((s) => `${s.nome} (${unidade})`)].join(',')]
    base.forEach((p, i) => linhas.push([p.rotulo, ...series.map((s) => s.pontos[i].valor.toFixed(decimais + 1))].join(',')))
    const blob = new Blob(['\ufeff' + linhas.join('\n')], { type: 'text/csv;charset=utf-8' })
    const a = document.createElement('a')
    a.href = URL.createObjectURL(blob)
    a.download = `${arquivo}.csv`
    a.click()
    URL.revokeObjectURL(a.href)
  }

  function aoMover(e: React.PointerEvent<SVGRectElement>) {
    const r = e.currentTarget.getBoundingClientRect()
    setHover(b0 + Math.max(0, Math.min(visiveis - 1, Math.floor(((e.clientX - r.left) / r.width) * visiveis))))
  }

  const hp = hover !== null ? base[hover] : null
  const hx = hp ? px((hp.inicio + hp.fim) / 2) : 0
  const ensoHover = hp ? episodios.find((e) => e.inicio < hp.fim && e.fim > hp.inicio) : undefined
  const grupo = Math.max(1, series.length)
  const larguraBarra = Math.max(1, Math.min(14, (larguraSlot * 0.72) / grupo))

  return (
    <article className={`card chart-card ${className ?? ''}`}>
      <header className="chart-card__head">
        <div>
          <h3>{titulo}</h3>
          <p>{subtitulo}</p>
        </div>
        <button type="button" className="btn btn--outline" onClick={baixar}>
          <IconDownload size={18} />
          Baixar
        </button>
      </header>

      <div ref={wrapRef} className="chart-wrap">
        <svg width={largura} height={altura} role="img" aria-label={`${titulo}: gráfico de ${tipo === 'linha' ? 'linha' : 'barras'}`}>
          {episodios.map((e, i) => {
            const a = Math.max(e.inicio, mesIni)
            const b = Math.min(e.fim, mesFim)
            if (b <= a) return null
            return <rect key={i} x={px(a)} y={MARGEM.topo} width={px(b) - px(a)} height={ih} fill={e.tipo === 'el-nino' ? COR_EL_NINO : COR_LA_NINA} />
          })}
          {ticks.map((t) => (
            <g key={t}>
              <line x1={MARGEM.esq} x2={largura - MARGEM.dir} y1={py(t)} y2={py(t)} className="grid-line" />
              <text x={MARGEM.esq - 10} y={py(t)} dy="0.32em" textAnchor="end" className="axis-text">
                {fmtNum(t, 0)}
              </text>
            </g>
          ))}
          <text transform={`translate(14 ${MARGEM.topo + ih / 2}) rotate(-90)`} textAnchor="middle" className="axis-text axis-text--unit">
            {unidade}
          </text>

          {ticksX.map((i, k) => (
            <text
              key={i}
              x={px((base[i].inicio + base[i].fim) / 2)}
              y={altura - 10}
              textAnchor={k === 0 && ticksX.length > 1 ? 'start' : k === ticksX.length - 1 && ticksX.length > 1 ? 'end' : 'middle'}
              dx={k === 0 && ticksX.length > 1 ? -12 : k === ticksX.length - 1 && ticksX.length > 1 ? 12 : 0}
              className="axis-text"
            >
              {base[i].rotulo}
            </text>
          ))}

          {tipo === 'barra'
            ? series.map((s, si) =>
                s.pontos.slice(b0, b1 + 1).map((p) => {
                  const cx = px((p.inicio + p.fim) / 2)
                  const x = cx - (larguraBarra * grupo) / 2 + si * larguraBarra
                  const y = py(p.valor)
                  return <rect key={`${si}-${p.inicio}`} x={x} y={y} width={larguraBarra} height={Math.max(0, MARGEM.topo + ih - y)} fill={s.cor} opacity={hover !== null && base[hover].inicio !== p.inicio ? 0.55 : 1} />
                }),
              )
            : series.map((s, si) => (
                <path
                  key={si}
                  d={s.pontos
                    .slice(b0, b1 + 1)
                    .map((p, k) => `${k ? 'L' : 'M'}${px((p.inicio + p.fim) / 2).toFixed(1)},${py(p.valor).toFixed(1)}`)
                    .join('')}
                  fill="none"
                  stroke={s.cor}
                  strokeWidth={2}
                  strokeLinejoin="round"
                  strokeLinecap="round"
                />
              ))}

          {hp && (
            <g pointerEvents="none">
              <line x1={hx} x2={hx} y1={MARGEM.topo} y2={MARGEM.topo + ih} className="crosshair" />
              {tipo === 'linha' &&
                series.map((s, si) => <circle key={si} cx={hx} cy={py(s.pontos[hover!].valor)} r={4} fill="#fff" stroke={s.cor} strokeWidth={2} />)}
            </g>
          )}
          <rect
            x={MARGEM.esq}
            y={MARGEM.topo}
            width={iw}
            height={ih}
            fill="transparent"
            onPointerMove={aoMover}
            onPointerLeave={() => setHover(null)}
          />
        </svg>

        {hp && (
          <div className="tooltip" style={{ left: Math.min(largura - 170, Math.max(4, hx + 12)), top: MARGEM.topo + 6 }}>
            <strong>{hp.rotulo}</strong>
            {series.map((s) => (
              <span key={s.nome} className="tooltip__row">
                <i style={{ background: s.cor }} />
                {s.nome}: {fmtNum(s.pontos[hover!].valor, decimais)} {unidade}
              </span>
            ))}
            {ensoHover && <span className="tooltip__enso">{ensoHover.tipo === 'el-nino' ? 'El Niño' : 'La Niña'}</span>}
          </div>
        )}
      </div>

      <Brush n={n} faixa={[b0, b1]} onChange={setFaixa} esq={MARGEM.esq} dir={MARGEM.dir} />

      <footer className="legend">
        <ul>
          {series.map((s) => (
            <li key={s.nome}>
              <i className={tipo === 'linha' ? 'swatch swatch--line' : 'swatch swatch--bar'} style={{ background: s.cor }} />
              {s.nome}
            </li>
          ))}
          <li>
            <i className="swatch swatch--bar" style={{ background: COR_EL_NINO }} />
            El Niño
          </li>
          <li>
            <i className="swatch swatch--bar" style={{ background: COR_LA_NINA }} />
            La Niña
          </li>
        </ul>
        <span className="legend__hint">Arraste a barra inferior para ampliar</span>
      </footer>
    </article>
  )
}

interface BrushProps {
  n: number
  faixa: [number, number]
  onChange: (f: [number, number]) => void
  esq: number
  dir: number
}

function Brush({ n, faixa, onChange, esq, dir }: BrushProps) {
  const trilha = useRef<HTMLDivElement>(null)
  const drag = useRef<{ modo: 'l' | 'r' | 'm'; x: number; f: [number, number] } | null>(null)
  const minimo = Math.min(n, 3)
  const [a, b] = faixa

  function mover(e: React.PointerEvent) {
    const d = drag.current
    if (!d || !trilha.current) return
    const largura = trilha.current.getBoundingClientRect().width
    const delta = Math.round(((e.clientX - d.x) / largura) * n)
    let [x0, x1] = d.f
    if (d.modo === 'l') x0 = Math.max(0, Math.min(x1 - minimo + 1, x0 + delta))
    else if (d.modo === 'r') x1 = Math.min(n - 1, Math.max(x0 + minimo - 1, x1 + delta))
    else {
      const w = x1 - x0
      x0 = Math.max(0, Math.min(n - 1 - w, x0 + delta))
      x1 = x0 + w
    }
    onChange([x0, x1])
  }

  function iniciar(modo: 'l' | 'r' | 'm') {
    return (e: React.PointerEvent) => {
      e.stopPropagation()
      drag.current = { modo, x: e.clientX, f: faixa }
      trilha.current?.setPointerCapture(e.pointerId)
    }
  }

  function teclar(modo: 'l' | 'r') {
    return (e: React.KeyboardEvent) => {
      const passo = e.key === 'ArrowLeft' ? -1 : e.key === 'ArrowRight' ? 1 : 0
      if (!passo) return
      e.preventDefault()
      if (modo === 'l') onChange([Math.max(0, Math.min(b - minimo + 1, a + passo)), b])
      else onChange([a, Math.min(n - 1, Math.max(a + minimo - 1, b + passo))])
    }
  }

  return (
    <div className="brush" style={{ marginLeft: esq, marginRight: dir }}>
      <div
        ref={trilha}
        className="brush__track"
        onPointerMove={mover}
        onPointerUp={() => (drag.current = null)}
        onPointerCancel={() => (drag.current = null)}
      >
        <div className="brush__sel" style={{ left: `${(a / n) * 100}%`, width: `${((b - a + 1) / n) * 100}%` }} onPointerDown={iniciar('m')}>
          <span className="brush__handle brush__handle--l" role="slider" tabIndex={0} aria-label="Início do intervalo" aria-valuemin={0} aria-valuemax={n - 1} aria-valuenow={a} onPointerDown={iniciar('l')} onKeyDown={teclar('l')} />
          <span className="brush__handle brush__handle--r" role="slider" tabIndex={0} aria-label="Fim do intervalo" aria-valuemin={0} aria-valuemax={n - 1} aria-valuenow={b} onPointerDown={iniciar('r')} onKeyDown={teclar('r')} />
        </div>
      </div>
    </div>
  )
}
