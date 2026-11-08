import { useMemo } from 'react'
import {
  Bar,
  CartesianGrid,
  ComposedChart,
  Brush,
  Line,
  ReferenceArea,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
  type TooltipContentProps,
} from 'recharts'
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
  passoY: number
  dominioZero?: boolean
  className?: string
}

interface LinhaGrafico {
  rotulo: string
  inicio: number
  fim: number
  episodio?: string
  [key: string]: string | number | undefined
}

const COR_EL_NINO = '#f6dfd2'
const COR_LA_NINA = '#d5e5f2'
const fmtNum = (v: number, d: number) => v.toLocaleString('pt-BR', { minimumFractionDigits: d, maximumFractionDigits: d })

function TooltipClima({ active, payload, label, unidade, decimais, series }: TooltipContentProps & { unidade: string; decimais: number; series: SerieGrafico[] }) {
  if (!active || !payload?.length) return null
  const dados = payload[0]?.payload as LinhaGrafico | undefined
  return (
    <div className="tooltip chart-tooltip">
      <strong>{label}</strong>
      {series.map((s) => (
        <span key={s.nome} className="tooltip__row">
          <i style={{ background: s.cor }} />
          {s.nome}: {fmtNum(Number(dados?.[s.nome] ?? 0), decimais)} {unidade}
        </span>
      ))}
      {dados?.episodio && <span className="tooltip__enso">{dados.episodio}</span>}
    </div>
  )
}

export function TimeSeriesChart({ titulo, subtitulo, unidade, tipo, series, episodios, decimais, arquivo, altura, passoY, dominioZero, className }: Props) {
  const dados = useMemo<LinhaGrafico[]>(() => {
    const base = series[0]?.pontos ?? []
    return base.map((p, i) => {
      const episodio = episodios.find((e) => e.inicio < p.fim && e.fim > p.inicio)
      const linha: LinhaGrafico = {
        rotulo: p.rotulo,
        inicio: p.inicio,
        fim: p.fim,
        episodio: episodio ? (episodio.tipo === 'el-nino' ? 'El Niño' : 'La Niña') : undefined,
      }
      series.forEach((s) => { linha[s.nome] = s.pontos[i]?.valor ?? 0 })
      return linha
    })
  }, [series, episodios])

  const areas = useMemo(() => episodios.flatMap((ep, i) => {
    const atingidos = dados.filter((p) => ep.inicio < p.fim && ep.fim > p.inicio)
    if (!atingidos.length) return []
    return [{ x1: atingidos[0].rotulo, x2: atingidos[atingidos.length - 1].rotulo, fill: ep.tipo === 'el-nino' ? COR_EL_NINO : COR_LA_NINA, key: i }]
  }), [episodios, dados])

  function baixar() {
    const linhas = [['periodo', ...series.map((s) => `${s.nome} (${unidade})`)].join(',')]
    dados.forEach((p) => linhas.push([p.rotulo, ...series.map((s) => Number(p[s.nome] ?? 0).toFixed(decimais + 1))].join(',')))
    const blob = new Blob(['\ufeff' + linhas.join('\n')], { type: 'text/csv;charset=utf-8' })
    const a = document.createElement('a')
    a.href = URL.createObjectURL(blob)
    a.download = `${arquivo}.csv`
    a.click()
    URL.revokeObjectURL(a.href)
  }

  const valores = series.flatMap((s) => s.pontos.map((p) => p.valor))
  const min = Math.min(...valores)
  const max = Math.max(...valores)
  const dominio: [number | 'auto', number | 'auto'] = dominioZero
    ? [0, Math.ceil(max / passoY) * passoY || 'auto']
    : [Math.floor(min / passoY) * passoY, Math.ceil(max / passoY) * passoY || 'auto']

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

      <div className="chart-wrap" role="img" aria-label={`${titulo}: gráfico de ${tipo === 'linha' ? 'linha' : 'barras'}`}>
        <ResponsiveContainer width="100%" height={altura}>
          <ComposedChart data={dados} margin={{ top: 14, right: 20, bottom: 14, left: 12 }}>
            <CartesianGrid stroke="#e5ece9" strokeDasharray="3 3" vertical={false} />
            <XAxis dataKey="rotulo" tick={{ fill: '#5c7370', fontSize: 12 }} tickLine={false} axisLine={{ stroke: '#cfdad6' }} minTickGap={22} />
            <YAxis
              width={48}
              domain={dominio}
              tick={{ fill: '#5c7370', fontSize: 12 }}
              tickLine={false}
              axisLine={false}
              tickFormatter={(v: number) => fmtNum(v, 0)}
              label={{ value: unidade, angle: -90, position: 'insideLeft', fill: '#5c7370', fontSize: 12 }}
            />
            <Tooltip content={(props) => <TooltipClima {...props} unidade={unidade} decimais={decimais} series={series} />} />
            {areas.map((a) => <ReferenceArea key={a.key} x1={a.x1} x2={a.x2} fill={a.fill} fillOpacity={0.72} ifOverflow="extendDomain" />)}
            {series.map((s) => tipo === 'linha'
              ? <Line key={s.nome} type="monotone" dataKey={s.nome} stroke={s.cor} strokeWidth={2.5} dot={false} activeDot={{ r: 4 }} />
              : <Bar key={s.nome} dataKey={s.nome} fill={s.cor} maxBarSize={18} />)}
            <Brush dataKey="rotulo" height={24} stroke="#0b6b63" fill="#f4f7f5" travellerWidth={9} />
          </ComposedChart>
        </ResponsiveContainer>
      </div>

      <footer className="legend">
        <ul>
          {series.map((s) => (
            <li key={s.nome}>
              <i className={tipo === 'linha' ? 'swatch swatch--line' : 'swatch swatch--bar'} style={{ background: s.cor }} />
              {s.nome}
            </li>
          ))}
          <li><i className="swatch swatch--bar" style={{ background: COR_EL_NINO }} />El Niño</li>
          <li><i className="swatch swatch--bar" style={{ background: COR_LA_NINA }} />La Niña</li>
        </ul>
        <span className="legend__hint">Use a barra inferior para ampliar</span>
      </footer>
    </article>
  )
}
