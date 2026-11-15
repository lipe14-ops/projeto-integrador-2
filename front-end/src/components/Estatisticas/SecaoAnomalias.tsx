import { useState } from 'react'
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { Estado, Figura, ItemLegenda, Segmentos } from '../Editorial/Editorial'
import { type Recurso } from '../Editorial/useRecurso'
import { COR_CLASSE, fmt, fmtInt, ROTULO_ANOMALIA, type Anomalias, type IdAnomalia } from '../../data/estatisticas'
import { NOMES_ESTACAO } from '../../data/seasons'
import { EIXO, GRADE, tooltipEd } from './graficos'

const NOME_CLASSE = { estatisticas: 'Anomalia estatística', extremos: 'Extremo local' } as const

function Barras({ dados, chaveX, carregando }: { dados: Record<string, unknown>[]; chaveX: string; carregando: boolean }) {
  const dica = tooltipEd({
    unidade: 'por 1.000 dias', casas: 2, nome: (k) => NOME_CLASSE[k.replace('taxa_', '') as keyof typeof NOME_CLASSE],
    extra: (p) => `${fmtInt(p.estatisticas as number)} estatísticas · ${fmtInt(p.extremos as number)} extremos · ${fmtInt(p.dias as number)} município-dias`,
  })
  return (
    <div className={`ed-grafico ed-grafico--baixo${carregando ? ' ed-atualizando' : ''}`}>
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={dados} margin={{ top: 8, right: 8, bottom: 0, left: 0 }} barGap={2} barCategoryGap="22%">
          <CartesianGrid {...GRADE} />
          <XAxis dataKey={chaveX} {...EIXO} interval={0} fontSize={11} />
          <YAxis {...EIXO} width={40} tickFormatter={(v: number) => fmt(v, v < 10 ? 1 : 0)} />
          <Tooltip content={dica} cursor={{ fill: 'rgb(0 0 0 / 5%)' }} />
          <Bar dataKey="taxa_estatisticas" fill={COR_CLASSE.estatisticas} radius={[3, 3, 0, 0]} isAnimationActive={false} />
          <Bar dataKey="taxa_extremos" fill={COR_CLASSE.extremos} radius={[3, 3, 0, 0]} isAnimationActive={false} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}

export function SecaoAnomalias({ anomalias, variavel, onVariavel, numero }: {
  anomalias: Recurso<Anomalias>
  variavel: IdAnomalia
  onVariavel: (v: IdAnomalia) => void
  numero: number
}) {
  const [aba, setAba] = useState<'ano' | 'estacao' | 'regiao'>('ano')
  const d = anomalias.dados
  const v = d?.variaveis.find((x) => x.variavel === variavel)
  const opcoes = (d?.variaveis ?? []).map((x) => [x.variavel, ROTULO_ANOMALIA[x.variavel]] as const)

  if (anomalias.erro && !d) return <Estado tipo="erro">Não foi possível carregar as anomalias: {anomalias.erro}</Estado>
  if (!d) return <Estado tipo="carregando" altura={360}>Carregando anomalias</Estado>
  if (!v) return <Estado tipo="vazio">Sem anomalias desta variável no snapshot.</Estado>

  const dadosAba = aba === 'ano'
    ? v.por_ano.map((p) => ({ ...p, x: String(p.ano) }))
    : aba === 'estacao'
      ? v.por_estacao.map((p) => ({ ...p, x: NOMES_ESTACAO[p.estacao] }))
      : v.por_regiao.map((p) => ({ ...p, x: p.regiao }))

  return (
    <>
      <div className="est-definicoes">
        <div>
          <p className="est-definicoes__rotulo" style={{ color: COR_CLASSE.estatisticas }}>■ Anomalia estatística</p>
          <p>O valor observado fugiu da previsão do modelo para aquele dia: resíduo com |Z| &gt; 3. O valor em si pode ser
            comum para o lugar; o que é incomum é ter ocorrido naquele dia.</p>
        </div>
        <div>
          <p className="est-definicoes__rotulo" style={{ color: COR_CLASSE.extremos }}>■ Evento extremo (local)</p>
          <p>Anomalia cujo valor também é raro para o município e a época (acima do percentil da climatologia local).
            Não é sinônimo de desastre: o impacto só é afirmado quando há notícia verificada.</p>
        </div>
      </div>

      <div className="ed-controles">
        <Segmentos rotulo="Variável da anomalia" valor={variavel} onChange={onVariavel} opcoes={opcoes} />
      </div>

      <dl className={`ed-kpis est-anom-totais${anomalias.carregando ? ' ed-atualizando' : ''}`}>
        <div className="ed-kpi">
          <dt className="ed-kpi__rotulo">Todas as anomalias válidas</dt>
          <dd className="ed-kpi__valor">{fmtInt(v.totais.todas.eventos)}<small>eventos</small></dd>
          <dd className="ed-kpi__criterio">{fmt(v.totais.todas.taxa, 2)} por 1.000 município-dias · {fmtInt(v.dias_validos)} município-dias válidos</dd>
        </div>
        <div className="ed-kpi">
          <dt className="ed-kpi__rotulo" style={{ color: COR_CLASSE.estatisticas }}>Anomalias estatísticas</dt>
          <dd className="ed-kpi__valor">{fmtInt(v.totais.estatisticas.eventos)}<small>eventos</small></dd>
          <dd className="ed-kpi__criterio">{fmt(v.totais.estatisticas.taxa, 2)} por 1.000 município-dias</dd>
        </div>
        <div className="ed-kpi">
          <dt className="ed-kpi__rotulo" style={{ color: COR_CLASSE.extremos }}>Extremos locais</dt>
          <dd className="ed-kpi__valor">{fmtInt(v.totais.extremos.eventos)}<small>eventos</small></dd>
          <dd className="ed-kpi__criterio">{fmt(v.totais.extremos.taxa, 2)} por 1.000 município-dias</dd>
        </div>
      </dl>
      <p className="ed-kpi__criterio" style={{ margin: '8px 0 24px' }}>
        {d.definicao} Período pontuado: {d.recorte.inicio}–{d.recorte.fim} (os anos anteriores a {d.inicio_pontuado} só treinam os modelos).
      </p>

      <div className="ed-grade est-anom-grade">
        <Figura
          numero={numero}
          titulo={`Frequência de eventos — ${v.rotulo}`}
          unidade="Eventos por 1.000 município-dias válidos"
          controles={<Segmentos rotulo="Agrupar por" valor={aba} onChange={setAba}
            opcoes={[['ano', 'Ano'], ['estacao', 'Estação'], ['regiao', 'Região']]} />}
          legenda="A taxa divide os eventos pelos dias com dado válido, por isso grupos de tamanhos diferentes (estações, regiões) são comparáveis. As duas classes são contadas separadamente."
        >
          <ul className="ed-legenda">
            <ItemLegenda cor={COR_CLASSE.estatisticas} texto="Anomalia estatística" />
            <ItemLegenda cor={COR_CLASSE.extremos} texto="Extremo local" />
          </ul>
          <Barras dados={dadosAba} chaveX="x" carregando={anomalias.carregando} />
        </Figura>
        <div>
          <h3 className="ed-figura__titulo" style={{ marginBottom: 12 }}>Municípios com maior frequência</h3>
          {v.ranking.length
            ? (
              <div className="ed-tabela-wrap">
                <table className="ed-tabela">
                  <caption>{v.rotulo}: todas as anomalias, municípios com ≥ {d.min_eventos_ranking} eventos</caption>
                  <thead><tr><th>Município</th><th>Eventos</th><th>Por 1.000 dias</th></tr></thead>
                  <tbody>
                    {v.ranking.map((m, i) => (
                      <tr key={m.codigo_ibge}>
                        <td>{i + 1}. {m.municipio} — {m.uf}</td>
                        <td>{fmtInt(m.eventos)}</td>
                        <td>{fmt(m.taxa, 2)}</td>
                      </tr>
                    ))}
                  </tbody>
                  <tfoot><tr><td colSpan={3}>Frequência alta indica muitos dias fora do esperado pelo modelo local, não necessariamente clima mais severo.</td></tr></tfoot>
                </table>
              </div>
            )
            : <Estado tipo="vazio">Nenhum município com ao menos {d.min_eventos_ranking} eventos no recorte.</Estado>}
        </div>
      </div>
    </>
  )
}
