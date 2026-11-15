import { useState } from 'react'
import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { Estado, Figura, ItemLegenda, Segmentos } from '../Editorial/Editorial'
import { type Recurso } from '../Editorial/useRecurso'
import {
  casasDe, COR_REGIAO, fmt, fmtInt, fmtSinal, MESES_CURTOS, NOME_VARIAVEL, REGIOES, UNIDADE,
  type Regiao, type Regioes, type VariavelClima,
} from '../../data/estatisticas'
import { EIXO, GRADE, tooltipEd } from './graficos'

export function SecaoRegional({ regioes, numero, destaque }: { regioes: Recurso<Regioes>; numero: number; destaque: Regiao | null }) {
  const [variavel, setVariavel] = useState<VariavelClima>('precipitacao')
  const d = regioes.dados
  const casas = casasDe(variavel)
  const pontos = (() => {
    if (!d) return []
    return Array.from({ length: 12 }, (_, i) => {
      const linha: Record<string, string | number | null> = { x: MESES_CURTOS[i] }
      for (const r of REGIOES) linha[r] = d.ciclo_mensal.find((c) => c.regiao === r && c.mes === i + 1)?.[variavel] ?? null
      return linha
    })
  })()
  const dica = tooltipEd({ unidade: UNIDADE[variavel], casas })
  const areaTotal = d?.regioes.reduce((s, r) => s + (r.area_km2 ?? 0), 0) ?? 0
  const areaNorte = d?.regioes.find((r) => r.regiao === 'Norte')?.area_km2 ?? null
  const pesoNorte = areaTotal > 0 && areaNorte !== null ? (100 * areaNorte) / areaTotal : null

  return (
    <div className="ed-grade ed-grade--2">
      <Figura
        numero={numero}
        titulo={`Ciclo anual por região — ${NOME_VARIAVEL[variavel]}`}
        unidade={`Unidade: ${UNIDADE[variavel]} · média de cada mês do calendário no período`}
        controles={<Segmentos rotulo="Variável" valor={variavel} onChange={setVariavel}
          opcoes={[['precipitacao', 'Precipitação'], ['temperatura', 'Temperatura'], ['umidade', 'Umidade']]} />}
        legenda="Médias ponderadas pela área dos municípios de cada região. Diferenças de regime (época chuvosa, amplitude térmica) refletem latitude, relevo e circulação atmosférica; o gráfico descreve, não explica a causa."
      >
        <ul className="ed-legenda">
          {REGIOES.map((r) => <ItemLegenda key={r} cor={COR_REGIAO[r]} texto={r} linha />)}
        </ul>
        {regioes.erro && !d ? <Estado tipo="erro" altura={280}>{regioes.erro}</Estado>
          : !d ? <Estado tipo="carregando" altura={280} />
            : (
              <div className={`ed-grafico ed-grafico--medio${regioes.carregando ? ' ed-atualizando' : ''}`}>
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={pontos} margin={{ top: 8, right: 12, bottom: 4, left: 0 }}>
                    <CartesianGrid {...GRADE} />
                    <XAxis dataKey="x" {...EIXO} />
                    <YAxis {...EIXO} width={48} domain={['auto', 'auto']} tickFormatter={(v: number) => fmt(v, 0)} />
                    <Tooltip content={dica} cursor={{ stroke: '#999', strokeWidth: 1 }} />
                    {REGIOES.map((r) => (
                      <Line key={r} dataKey={r} stroke={COR_REGIAO[r]} isAnimationActive={false}
                        strokeWidth={destaque && destaque !== r ? 1.25 : 2} strokeOpacity={destaque && destaque !== r ? 0.4 : 1}
                        dot={false} activeDot={{ r: 4, stroke: '#fff', strokeWidth: 2 }} />
                    ))}
                  </LineChart>
                </ResponsiveContainer>
              </div>
            )}
      </Figura>
      <div>
        <h3 className="ed-figura__titulo" style={{ marginBottom: 12 }}>Comparação entre regiões</h3>
        {d
          ? (
            <div className={`ed-tabela-wrap${regioes.carregando ? ' ed-atualizando' : ''}`}>
              <table className="ed-tabela">
                <caption>Média no recorte (estação e fase ENSO filtradas) e diferença para o Brasil</caption>
                <thead>
                  <tr><th>Região</th><th>Municípios</th><th>Temp. (°C)</th><th>Chuva (mm/mês)</th><th>Umidade (%)</th></tr>
                </thead>
                <tbody>
                  {d.regioes.map((r) => (
                    <tr key={r.regiao} style={destaque === r.regiao ? { background: '#e6f1ee' } : undefined}>
                      <td><i className="inicio-ponto" style={{ background: COR_REGIAO[r.regiao] }} />{r.regiao}</td>
                      <td>{fmtInt(r.municipios)}</td>
                      {(['temperatura', 'precipitacao', 'umidade'] as const).map((v) => (
                        <td key={v}>
                          {fmt(r[v], casasDe(v))}{' '}
                          <span className="est-delta">({fmtSinal(r[v] !== null && d.brasil[v] !== null ? r[v]! - d.brasil[v]! : null, casasDe(v))})</span>
                        </td>
                      ))}
                    </tr>
                  ))}
                  <tr>
                    <td><b>Brasil</b></td>
                    <td>{fmtInt(d.regioes.reduce((s, r) => s + r.municipios, 0))}</td>
                    <td><b>{fmt(d.brasil.temperatura, 1)}</b></td>
                    <td><b>{fmt(d.brasil.precipitacao, 0)}</b></td>
                    <td><b>{fmt(d.brasil.umidade, 1)}</b></td>
                  </tr>
                </tbody>
                <tfoot><tr><td colSpan={5}>Entre parênteses: diferença para a média nacional (ponderada pela área). {pesoNorte !== null && <> O Norte responde por {fmt(pesoNorte, 0)}% da área com dados, por isso pesa mais na média nacional.</>}</td></tr></tfoot>
              </table>
            </div>
          )
          : <Estado tipo="carregando" altura={220} />}
      </div>
    </div>
  )
}
