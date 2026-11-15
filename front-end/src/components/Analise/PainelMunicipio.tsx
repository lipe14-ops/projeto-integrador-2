import { Bar, BarChart, CartesianGrid, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import type { AnaliseMunicipio, Coropletico, Definicoes, LinhaSazonal, ValorMunicipio } from '../../data/analise'
import { NOMES_ESTACAO, ORDEM_ESTACOES, type Estacao } from '../../data/seasons'
import { ROTULO_PADRAO } from './cores'
import { dec, descreverValor, formatarQ, pct, ROTULO_STATUS } from './formatos'

// município → UF → região → Brasil: do mais local (escuro) ao mais amplo (cinza)
const SERIES = [
  { chave: 'municipio', cor: '#0d366b' },
  { chave: 'estado', cor: '#3987e5' },
  { chave: 'regiao', cor: '#9ec5f4' },
  { chave: 'brasil', cor: '#b9b8b2' },
] as const

interface Props {
  codigo: string
  nome: string | null
  analise: AnaliseMunicipio | null
  carregando: boolean
  erro: string | null
  valorMapa: ValorMunicipio | undefined
  dados: Coropletico | null
  definicoes: Definicoes | null
  onFechar: () => void
}

const porEstacao = (linhas: LinhaSazonal[]) => new Map(linhas.map((l) => [l.season, l]))
const emPct = (v: number | null | undefined) => (v === null || v === undefined ? null : +(100 * v).toFixed(1))

export function PainelMunicipio({ codigo, nome, analise, carregando, erro, valorMapa, dados, definicoes, onFechar }: Props) {
  const titulo = analise ? `${analise.nome} — ${analise.uf}` : nome ?? `Município ${codigo}`
  return (
    <aside className="card painel-municipio" aria-label={`Análise de ${titulo}`}>
      <div className="painel-municipio__topo">
        <div>
          <p className="mono-label">Município selecionado</p>
          <h2>{titulo}</h2>
          {analise && <p className="painel-municipio__sub">Região {analise.regiao} · IBGE {analise.codigo_ibge}</p>}
        </div>
        <button type="button" className="painel-municipio__fechar" aria-label="Fechar painel" onClick={onFechar}>×</button>
      </div>

      {dados && (
        <div className="painel-municipio__valor">
          <span>{dados.label} no mapa</span>
          <b>{valorMapa ? descreverValor(valorMapa, dados) : 'sem detecção / sem dados'}</b>
          {valorMapa && <small>{valorMapa.n.toLocaleString('pt-BR')} eventos · {valorMapa.days.toLocaleString('pt-BR')} dias válidos · {ROTULO_STATUS[valorMapa.status]}</small>}
        </div>
      )}

      {carregando && <p className="loading-message"><span className="loading-spinner" />Carregando distribuição sazonal…</p>}
      {erro && <p role="alert" className="filter-error">{erro}</p>}
      {analise && !carregando && <Conteudo analise={analise} definicoes={definicoes} />}
    </aside>
  )
}

function Conteudo({ analise, definicoes }: { analise: AnaliseMunicipio; definicoes: Definicoes | null }) {
  if (!analise.has_detection) {
    return <p className="painel-municipio__vazio">Nenhum evento detectado para este município com os filtros atuais.</p>
  }
  const proprio = porEstacao(analise.seasons)
  const est = porEstacao(analise.comparison.estado)
  const reg = porEstacao(analise.comparison.regiao)
  const br = porEstacao(analise.comparison.brasil)
  const linhas = ORDEM_ESTACOES.map((e) => ({
    estacao: NOMES_ESTACAO[e],
    municipio: emPct(proprio.get(e)?.share_norm),
    estado: emPct(est.get(e)?.share_norm),
    regiao: emPct(reg.get(e)?.share_norm),
    brasil: emPct(br.get(e)?.share_norm),
  }))
  const nomes: Record<(typeof SERIES)[number]['chave'], string> = {
    municipio: analise.nome, estado: analise.uf, regiao: analise.regiao, brasil: 'Brasil',
  }
  const s = analise.summary
  const minEventos = definicoes?.min_events ?? 20
  const anos = Object.entries(analise.events_by_year)

  return (
    <>
      <div className="painel-municipio__bloco">
        <h3>Participação normalizada por estação</h3>
        <p className="painel-municipio__nota">
          Taxa de cada estação (eventos ÷ dias válidos) dividida pela soma das 4 taxas. A linha tracejada marca 25%
          (sem preferência sazonal).
        </p>
        <div className="painel-municipio__grafico">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={linhas} margin={{ top: 8, right: 30, bottom: 0, left: -12 }} barCategoryGap="18%" barGap={2}>
              <CartesianGrid vertical={false} stroke="#e0e8e5" />
              <XAxis dataKey="estacao" tick={{ fontSize: 13, fill: '#5c7370' }} axisLine={{ stroke: '#cfdad6' }} tickLine={false} />
              <YAxis unit="%" tick={{ fontSize: 12, fill: '#5c7370' }} axisLine={false} tickLine={false} domain={[0, 'auto']} />
              <Tooltip
                formatter={(v, chave) => [v === null || v === undefined ? '—' : `${String(v).replace('.', ',')}%`, nomes[chave as keyof typeof nomes] ?? String(chave)]}
                cursor={{ fill: 'rgb(15 47 45 / 5%)' }}
                itemStyle={{ color: '#0f2f2d' }}
                itemSorter={(item) => SERIES.findIndex((x) => x.chave === item.dataKey)}
              />
              <ReferenceLine y={25} stroke="#0f2f2d" strokeDasharray="4 4" label={{ value: '25%', position: 'right', fontSize: 11, fill: '#5c7370' }} />
              {SERIES.map((serie) => (
                <Bar key={serie.chave} dataKey={serie.chave} fill={serie.cor} radius={[3, 3, 0, 0]} isAnimationActive={false} />
              ))}
            </BarChart>
          </ResponsiveContainer>
        </div>
        <ul className="legenda-series">
          {SERIES.map((serie) => <li key={serie.chave}><i style={{ background: serie.cor }} />{nomes[serie.chave]}</li>)}
        </ul>
      </div>

      {s && (
        <div className="painel-municipio__bloco">
          <h3>Padrão sazonal</h3>
          <dl className="painel-municipio__resumo">
            <div><dt>Resultado</dt><dd>{ROTULO_PADRAO[s.pattern]}</dd></div>
            <div><dt>Eventos</dt><dd>{s.n_events.toLocaleString('pt-BR')}</dd></div>
            <div><dt>Estação de maior taxa</dt><dd>{s.dominant_season ? NOMES_ESTACAO[s.dominant_season] : '—'}</dd></div>
            <div><dt>Outono + inverno</dt><dd>{pct(s.autumn_winter_share)}</dd></div>
            <div><dt>Concentração (0–1)</dt><dd>{dec(s.concentration, 3)}</dd></div>
            <div><dt>Teste χ² (q-valor FDR)</dt><dd>{formatarQ(s.chi2_qvalue)}</dd></div>
          </dl>
          <p className="painel-municipio__nota">
            Qui-quadrado contra distribuição proporcional aos dias válidos de cada estação, com correção de
            Benjamini–Hochberg; predomínio só quando q &lt; 0,05 e houver pelo menos {minEventos} eventos.
          </p>
        </div>
      )}

      <div className="painel-municipio__bloco">
        <h3>Por estação</h3>
        <div className="tabela-rolagem">
          <table className="tabela-analise">
            <thead><tr><th>Estação</th><th>Eventos</th><th>Dias válidos</th><th>Taxa /1.000 dias</th><th>Part. bruta</th><th>Part. normalizada</th></tr></thead>
            <tbody>
              {ORDEM_ESTACOES.map((e) => {
                const l = analise.seasons.find((x) => x.season === e)
                return (
                  <tr key={e}>
                    <th scope="row">{NOMES_ESTACAO[e]}</th>
                    <td>{l?.n ?? '—'}</td><td>{l?.days.toLocaleString('pt-BR') ?? '—'}</td>
                    <td>{dec(l?.rate_per_1000)}</td><td>{pct(l?.share_abs)}</td><td>{pct(l?.share_norm)}</td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      </div>

      <TabelaEnso analise={analise} definicoes={definicoes} />

      {anos.length > 0 && (
        <div className="painel-municipio__bloco">
          <h3>Eventos por ano</h3>
          <ul className="painel-municipio__anos">
            {anos.map(([ano, n]) => <li key={ano}><span>{ano}</span><b>{n}</b></li>)}
          </ul>
        </div>
      )}
    </>
  )
}

function TabelaEnso({ analise, definicoes }: { analise: AnaliseMunicipio; definicoes: Definicoes | null }) {
  if (!analise.enso.length) return null
  const fases = ['el_nino', 'la_nina', 'neutro'] as const
  const linha = (e: Estacao, f: (typeof fases)[number]) => analise.enso.find((x) => x.season === e && x.enso_phase === f)
  return (
    <div className="painel-municipio__bloco">
      <h3>ENSO por estação</h3>
      <p className="painel-municipio__nota">
        Razão entre a taxa na fase e a taxa nos meses neutros da mesma estação, com intervalo de confiança de 95%.
        Intervalos que incluem 1 não indicam diferença. {definicoes?.enso_rule}
      </p>
      <div className="tabela-rolagem">
        <table className="tabela-analise">
          <thead>
            <tr><th>Estação</th><th>Fase</th><th>Eventos</th><th>Dias</th><th>Taxa /1.000</th><th>Razão vs. neutro</th><th>IC 95%</th></tr>
          </thead>
          <tbody>
            {ORDEM_ESTACOES.flatMap((e) => fases.map((f, i) => {
              const l = linha(e, f)
              if (!l) return null
              return (
                <tr key={`${e}-${f}`} className={i === 0 ? 'inicio-grupo' : undefined}>
                  <th scope="row">{i === 0 ? NOMES_ESTACAO[e] : ''}</th>
                  <td>{definicoes?.enso_phases[f] ?? f}</td>
                  <td>{l.n}</td><td>{l.days.toLocaleString('pt-BR')}</td><td>{dec(l.rate_per_1000)}</td>
                  <td>{f === 'neutro' ? 'referência' : dec(l.ratio_vs_neutral)}</td>
                  <td>{f === 'neutro' || l.ratio_ci_low === null ? '—' : `${dec(l.ratio_ci_low)} – ${dec(l.ratio_ci_high)}`}</td>
                </tr>
              )
            }))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
