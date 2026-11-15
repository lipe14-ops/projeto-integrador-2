import { useState } from 'react'
import { Bar, BarChart, CartesianGrid, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { Estado, Figura, ItemLegenda, Segmentos } from '../Editorial/Editorial'
import { type Recurso } from '../Editorial/useRecurso'
import {
  casasDe, COR_FASE, fmt, fmtSinal, FASES, NOME_FASE, NOME_VARIAVEL, REGIOES, UNIDADE,
  type Enso, type FaseEnso, type LinhaEnso, type Regiao, type VariavelClima,
} from '../../data/estatisticas'
import { NOMES_ESTACAO, ORDEM_ESTACOES } from '../../data/seasons'
import { EIXO, GRADE } from './graficos'

type Escopo = 'Brasil' | Regiao

export function SecaoEnso({ enso, numero, regiaoFiltro, ensoFiltro }: { enso: Recurso<Enso>; numero: number; regiaoFiltro: Regiao | null; ensoFiltro: FaseEnso | null }) {
  const [variavel, setVariavel] = useState<VariavelClima>('precipitacao')
  const [escolhido, setEscopo] = useState<Escopo | null>(null)
  const escopo: Escopo = escolhido ?? regiaoFiltro ?? 'Brasil'
  const d = enso.dados
  const casas = variavel === 'precipitacao' ? 1 : 2
  const unidade = `${UNIDADE[variavel].replace('/mês', '/mês')}`

  const linhas = d?.linhas.filter((l) => l.escopo === escopo) ?? []
  const grupos = (['todas', ...ORDEM_ESTACOES] as const).map((est) => {
    const linha: Record<string, unknown> = { x: est === 'todas' ? 'Ano todo' : NOMES_ESTACAO[est] }
    for (const f of FASES) {
      const l = linhas.find((q) => q.estacao === est && q.fase === f)
      linha[f] = l?.[variavel] ?? null
      linha[`${f}_meses`] = l?.meses ?? 0
      linha[`${f}_pct`] = l?.precipitacao_pct ?? null
    }
    return linha
  })

  return (
    <>
      <div className="ed-controles">
        <Segmentos rotulo="Variável" valor={variavel} onChange={setVariavel}
          opcoes={[['precipitacao', 'Precipitação'], ['temperatura', 'Temperatura'], ['umidade', 'Umidade']]} />
        <label className="ed-campo">
          <span>Recorte espacial</span>
          <select value={escopo} onChange={(e) => setEscopo(e.target.value as Escopo)}>
            <option value="Brasil">Brasil</option>
            {REGIOES.map((r) => <option key={r} value={r}>{r}</option>)}
          </select>
        </label>
      </div>
      <div className="ed-grade est-enso-grade">
        <Figura
          numero={numero}
          titulo={`Anomalia média por fase do ENSO — ${NOME_VARIAVEL[variavel]} (${escopo})`}
          unidade={`Unidade: ${unidade} de diferença para a média do mesmo mês do calendário (2015–2025)`}
          legenda={<>{d?.metodo} {ensoFiltro && 'Esta seção compara as três fases; o filtro de fase ENSO não se aplica. '}Com poucos episódios em 11 anos, diferenças pequenas podem ser acaso.</>}
        >
          <ul className="ed-legenda">
            {FASES.map((f) => <ItemLegenda key={f} cor={COR_FASE[f]} texto={`${NOME_FASE[f]}${d ? ` (${d.meses_por_fase[f]} meses)` : ''}`} />)}
          </ul>
          {enso.erro && !d ? <Estado tipo="erro" altura={280}>{enso.erro}</Estado>
            : !d ? <Estado tipo="carregando" altura={280} />
              : (
                <div className={`ed-grafico ed-grafico--medio${enso.carregando ? ' ed-atualizando' : ''}`}>
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={grupos} margin={{ top: 8, right: 8, bottom: 0, left: 0 }} barGap={2} barCategoryGap="20%">
                      <CartesianGrid {...GRADE} />
                      <XAxis dataKey="x" {...EIXO} interval={0} />
                      <YAxis {...EIXO} width={44} tickFormatter={(v: number) => fmt(v, variavel === 'precipitacao' ? 0 : 1)} />
                      <ReferenceLine y={0} stroke="#141414" strokeWidth={1} />
                      <Tooltip
                        cursor={{ fill: 'rgb(0 0 0 / 5%)' }}
                        content={({ active, payload, label }) => {
                          if (!active || !payload?.length) return null
                          const p = payload[0].payload as Record<string, number | null>
                          return (
                            <div className="ed-tooltip">
                              <div className="ed-tooltip__titulo">{String(label)}</div>
                              {FASES.map((f) => (
                                <div key={f} className="ed-tooltip__linha">
                                  <span><i style={{ background: COR_FASE[f] }} />{NOME_FASE[f]} ({p[`${f}_meses`]} meses)</span>
                                  <b>{fmtSinal(p[f], casas)} {unidade}{variavel === 'precipitacao' && p[`${f}_pct`] !== null ? ` (${fmtSinal(p[`${f}_pct`], 0)}%)` : ''}</b>
                                </div>
                              ))}
                            </div>
                          )
                        }}
                      />
                      {FASES.map((f) => <Bar key={f} dataKey={f} fill={COR_FASE[f]} isAnimationActive={false} radius={2} />)}
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              )}
        </Figura>
        <div>
          <h3 className="ed-figura__titulo" style={{ marginBottom: 12 }}>El Niño × La Niña nas regiões (ano todo)</h3>
          {d ? <TabelaRegioes linhas={d.linhas} variavel={variavel} /> : <Estado tipo="carregando" altura={220} />}
          <p className="ed-nota">
            <b>Associação não é causalidade.</b> As fases coincidem com outros fatores (tendência de aquecimento,
            variabilidade do Atlântico, eventos isolados como a enchente de 2024 no Sul). Os valores mostram como o clima
            se comportou nos meses de cada fase, não o efeito isolado do ENSO.
          </p>
        </div>
      </div>
    </>
  )
}

function TabelaRegioes({ linhas, variavel }: { linhas: LinhaEnso[]; variavel: VariavelClima }) {
  const casas = casasDe(variavel) + 1
  const valor = (escopo: string, fase: FaseEnso) => linhas.find((l) => l.escopo === escopo && l.estacao === 'todas' && l.fase === fase)
  return (
    <div className="ed-tabela-wrap">
      <table className="ed-tabela">
        <caption>{NOME_VARIAVEL[variavel]}: anomalia média ({UNIDADE[variavel]}){variavel === 'precipitacao' ? ' e % da climatologia' : ''}</caption>
        <thead><tr><th>Recorte</th><th style={{ color: COR_FASE.el_nino }}>El Niño</th><th style={{ color: COR_FASE.la_nina }}>La Niña</th><th>Neutro</th></tr></thead>
        <tbody>
          {(['Brasil', ...REGIOES] as const).map((e) => (
            <tr key={e}>
              <td>{e === 'Brasil' ? <b>Brasil</b> : e}</td>
              {FASES.map((f) => {
                const l = valor(e, f)
                return (
                  <td key={f}>
                    {fmtSinal(l?.[variavel], casas)}
                    {variavel === 'precipitacao' && l?.precipitacao_pct !== null && l?.precipitacao_pct !== undefined && <span className="est-delta"> ({fmtSinal(l.precipitacao_pct, 0)}%)</span>}
                  </td>
                )
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
