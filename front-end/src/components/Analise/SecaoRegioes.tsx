import { Bar, BarChart, CartesianGrid, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import type { Definicoes, FiltrosAnalise, Padrao, Regioes } from '../../data/analise'
import { NOMES_ESTACAO, ORDEM_ESTACOES } from '../../data/seasons'
import { COR_ESTACAO, COR_SEM_PREDOMINIO, HACHURA_CSS, ROTULO_PADRAO } from './cores'
import { formatarQ, pct } from './formatos'

const ORDEM_REGIOES = ['Norte', 'Nordeste', 'Centro-Oeste', 'Sudeste', 'Sul', 'Brasil']
const PADROES: Padrao[] = [
  'predominio_verao', 'predominio_outono', 'predominio_inverno', 'predominio_primavera', 'sem_predominio', 'insuficiente',
]
const corPadrao = (p: Padrao) =>
  p === 'insuficiente' ? HACHURA_CSS : p === 'sem_predominio' ? COR_SEM_PREDOMINIO : COR_ESTACAO[p.replace('predominio_', '') as keyof typeof COR_ESTACAO]

interface Props {
  dados: Regioes | null
  carregando: boolean
  erro: string | null
  definicoes: Definicoes | null
  filtros: FiltrosAnalise
  onVerPortoAlegre: () => void
}

export function SecaoRegioes({ dados, carregando, erro, definicoes, filtros, onVerPortoAlegre }: Props) {
  const termico = filtros.variable !== 'precipitacao'
  const classes = termico ? definicoes?.thermal_classes : definicoes?.precipitation_classes
  const estatistica = classes?.anomalia_estatistica
  const extremos = classes ? Object.values(classes).filter((c) => c.is_extreme && c.counted) : []

  const linhas = ORDEM_REGIOES.map((regiao) => {
    const daRegiao = dados?.pooled.filter((p) => p.regiao === regiao) ?? []
    const linha: Record<string, string | number | null> = { regiao }
    for (const e of ORDEM_ESTACOES) {
      const v = daRegiao.find((p) => p.season === e)?.share_norm
      linha[e] = v === null || v === undefined ? null : +(100 * v).toFixed(1)
      linha[`bruto_${e}`] = v ?? null
    }
    const o = daRegiao.find((p) => p.season === 'outono')?.share_norm
    const i = daRegiao.find((p) => p.season === 'inverno')?.share_norm
    linha.outono_inverno = o === undefined || i === undefined || o === null || i === null ? null : o + i
    linha.eventos = daRegiao.reduce((soma, p) => soma + p.n, 0)
    return linha
  }).filter((l) => (l.eventos as number) > 0)

  const moran = dados?.moran_autumn_winter

  return (
    <section className="regioes-analise" id="distribuicao-regional" aria-labelledby="regioes-titulo">
      <div className="regioes-analise__cabecalho">
        <div>
          <p className="mono-label">Distribuição sazonal no Brasil</p>
          <h2 id="regioes-titulo" className="section-title">Como a sazonalidade dos eventos se distribui pelos municípios?</h2>
          <p className="regioes-analise__pergunta">
            Pergunta da avaliação: <q>O caso de POA indica majoritariamente outono/inverno. Como isso se distribui nos
            outros municípios?</q> Os dados abaixo vêm diretamente da API, com os filtros escolhidos no mapa.
          </p>
        </div>
        <button type="button" className="btn btn--primary" onClick={onVerPortoAlegre}>
          Ver Porto Alegre no mapa (outono + inverno)
        </button>
      </div>

      <div className="regioes-analise__explicacao card">
        <ul>
          <li><b>Frequências normalizadas.</b> Cada estação é medida como eventos ÷ dias com dado válido naquela estação; a
            participação é essa taxa dividida pela soma das taxas das quatro estações. Sem preferência sazonal, cada estação
            teria 25% (outono + inverno, 50%).</li>
          <li><b>Eventos, não dias.</b> Dias anômalos consecutivos contam como um único evento.</li>
          <li>
            <b>Anomalia estatística ≠ evento extremo.</b>{' '}
            {estatistica ? <>{estatistica.label}: {estatistica.definition}</> : 'Carregando definições…'}
            {extremos.length > 0 && <> Extremos: {extremos.map((c) => `${c.label} (${c.definition})`).join(' ')}</>}
            {' '}Use o filtro “Classe” acima para separar as duas.
          </li>
          <li>Os agregados abaixo usam os mesmos filtros de variável, classe, período e fase ENSO do mapa (sem recorte de estação).</li>
        </ul>
      </div>

      {erro && <p role="alert" className="filter-error">{erro}</p>}
      {carregando && !dados && <div className="loading-skeleton loading-skeleton--chart" />}
      {dados && (
        <div className={carregando ? 'regioes-analise__grade is-desatualizada' : 'regioes-analise__grade'}>
          <div className="card chart-card">
            <div className="chart-card__head">
              <div>
                <h3>Participação normalizada por região</h3>
                <p>Eventos agregados de todos os municípios de cada região (Σ eventos ÷ Σ dias válidos por estação).</p>
              </div>
            </div>
            <div className="regioes-analise__grafico">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={linhas} margin={{ top: 10, right: 34, bottom: 0, left: -8 }} barCategoryGap="16%" barGap={2}>
                  <CartesianGrid vertical={false} stroke="#e0e8e5" />
                  <XAxis dataKey="regiao" tick={{ fontSize: 14, fill: '#5c7370' }} axisLine={{ stroke: '#cfdad6' }} tickLine={false} />
                  <YAxis unit="%" tick={{ fontSize: 13, fill: '#5c7370' }} axisLine={false} tickLine={false} />
                  <Tooltip
                    formatter={(v, chave) => [v === null || v === undefined ? '—' : `${String(v).replace('.', ',')}%`, NOMES_ESTACAO[chave as keyof typeof NOMES_ESTACAO] ?? String(chave)]}
                    cursor={{ fill: 'rgb(15 47 45 / 5%)' }}
                    itemStyle={{ color: '#0f2f2d' }}
                    itemSorter={(item) => ORDEM_ESTACOES.indexOf(item.dataKey as (typeof ORDEM_ESTACOES)[number])}
                  />
                  <ReferenceLine y={25} stroke="#0f2f2d" strokeDasharray="4 4" label={{ value: '25%', position: 'right', fontSize: 12, fill: '#5c7370' }} />
                  {ORDEM_ESTACOES.map((e) => (
                    <Bar key={e} dataKey={e} fill={COR_ESTACAO[e]} radius={[3, 3, 0, 0]} isAnimationActive={false} />
                  ))}
                </BarChart>
              </ResponsiveContainer>
            </div>
            <ul className="legenda-series">
              {ORDEM_ESTACOES.map((e) => <li key={e}><i style={{ background: COR_ESTACAO[e] }} />{NOMES_ESTACAO[e]}</li>)}
              <li><i className="legenda-series__linha" />25% = sem preferência</li>
            </ul>
            <div className="tabela-rolagem">
              <table className="tabela-analise">
                <thead>
                  <tr><th>Região</th>{ORDEM_ESTACOES.map((e) => <th key={e}>{NOMES_ESTACAO[e]}</th>)}<th>Outono + inverno</th><th>Eventos</th></tr>
                </thead>
                <tbody>
                  {linhas.map((l) => (
                    <tr key={l.regiao as string}>
                      <th scope="row">{l.regiao}</th>
                      {ORDEM_ESTACOES.map((e) => <td key={e}>{pct(l[`bruto_${e}`] as number | null)}</td>)}
                      <td><b>{pct(l.outono_inverno as number | null)}</b></td>
                      <td>{(l.eventos as number).toLocaleString('pt-BR')}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          <div className="card chart-card">
            <div className="chart-card__head">
              <div>
                <h3>Padrão sazonal dos municípios</h3>
                <p>Quantos municípios têm predomínio estatisticamente significativo de cada estação (χ², FDR q &lt; 0,05).</p>
              </div>
            </div>
            <div className="tabela-rolagem">
              <table className="tabela-analise tabela-analise--padroes">
                <thead>
                  <tr>
                    <th>Região</th>
                    {PADROES.map((p) => <th key={p}><i className="amostra" style={{ background: corPadrao(p) }} />{ROTULO_PADRAO[p]}</th>)}
                  </tr>
                </thead>
                <tbody>
                  {ORDEM_REGIOES.map((regiao) => {
                    const daRegiao = dados.patterns.filter((p) => p.regiao === regiao)
                    if (!daRegiao.length) return null
                    return (
                      <tr key={regiao}>
                        <th scope="row">{regiao}</th>
                        {PADROES.map((p) => {
                          const c = daRegiao.find((x) => x.pattern === p)
                          return <td key={p}>{c ? <>{c.municipalities.toLocaleString('pt-BR')} <small>({pct(c.share, 0)})</small></> : '0'}</td>
                        })}
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>
            {moran && moran.I !== null && (
              <p className="painel-municipio__nota">
                Autocorrelação espacial da participação de outono + inverno (I de Moran, 8 vizinhos mais próximos):
                I = {moran.I.toLocaleString('pt-BR')}; p = {formatarQ(moran.p_value)}
                {moran.permutations ? ` (${moran.permutations} permutações)` : ''}; n = {moran.n.toLocaleString('pt-BR')} municípios
                com pelo menos {definicoes?.min_events ?? 20} eventos.
              </p>
            )}
          </div>
        </div>
      )}
    </section>
  )
}
