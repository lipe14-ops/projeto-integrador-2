import { useMemo } from 'react'
import {
  Bar,
  Brush,
  CartesianGrid,
  ComposedChart,
  Line,
  ReferenceArea,
  ReferenceDot,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
  type TooltipContentProps,
} from 'recharts'
import { ANO_INICIO, rotuloMes, type EpisodioEnso, type Ponto } from '../data/climate'
import {
  NOMES_ESTACAO,
  ORDEM_ESTACOES,
  diasNoMes,
  formatarData,
  intervalosEstacoes,
  partesDoPeriodo,
  type DataCivil,
  type Estacao,
  type MetodoEstacao,
} from '../data/seasons'
import { IconDownload } from './Icons'

/** Evento marcado no eixo do tempo (▼), na data real. */
export interface Marcador {
  id: string
  grupo: string // eventos com o mesmo grupo são destacados juntos
  data: DataCivil
  texto: string
}

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
  passoY: number
  /** null oculta as estações */
  metodoEstacao: MetodoEstacao | null
  /** gráficos com o mesmo syncId compartilham cursor e zoom */
  syncId?: string
  /** só o gráfico sob o ponteiro/toque mostra o tooltip; os demais mostram o cursor sincronizado */
  tooltipVisivel?: boolean
  onAtivar?: (ativo: boolean) => void
  dominioZero?: boolean
  marcadores?: Marcador[]
  /** grupo de marcadores em destaque */
  destaque?: string | null
  rotuloMarcadores?: string
}

interface LinhaGrafico {
  x: number // centro do período em "meses desde jan/2015" (eixo numérico)
  rotulo: string
  inicio: number
  fim: number
  episodio?: string
  [key: string]: string | number | null | undefined
}

// Tons sazonais dessaturados, harmonizados com a paleta (areia ↔ --rust,
// terroso, azul-acinzentado ↔ --blue, sálvia ↔ --green). Usados com baixa opacidade.
const COR_ESTACAO: Record<Estacao, string> = {
  verao: '#efd29b',
  outono: '#dfc0a6',
  inverno: '#c6d6e4',
  primavera: '#cfe2c8',
}
// estações na faixa superior: tons cheios, já que a faixa é estreita
// ENSO no fundo da área de dados: versões mais densas de --el-nino / --la-nina,
// aplicadas com baixa opacidade para as séries continuarem em destaque.
const COR_EL_NINO = '#eab89c'
const COR_LA_NINA = '#a9c6e0'
const OPACIDADE_ENSO = 0.32
const FRACAO_FAIXA_ESTACOES = 0.09
const LARGURA_EIXO_Y = 56

const fmtNum = (v: number, d: number) => v.toLocaleString('pt-BR', { minimumFractionDigits: d, maximumFractionDigits: d })
const dataDoMes = (indice: number): DataCivil => ({ ano: ANO_INICIO + Math.floor(indice / 12), mes: (indice % 12) + 1, dia: 1 })

/** Posição de uma data no eixo X (meses fracionários desde jan/ANO_INICIO). */
function posicao(d: DataCivil): number {
  return (d.ano - ANO_INICIO) * 12 + (d.mes - 1) + (d.dia - 1) / diasNoMes(d.ano, d.mes)
}
const posicaoFimDoDia = (d: DataCivil) => posicao(d) + 1 / diasNoMes(d.ano, d.mes)

function passoLegivel(passoBase: number, amplitude: number): number {
  for (const fator of [1, 2, 5, 10, 20, 50, 100, 200]) {
    const passo = passoBase * fator
    if (amplitude / passo <= 6) return passo
  }
  return passoBase * 500
}

type PropsTooltip = TooltipContentProps & {
  unidade: string
  decimais: number
  series: SerieGrafico[]
  metodoEstacao: MetodoEstacao | null
  marcadores: Marcador[]
}

