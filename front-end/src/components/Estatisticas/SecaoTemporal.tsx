import { useMemo, useState } from 'react'
import { CartesianGrid, Line, LineChart, ReferenceArea, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { Estado, Figura, Segmentos } from '../Editorial/Editorial'
import { type Recurso } from '../Editorial/useRecurso'
import {
  casasDe, COR_FASE, COR_VARIAVEL, fmt, MESES_CURTOS, NOME_FASE, NOME_VARIAVEL, UNIDADE,
  type FaseEnso, type Recorte, type Serie, type VariavelClima,
} from '../../data/estatisticas'
import { NOMES_ESTACAO } from '../../data/seasons'
import { EIXO, GRADE, tooltipEd } from './graficos'

type Visao = 'mensal' | 'anual' | 'ciclo'
const FUNDO_FASE: Partial<Record<FaseEnso, string>> = { el_nino: '#f8e0d6', la_nina: '#dbe6f6' }

export function SecaoTemporal({ serie, recorte, escopo, numero }: { serie: Recurso<Serie>; recorte: Recorte; escopo: string; numero: number }) {
  const [variavel, setVariavel] = useState<VariavelClima>('temperatura')
  const [visao, setVisao] = useState<Visao>('mensal')
  const casas = casasDe(variavel)
  const d = serie.dados

  const { pontos, bandas, unidade, chave, rotuloX } = useMemo(() => {
    if (!d) return { pontos: [], bandas: [], unidade: UNIDADE[variavel], chave: 'y', rotuloX: '' }
    if (visao === 'mensal') {
      const pts = d.mensal.map((p) => ({ x: `${p.ano}-${String(p.mes).padStart(2, '0')}`, y: p[variavel], fase: p.fase, oni: p.oni, ano: p.ano, mes: p.mes }))
      // faixas contínuas de El Niño e La Niña atrás da linha
      const faixas: { fase: FaseEnso; x1: string; x2: string }[] = []
      for (const p of pts) {
        const ultima = faixas[faixas.length - 1]
        if (p.fase && p.fase !== 'neutro') {
          if (ultima && ultima.fase === p.fase && ultima.x2 === pts[pts.indexOf(p) - 1]?.x) ultima.x2 = p.x
          else faixas.push({ fase: p.fase, x1: p.x, x2: p.x })
        }
      }
      return { pontos: pts, bandas: faixas, unidade: UNIDADE[variavel], chave: 'y', rotuloX: 'Mês' }
    }
    if (visao === 'anual') {
      const total = variavel === 'precipitacao' && d.anual.every((a) => a.precipitacao_total !== null)
      const pts = d.anual.map((a) => ({
        x: String(a.ano),
        y: variavel === 'precipitacao' ? (total ? a.precipitacao_total : a.precipitacao_mensal) : a[variavel],
        meses: a.meses,
      }))
      const un = variavel === 'precipitacao' ? (total ? (recorte.estacao ? 'mm/estação' : 'mm/ano') : 'mm/mês') : UNIDADE[variavel]
      return { pontos: pts, bandas: [], unidade: un, chave: 'y', rotuloX: 'Ano' }
    }
    const pts = d.ciclo_mensal.map((c) => ({ x: MESES_CURTOS[c.mes - 1], y: c[variavel] }))
    return { pontos: pts, bandas: [], unidade: UNIDADE[variavel], chave: 'y', rotuloX: 'Mês do ano' }
  }, [d, visao, variavel, recorte.estacao])

  const dica = tooltipEd({
    unidade, casas: visao === 'anual' && variavel === 'precipitacao' && unidade !== 'mm/mês' ? 0 : casas,
    nome: () => NOME_VARIAVEL[variavel],
    titulo: (label, p) => {
      if (visao !== 'mensal') return String(label)
      const q = p as { ano: number; mes: number }
      return `${MESES_CURTOS[q.mes - 1]}/${q.ano}`
    },
    extra: (p) => {
      if (visao === 'mensal') {
        const q = p as { fase: FaseEnso | null; oni: number | null }
        return q.fase ? `${NOME_FASE[q.fase]} · ONI ${fmt(q.oni, 2)}` : null
      }
      if (visao === 'anual') return `${(p as { meses: number }).meses} meses no recorte`
      return null
    },
  })

  const filtroTempo = [recorte.estacao && NOMES_ESTACAO[recorte.estacao].toLowerCase(), recorte.enso && NOME_FASE[recorte.enso]].filter(Boolean).join(' e ')
  const legenda = visao === 'mensal'
    ? <>Média mensal ({escopo}), ponderada pela área municipal. Faixas ao fundo: episódios de <b style={{ color: '#7d2d12' }}>El Niño</b> e <b style={{ color: '#1d4f91' }}>La Niña</b> (regra do NOAA/CPC). A série mensal mostra todos os meses; os filtros de estação e ENSO valem para as visões anual e de ciclo.</>
    : visao === 'anual'
      ? <>Média dos meses de cada ano{filtroTempo ? ` (só ${filtroTempo})` : ''}. {variavel === 'precipitacao' && (unidade === 'mm/mês'
        ? 'Com filtro ENSO os anos têm números de meses diferentes, por isso a chuva é mostrada em mm/mês.'
        : 'Chuva: total do ano (ou da estação no ano).')}</>
      : <>Ciclo sazonal médio: média de cada mês do calendário no período{recorte.enso ? `, só nos meses de ${NOME_FASE[recorte.enso]}` : ''}.</>

  return (
    <Figura
      numero={numero}
      titulo={`Evolução temporal — ${NOME_VARIAVEL[variavel]}`}
      unidade={`Unidade: ${unidade} · ${escopo}`}
      controles={(
        <div className="ed-controles" style={{ marginBottom: 0 }}>
          <Segmentos rotulo="Variável" valor={variavel} onChange={setVariavel}
            opcoes={[['temperatura', 'Temperatura'], ['precipitacao', 'Precipitação'], ['umidade', 'Umidade']]} />
          <Segmentos rotulo="Visão temporal" valor={visao} onChange={setVisao}
            opcoes={[['mensal', 'Mensal'], ['anual', 'Anual'], ['ciclo', 'Ciclo sazonal']]} />
        </div>
      )}
      legenda={legenda}
    >
      {serie.erro && !d
        ? <Estado tipo="erro" altura={340}>Não foi possível carregar a série: {serie.erro}</Estado>
        : !d
          ? <Estado tipo="carregando" altura={340} />
          : pontos.length === 0
            ? <Estado tipo="vazio" altura={340}>Nenhum mês no recorte escolhido.</Estado>
            : (
              <div className={`ed-grafico ed-grafico--alto${serie.carregando ? ' ed-atualizando' : ''}`} aria-busy={serie.carregando}>
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={pontos} margin={{ top: 8, right: 12, bottom: 4, left: 0 }}>
                    <CartesianGrid {...GRADE} />
                    {bandas.map((b) => (
                      <ReferenceArea key={`${b.fase}-${b.x1}`} x1={b.x1} x2={b.x2} fill={FUNDO_FASE[b.fase]} fillOpacity={1} strokeOpacity={0} ifOverflow="hidden" />
                    ))}
                    <XAxis dataKey="x" {...EIXO} minTickGap={24} interval="preserveStartEnd"
                      tickFormatter={(v: string) => (visao === 'mensal' ? (v.endsWith('-01') ? v.slice(0, 4) : '') : v)}
                      label={{ value: rotuloX, position: 'insideBottomRight', offset: -2, fontSize: 12, fill: '#5f6b6b' }} height={36} />
                    <YAxis {...EIXO} width={52} domain={['auto', 'auto']} tickFormatter={(v: number) => fmt(v, variavel === 'precipitacao' ? 0 : 0)}
                      label={{ value: unidade, angle: -90, position: 'insideLeft', fontSize: 12, fill: '#5f6b6b', dy: 30 }} />
                    <Tooltip content={dica} cursor={{ stroke: '#999', strokeWidth: 1 }} />
                    <Line dataKey={chave} name={NOME_VARIAVEL[variavel]} stroke={COR_VARIAVEL[variavel]} strokeWidth={2}
                      dot={visao !== 'mensal' ? { r: 3.5, strokeWidth: 0, fill: COR_VARIAVEL[variavel] } : false}
                      activeDot={{ r: 5, stroke: '#fff', strokeWidth: 2 }} isAnimationActive={false} connectNulls={false} />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            )}
      {visao === 'mensal' && d && (
        <ul className="ed-legenda" style={{ marginTop: 8 }}>
          <li><i className="linha" style={{ background: COR_VARIAVEL[variavel] }} />{NOME_VARIAVEL[variavel]}</li>
          <li><i style={{ background: FUNDO_FASE.el_nino, outline: `1px solid ${COR_FASE.el_nino}` }} />El Niño</li>
          <li><i style={{ background: FUNDO_FASE.la_nina, outline: `1px solid ${COR_FASE.la_nina}` }} />La Niña</li>
        </ul>
      )}
    </Figura>
  )
}
