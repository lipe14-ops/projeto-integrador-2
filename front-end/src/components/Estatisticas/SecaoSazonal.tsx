import { useState } from 'react'
import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { Estado, Figura, ItemLegenda, Segmentos } from '../Editorial/Editorial'
import { type Recurso } from '../Editorial/useRecurso'
import { COR_ESTACAO } from '../Analise/cores'
import { fmt, NOME_VARIAVEL, type Sazonal, type VariavelClima } from '../../data/estatisticas'
import { NOMES_ESTACAO, ORDEM_ESTACOES, type Estacao } from '../../data/seasons'
import { EIXO, GRADE, tooltipEd } from './graficos'

const CAMPO = { temperatura: 'temperatura', umidade: 'umidade', precipitacao: 'precipitacao_total' } as const
const UNID = { temperatura: '°C', umidade: '%', precipitacao: 'mm/estação' } as const

export function SecaoSazonal({ sazonal, escopo, numero, estacaoFiltro }: { sazonal: Recurso<Sazonal>; escopo: string; numero: number; estacaoFiltro: Estacao | null }) {
  const [variavel, setVariavel] = useState<VariavelClima>('precipitacao')
  const d = sazonal.dados
  const campo = CAMPO[variavel]
  const casas = variavel === 'precipitacao' ? 0 : 1
  const pontos = (() => {
    if (!d) return []
    const anos = [...new Set(d.por_ano.map((p) => p.ano))].sort()
    return anos.map((ano) => {
      const linha: Record<string, number | string | null> = { x: String(ano) }
      for (const e of ORDEM_ESTACOES) linha[e] = d.por_ano.find((p) => p.ano === ano && p.estacao === e)?.[campo] ?? null
      return linha
    })
  })()
  const dica = tooltipEd({ unidade: UNID[variavel], casas, nome: (k) => NOMES_ESTACAO[k as Estacao] })

  return (
    <div className="ed-grade ed-grade--2">
      <Figura
        numero={numero}
        titulo={`Cada estação, ano a ano — ${NOME_VARIAVEL[variavel]}`}
        unidade={`Unidade: ${UNID[variavel]} · ${escopo}`}
        controles={<Segmentos rotulo="Variável" valor={variavel} onChange={setVariavel}
          opcoes={[['precipitacao', 'Precipitação'], ['temperatura', 'Temperatura'], ['umidade', 'Umidade']]} />}
        legenda={<>{d?.nota} O verão de 2015 (sem dezembro de 2014) não entra.{estacaoFiltro && ' Esta seção compara as quatro estações; o filtro de estação não se aplica.'}</>}
      >
        <ul className="ed-legenda">
          {ORDEM_ESTACOES.map((e) => <ItemLegenda key={e} cor={COR_ESTACAO[e]} texto={NOMES_ESTACAO[e]} linha />)}
        </ul>
        {sazonal.erro && !d
          ? <Estado tipo="erro" altura={280}>{sazonal.erro}</Estado>
          : !d ? <Estado tipo="carregando" altura={280} />
            : pontos.length === 0 ? <Estado tipo="vazio" altura={280}>Nenhuma estação completa no período escolhido.</Estado>
              : (
                <div className={`ed-grafico ed-grafico--medio${sazonal.carregando ? ' ed-atualizando' : ''}`}>
                  <ResponsiveContainer width="100%" height="100%">
                    <LineChart data={pontos} margin={{ top: 8, right: 12, bottom: 4, left: 0 }}>
                      <CartesianGrid {...GRADE} />
                      <XAxis dataKey="x" {...EIXO} />
                      <YAxis {...EIXO} width={52} domain={['auto', 'auto']} tickFormatter={(v: number) => fmt(v, 0)} />
                      <Tooltip content={dica} cursor={{ stroke: '#999', strokeWidth: 1 }} />
                      {ORDEM_ESTACOES.map((e) => (
                        <Line key={e} dataKey={e} stroke={COR_ESTACAO[e]} strokeWidth={estacaoFiltro && estacaoFiltro !== e ? 1.25 : 2}
                          strokeOpacity={estacaoFiltro && estacaoFiltro !== e ? 0.45 : 1}
                          dot={{ r: 3, strokeWidth: 0, fill: COR_ESTACAO[e] }} isAnimationActive={false} connectNulls={false} />
                      ))}
                    </LineChart>
                  </ResponsiveContainer>
                </div>
              )}
      </Figura>
      <div>
        <h3 className="ed-figura__titulo" style={{ marginBottom: 12 }}>Resumo por estação</h3>
        {d && d.resumo.length > 0
          ? (
            <div className="ed-tabela-wrap">
              <table className="ed-tabela">
                <caption>{NOME_VARIAVEL[variavel]} ({UNID[variavel]}) — média entre os anos e os anos extremos</caption>
                <thead><tr><th>Estação</th><th>Anos</th><th>Média</th><th>Mínimo (ano)</th><th>Máximo (ano)</th></tr></thead>
                <tbody>
                  {d.resumo.map((r) => {
                    const v = r[campo]
                    return (
                      <tr key={r.estacao}>
                        <td><i className="inicio-ponto" style={{ background: COR_ESTACAO[r.estacao] }} />{NOMES_ESTACAO[r.estacao]}</td>
                        <td>{r.anos}</td>
                        <td><b>{fmt(v.media, casas)}</b></td>
                        <td>{fmt(v.min, casas)} ({v.ano_min})</td>
                        <td>{fmt(v.max, casas)} ({v.ano_max})</td>
                      </tr>
                    )
                  })}
                </tbody>
                <tfoot><tr><td colSpan={5}>Amplitude entre anos = variabilidade interanual; com 10–11 anos, não indica tendência.</td></tr></tfoot>
              </table>
            </div>
          )
          : d ? <Estado tipo="vazio">Sem estações completas.</Estado> : <Estado tipo="carregando" altura={200} />}
      </div>
    </div>
  )
}