function TooltipClima({ active, payload, unidade, decimais, series, metodoEstacao, marcadores }: PropsTooltip) {
  if (!active || !payload?.length) return null
  const dados = payload[0]?.payload as LinhaGrafico | undefined
  if (!dados) return null
  const partes = metodoEstacao ? partesDoPeriodo(metodoEstacao, dataDoMes(dados.inicio), dataDoMes(dados.fim)) : []
  return (
    <div className="tooltip chart-tooltip">
      <strong>{dados.rotulo}</strong>
      {series.map((s) => {
        const valor = dados[s.nome]
        return (
          <span key={s.nome} className="tooltip__row">
            <i style={{ background: s.cor }} />
            {s.nome}: {typeof valor === 'number' ? `${fmtNum(valor, decimais)} ${unidade}` : 'sem dado'}
          </span>
        )
      })}
      {dados.episodio && <span className="tooltip__enso">{dados.episodio}</span>}
      {marcadores
        .filter((m) => { const x = posicao(m.data); return x >= dados.inicio && x < dados.fim })
        .map((m) => <span key={m.id} className="tooltip__evento">▼ {m.texto}</span>)}
      {partes.length > 0 && (
        <span className="tooltip__seasons">
          {partes.map(({ intervalo, dias }) => (
            <span key={intervalo.rotulo} className="tooltip__season">
              <i style={{ background: COR_ESTACAO[intervalo.estacao] }} />
              <span>
                <b>{intervalo.rotulo}</b>
                {partes.length > 1 && ` · ${dias} dias neste período`}
                <br />
                {formatarData(intervalo.inicio)} a {formatarData(intervalo.fim)}
              </span>
            </span>
          ))}
        </span>
      )}
    </div>
  )
}

