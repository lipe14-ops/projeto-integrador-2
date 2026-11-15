import { useEffect, useState } from 'react'
import { Bar, BarChart, CartesianGrid, ErrorBar, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { carregarNoticiasIntensidade, type NoticiasIntensidade, type Proporcao } from '../../data/analise'

const num = (v: number) => v.toLocaleString('pt-BR')
const pctTexto = (p: Proporcao) => (p.pct === null ? '—' : `${p.pct.toLocaleString('pt-BR')}%`)
const ic = (p: Proporcao) =>
  p.ci_low === null || p.ci_high === null
    ? ''
    : `${p.ci_low.toLocaleString('pt-BR')}–${p.ci_high.toLocaleString('pt-BR')}%`

/** Eventos de chuva com notícia verificada, por intensidade (dados da API /analysis/noticias-intensidade). */
export function SecaoNoticias() {
  const [dados, setDados] = useState<NoticiasIntensidade | null>(null)
  const [erro, setErro] = useState<string | null>(null)

  useEffect(() => {
    let ativo = true
    carregarNoticiasIntensidade()
      .then((d) => { if (ativo) setDados(d) })
      .catch((e: Error) => { if (ativo) setErro(e.message) })
    return () => { ativo = false }
  }, [])

  const barras = (dados?.by_intensity_daily ?? []).map((b) => ({
    label: b.label,
    pct: b.pct,
    erro: b.pct === null || b.ci_low === null || b.ci_high === null ? [0, 0] : [b.pct - b.ci_low, b.ci_high - b.pct],
    n: b.n,
    com: b.with_news,
  }))

  return (
    <section className="regioes-analise" id="noticias-intensidade" aria-labelledby="noticias-titulo">
      <div className="regioes-analise__cabecalho">
        <div>
          <p className="mono-label">Eventos e notícias</p>
          <h2 id="noticias-titulo" className="section-title">As notícias confirmam os eventos mais fortes?</h2>
          <p className="regioes-analise__pergunta">
            Proporção de eventos de chuva detectados que têm pelo menos uma notícia da época, conferida na página
            original, por intensidade da chuva.
          </p>
        </div>
      </div>

      {erro && <p role="alert" className="filter-error">{erro}</p>}
      {!dados && !erro && <div className="loading-skeleton loading-skeleton--chart" />}

      {dados && (
        <div className="regioes-analise__grade">
          <div className="card chart-card">
            <div className="chart-card__head">
              <div>
                <h3>Eventos diários com notícia, por chuva do dia</h3>
                <p>
                  {num(dados.investigated_events)} eventos investigados em {num(dados.investigated_municipalities)}{' '}
                  municípios · barras: intervalo de confiança de 95%
                </p>
              </div>
            </div>
            <div className="regioes-analise__grafico">
              <ResponsiveContainer width="100%" height={280}>
                <BarChart data={barras} margin={{ top: 12, right: 12, bottom: 4, left: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="var(--color-border, #e4e3df)" />
                  <XAxis dataKey="label" tick={{ fontSize: 12 }} />
                  <YAxis unit="%" tick={{ fontSize: 12 }} domain={[0, 'auto']} width={44} />
                  <Tooltip
                    formatter={(v, _n, item) => [
                      `${String(v).replace('.', ',')}% (${num(item.payload.com)} de ${num(item.payload.n)})`,
                      'com notícia',
                    ]}
                  />
                  <Bar dataKey="pct" fill="#2a78d6" radius={[4, 4, 0, 0]} isAnimationActive={false}>
                    <ErrorBar dataKey="erro" width={6} strokeWidth={1.5} stroke="#52514e" />
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>

          <div className="card chart-card">
            <div className="chart-card__head">
              <div>
                <h3>Por tipo de evento</h3>
                <p>Classes definidas pela climatologia de cada município</p>
              </div>
            </div>
            <div className="tabela-rolagem">
              <table className="tabela-analise">
                <thead>
                  <tr><th>Tipo</th><th>Eventos</th><th>Com notícia</th><th>IC 95%</th></tr>
                </thead>
                <tbody>
                  {dados.by_class.map((c) => (
                    <tr key={c.event_class}>
                      <td>{c.label}</td><td>{num(c.n)}</td><td>{pctTexto(c)}</td><td>{ic(c)}</td>
                    </tr>
                  ))}
                  <tr>
                    <td>Intensidade alta ({dados.definitions.high_intensity})</td>
                    <td>{num(dados.by_high_intensity.alta.n)}</td>
                    <td>{pctTexto(dados.by_high_intensity.alta)}</td>
                    <td>{ic(dados.by_high_intensity.alta)}</td>
                  </tr>
                  <tr>
                    <td>Demais eventos</td>
                    <td>{num(dados.by_high_intensity.demais.n)}</td>
                    <td>{pctTexto(dados.by_high_intensity.demais)}</td>
                    <td>{ic(dados.by_high_intensity.demais)}</td>
                  </tr>
                </tbody>
              </table>
            </div>
            <ul className="regioes-analise__ressalvas">
              {dados.caveats.map((c) => <li key={c}>{c}</li>)}
            </ul>
          </div>
        </div>
      )}
    </section>
  )
}