export function TimeSeriesChart({
  titulo, subtitulo, unidade, tipo, series, episodios, decimais, arquivo, passoY, metodoEstacao, syncId, dominioZero,
  tooltipVisivel = true, onAtivar, marcadores = [], destaque = null, rotuloMarcadores = 'Evento extremo',
}: Props) {
  const dados = useMemo<LinhaGrafico[]>(() => {
    const base = series[0]?.pontos ?? []
    return base.map((p, i) => {
      const episodio = episodios.find((e) => e.inicio < p.fim && e.fim > p.inicio)
      const linha: LinhaGrafico = {
        x: (p.inicio + p.fim) / 2,
        rotulo: p.rotulo,
        inicio: p.inicio,
        fim: p.fim,
        episodio: episodio ? (episodio.tipo === 'el-nino' ? 'El Niño' : 'La Niña') : undefined,
      }
      series.forEach((s) => {
        const valor = s.pontos[i]?.valor
        linha[s.nome] = valor !== undefined && Number.isFinite(valor) ? valor : null
      })
      return linha
    })
  }, [series, episodios])

  const inicioMes = dados[0]?.inicio ?? 0
  const fimMes = dados[dados.length - 1]?.fim ?? 0

  const faixasEstacao = useMemo(() => {
    if (!metodoEstacao || fimMes <= inicioMes) return []
    return intervalosEstacoes(metodoEstacao, dataDoMes(inicioMes), dataDoMes(fimMes)).map((intervalo) => ({
      intervalo,
      x1: posicao(intervalo.inicioVisivel),
      x2: posicaoFimDoDia(intervalo.fimVisivel),
    }))
  }, [metodoEstacao, inicioMes, fimMes])

  const valores = series.flatMap((s) => s.pontos.map((p) => p.valor)).filter(Number.isFinite)
  const minimo = valores.length ? Math.min(...valores) : 0
  const maximo = valores.length ? Math.max(...valores) : 1
  const passo = passoLegivel(passoY, maximo - (dominioZero ? 0 : minimo))
  const base = dominioZero ? 0 : Math.floor(minimo / passo) * passo
  let topo = Math.ceil(maximo / passo) * passo
  if (topo <= base) topo = base + passo
  const ticksY = Array.from({ length: Math.round((topo - base) / passo) + 1 }, (_, i) => +(base + i * passo).toFixed(6))
  // margem acima do maior tick reservada à faixa das estações: nunca cobre os dados
  const topoComFaixa = topo + (topo - base) * FRACAO_FAIXA_ESTACOES

  const faixasEnso = episodios
    .map((ep, i) => ({ key: i, x1: Math.max(ep.inicio, inicioMes), x2: Math.min(ep.fim, fimMes), tipo: ep.tipo }))
    .filter((f) => f.x2 > f.x1)

  const ticksX = useMemo(() => {
    const meses = fimMes - inicioMes
    const salto = meses <= 24 ? 1 : meses <= 60 ? 3 : 12
    const ticks: number[] = []
    for (let m = inicioMes; m < fimMes; m++) if (m % salto === 0) ticks.push(m + 0.5)
    return ticks
  }, [inicioMes, fimMes])

  const mostrarLetras = fimMes - inicioMes <= 36
  const pontosMarcadores = useMemo(
    () => marcadores
      .map((m) => ({ ...m, x: posicao(m.data) + 0.5 / diasNoMes(m.data.ano, m.data.mes) }))
      .filter((m) => m.x >= inicioMes && m.x < fimMes),
    [marcadores, inicioMes, fimMes],
  )

  function baixar() {
    const linhas = [['periodo', ...series.map((s) => `${s.nome} (${unidade})`)].join(',')]
    dados.forEach((p) => linhas.push([
      p.rotulo,
      ...series.map((s) => (typeof p[s.nome] === 'number' ? (p[s.nome] as number).toFixed(decimais + 1) : '')),
    ].join(',')))
    const blob = new Blob(['﻿' + linhas.join('\n')], { type: 'text/csv;charset=utf-8' })
    const a = document.createElement('a')
    a.href = URL.createObjectURL(blob)
    a.download = `${arquivo}.csv`
    a.click()
    URL.revokeObjectURL(a.href)
  }

  const periodoTexto = dados.length ? `${dados[0].rotulo} a ${dados[dados.length - 1].rotulo}` : 'sem dados'

  return (
    <article className="card chart-card">
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

      <div
        className="chart-wrap"
        role="img"
        onPointerEnter={() => onAtivar?.(true)}
        onPointerDown={() => onAtivar?.(true)}
        onPointerLeave={(e) => { if (e.pointerType === 'mouse') onAtivar?.(false) }}
        aria-label={`${titulo} (${unidade}), ${tipo === 'linha' ? 'gráfico de linha' : 'gráfico de barras'} mensal, ${periodoTexto}${metodoEstacao ? ', com faixas das estações do ano' : ''}`}
      >
        <ResponsiveContainer width="100%" height="100%">
          <ComposedChart data={dados} syncId={syncId} margin={{ top: 8, right: 16, bottom: 4, left: 0 }}>
            {/* fundo: episódios El Niño / La Niña, em toda a altura e com baixa opacidade */}
            {faixasEnso.map((f) => (
              <ReferenceArea
                key={`enso-${f.key}`}
                x1={f.x1}
                x2={f.x2}
                y1={base}
                y2={topo}
                fill={f.tipo === 'el-nino' ? COR_EL_NINO : COR_LA_NINA}
                fillOpacity={OPACIDADE_ENSO}
                stroke="none"
                ifOverflow="hidden"
              />
            ))}
            {/* faixa superior: estações do ano, acima do maior valor (nunca cobre os dados) */}
            {faixasEstacao.map(({ intervalo, x1, x2 }) => (
              <ReferenceArea
                key={`${intervalo.rotulo}-${x1}`}
                x1={x1}
                x2={x2}
                y1={topo}
                y2={topoComFaixa}
                fill={COR_ESTACAO[intervalo.estacao]}
                fillOpacity={1}
                stroke="#ffffff"
                strokeWidth={1}
                ifOverflow="hidden"
                label={mostrarLetras ? { value: intervalo.nome[0], position: 'center', fill: '#5c6f6b', fontSize: 10, fontWeight: 600 } : undefined}
              />
            ))}
            <CartesianGrid stroke="#dfe7e4" strokeDasharray="3 3" vertical={false} />
            <XAxis
              dataKey="x"
              type="number"
              domain={['dataMin - 0.5', 'dataMax + 0.5']}
              allowDataOverflow
              ticks={ticksX}
              tickFormatter={(v: number) => rotuloMes(Math.floor(v))}
              tick={{ fill: '#5c7370', fontSize: 12 }}
              tickLine={false}
              axisLine={{ stroke: '#cfdad6' }}
              minTickGap={18}
            />
            <YAxis
              width={LARGURA_EIXO_Y}
              domain={[base, topoComFaixa]}
              ticks={ticksY}
              allowDataOverflow
              tick={{ fill: '#5c7370', fontSize: 12 }}
              tickLine={false}
              axisLine={false}
              tickFormatter={(v: number) => fmtNum(v, passo < 1 ? 1 : 0)}
              label={{ value: unidade, angle: -90, position: 'insideLeft', fill: '#5c7370', fontSize: 12, offset: 6 }}
            />
            <Tooltip
              cursor={{ stroke: '#0f2f2d', strokeOpacity: 0.45, strokeDasharray: '3 3' }}
              content={(props) => tooltipVisivel && (
                <TooltipClima {...props} unidade={unidade} decimais={decimais} series={series} metodoEstacao={metodoEstacao} marcadores={pontosMarcadores} />
              )}
            />
            {series.map((s) => tipo === 'linha'
              ? <Line key={s.nome} type="monotone" dataKey={s.nome} stroke={s.cor} strokeWidth={2.5} dot={false} activeDot={{ r: 4 }} connectNulls={false} isAnimationActive={false} />
              : <Bar key={s.nome} dataKey={s.nome} fill={s.cor} maxBarSize={18} isAnimationActive={false} />)}
            {pontosMarcadores.filter((m) => m.grupo === destaque).map((m) => (
              <ReferenceLine key={`guia-${m.id}`} x={m.x} ifOverflow="discard" stroke="#0f2f2d" strokeOpacity={0.55} strokeDasharray="4 3" />
            ))}
            {pontosMarcadores.map((m) => {
              const ativo = destaque === m.grupo
              return (
                <ReferenceDot
                  key={m.id}
                  x={m.x}
                  y={topo}
                  ifOverflow="discard"
                  shape={({ cx, cy }: { cx?: number; cy?: number }) => {
                    if (cx === undefined || cy === undefined) return <g />
                    const t = ativo ? 8 : 5.5
                    return (
                      <g className={ativo ? 'marcador is-ativo' : 'marcador'}>
                        <path d={`M${cx - t} ${cy - t * 1.6}L${cx + t} ${cy - t * 1.6}L${cx} ${cy}Z`} />
                      </g>
                    )
                  }}
                />
              )
            })}
            <Brush dataKey="rotulo" height={24} stroke="#0b6b63" fill="#f4f7f5" travellerWidth={9} />
          </ComposedChart>
        </ResponsiveContainer>
      </div>

      <footer className="legend">
        <ul aria-label="Séries">
          {series.map((s) => (
            <li key={s.nome}>
              <i className={tipo === 'linha' ? 'swatch swatch--line' : 'swatch swatch--bar'} style={{ background: s.cor }} />
              {s.nome}
            </li>
          ))}
          {marcadores.length > 0 && <li><span className="swatch-marcador" aria-hidden="true">▼</span>{rotuloMarcadores}</li>}
          <li><i className="swatch swatch--season" style={{ background: COR_EL_NINO, opacity: 0.6 }} />El Niño (fundo)</li>
          <li><i className="swatch swatch--season" style={{ background: COR_LA_NINA, opacity: 0.6 }} />La Niña (fundo)</li>
        </ul>
        {metodoEstacao && (
          <ul className="legend__seasons" aria-label="Estações do ano (faixa superior do gráfico)">
            {ORDEM_ESTACOES.map((estacao) => (
              <li key={estacao}>
                <i className="swatch swatch--strip" style={{ background: COR_ESTACAO[estacao] }} />
                {NOMES_ESTACAO[estacao]}
              </li>
            ))}
          </ul>
        )}
      </footer>
    </article>
  )
}
