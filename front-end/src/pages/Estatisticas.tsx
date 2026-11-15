// Estatísticas gerais: panorama climático nacional, construído como uma
// narrativa (indicadores → tempo → estações → anomalias → espaço → regiões → ENSO).
// Todas as agregações vêm de /api/estatisticas; os filtros globais valem para
// todas as seções (com as exceções explicadas em cada legenda).
import { useState } from 'react'
import { Bloco, Estado } from '../components/Editorial/Editorial'
import { useRecurso } from '../components/Editorial/useRecurso'
import { SecaoAnomalias } from '../components/Estatisticas/SecaoAnomalias'
import { SecaoEnso } from '../components/Estatisticas/SecaoEnso'
import { SecaoMapa } from '../components/Estatisticas/SecaoMapa'
import { SecaoRegional } from '../components/Estatisticas/SecaoRegional'
import { SecaoSazonal } from '../components/Estatisticas/SecaoSazonal'
import { SecaoTemporal } from '../components/Estatisticas/SecaoTemporal'
import type { Pagina } from '../components/Header/Header'
import {
  carregarAnomalias, carregarEnso, carregarRegioes, carregarResumo, carregarSazonal, carregarSerie,
  fmt, fmtInt, fmtSinal, MESES_CURTOS, NOME_FASE, RECORTE_PADRAO, REGIOES,
  ROTULO_ANOMALIA, type ExtremoMensal, type FaseEnso, type IdAnomalia, type Indicador, type Recorte, type Regiao,
} from '../data/estatisticas'
import { NOMES_ESTACAO, ORDEM_ESTACOES, type Estacao } from '../data/seasons'
import { Rodape } from './Inicio'
import '../styles/editorial.css'
import './Inicio.css'
import './Estatisticas.css'

const ANOS = Array.from({ length: 11 }, (_, i) => 2015 + i)

export default function Estatisticas({ onNavegar, visivel = true }: { onNavegar: (p: Pagina) => void; visivel?: boolean }) {
  const [recorte, setRecorte] = useState<Recorte>(RECORTE_PADRAO)
  const [varAnomalia, setVarAnomalia] = useState<IdAnomalia>('precipitacao')
  const chave = JSON.stringify(recorte)

  const resumo = useRecurso(chave, (s) => carregarResumo(recorte, s))
  const serie = useRecurso(JSON.stringify([recorte.inicio, recorte.fim, recorte.regiao, recorte.estacao, recorte.enso]), (s) => carregarSerie(recorte, s))
  const sazonal = useRecurso(JSON.stringify([recorte.inicio, recorte.fim, recorte.regiao, recorte.enso]), (s) => carregarSazonal({ ...recorte, estacao: null }, s))
  const regioes = useRecurso(JSON.stringify([recorte.inicio, recorte.fim, recorte.estacao, recorte.enso]), (s) => carregarRegioes({ ...recorte, regiao: null }, s))
  const enso = useRecurso(JSON.stringify([recorte.inicio, recorte.fim, recorte.estacao]), (s) => carregarEnso({ ...recorte, regiao: null, enso: null }, s))
  const anomalias = useRecurso(chave, (s) => carregarAnomalias(recorte, s))

  function alterar<K extends keyof Recorte>(campo: K, valor: Recorte[K]) {
    setRecorte((r) => {
      const novo = { ...r, [campo]: valor }
      if (campo === 'inicio' && novo.fim < (valor as number)) novo.fim = valor as number
      if (campo === 'fim' && novo.inicio > (valor as number)) novo.inicio = valor as number
      return novo
    })
  }

  const escopo = recorte.regiao ?? 'Brasil'
  const periodo = `${recorte.inicio}–${recorte.fim}`
  const filtrosTexto = [
    escopo, periodo,
    recorte.estacao ? NOMES_ESTACAO[recorte.estacao] : 'todas as estações',
    recorte.enso ? NOME_FASE[recorte.enso] : 'todas as fases ENSO',
  ]
  const alterado = chave !== JSON.stringify(RECORTE_PADRAO)
  const atualizacao = anomalias.dados?.atualizado_em.precipitation
  const r = resumo.dados
  const totalAnom = anomalias.dados?.variaveis.reduce((s, v) => s + v.totais.todas.eventos, 0)

  // escondida (outra página aberta): mantém filtros e dados em memória, mas não desenha
  // gráficos com 0 px de largura
  if (!visivel) return null

  return (
    <div className="ed estatisticas">
      <header className="ed-faixa">
        <div className="ed-container ed-faixa__inner">
          <div>
            <p className="ed-kicker">Panorama nacional</p>
            <h1>Estatísticas Gerais</h1>
            <p className="ed-faixa__sub">
              Os principais padrões de temperatura, chuva e umidade do Brasil — no tempo, nas estações, no território e
              nas fases do El Niño e da La Niña — calculados a partir de todos os municípios com dados.
            </p>
            <div className="ed-faixa__meta">
              <span>Período: <b>2015–2025</b> (mensal)</span>
              <span>Fonte: <b>ERA5-Land</b> · IBGE · NOAA/CPC</span>
              <span>Unidade espacial: <b>município</b>, agregado por área</span>
              {atualizacao && <span>Detecção de anomalias: <b>{new Date(atualizacao).toLocaleDateString('pt-BR')}</b></span>}
            </div>
          </div>
        </div>
      </header>

      {/* ---------- Filtros globais ---------- */}
      <div className="ed-filtros" role="region" aria-label="Filtros globais">
        <div className="ed-container ed-filtros__inner">
          <div className="ed-campo">
            <span>Período</span>
            <div className="ed-filtros__periodo">
              <select aria-label="Ano inicial" value={recorte.inicio} onChange={(e) => alterar('inicio', Number(e.target.value))}>
                {ANOS.map((a) => <option key={a} value={a}>{a}</option>)}
              </select>
              <span>a</span>
              <select aria-label="Ano final" value={recorte.fim} onChange={(e) => alterar('fim', Number(e.target.value))}>
                {ANOS.map((a) => <option key={a} value={a}>{a}</option>)}
              </select>
            </div>
          </div>
          <label className="ed-campo">
            <span>Região</span>
            <select value={recorte.regiao ?? ''} onChange={(e) => alterar('regiao', (e.target.value || null) as Regiao | null)}>
              <option value="">Brasil (todas)</option>
              {REGIOES.map((g) => <option key={g} value={g}>{g}</option>)}
            </select>
          </label>
          <label className="ed-campo">
            <span>Estação</span>
            <select value={recorte.estacao ?? ''} onChange={(e) => alterar('estacao', (e.target.value || null) as Estacao | null)}>
              <option value="">Todas</option>
              {ORDEM_ESTACOES.map((s) => <option key={s} value={s}>{NOMES_ESTACAO[s]}</option>)}
            </select>
          </label>
          <label className="ed-campo">
            <span>Fase ENSO</span>
            <select value={recorte.enso ?? ''} onChange={(e) => alterar('enso', (e.target.value || null) as FaseEnso | null)}>
              <option value="">Todas</option>
              {(['el_nino', 'la_nina', 'neutro'] as const).map((f) => <option key={f} value={f}>{NOME_FASE[f]}</option>)}
            </select>
          </label>
          {alterado && <button type="button" className="ed-link" onClick={() => setRecorte(RECORTE_PADRAO)}>Limpar filtros</button>}
          <p className="ed-filtros__resumo" aria-live="polite">
            {filtrosTexto.map((t, i) => <span key={i}>{i > 0 && ' · '}<b>{t}</b></span>)}
          </p>
        </div>
      </div>

      <div className="ed-container">
        {/* ---------- 1. Indicadores ---------- */}
        <Bloco id="indicadores" titulo="Indicadores principais"
          intro={<>Médias de {escopo === 'Brasil' ? 'todo o país' : `todos os municípios da região ${escopo}`} no recorte, <b>ponderadas pela área</b> de cada município — uma aproximação da média sobre o território.</>}>
          {resumo.erro && !r ? <Estado tipo="erro">Não foi possível calcular os indicadores: {resumo.erro}</Estado> : (
            <>
              <dl className={`ed-kpis${resumo.carregando ? ' ed-atualizando' : ''}`} aria-busy={resumo.carregando}>
                <Kpi rotulo="Temperatura média" ind={r?.indicadores.temperatura} casas={1} periodo={periodo} semComparacao={r && r.meses === r.meses_referencia && (recorte.inicio !== 2015 || recorte.fim !== 2025) ? 'o recorte já inclui todos os meses de 2015–2025 com esses filtros' : undefined} />
                <Kpi rotulo="Precipitação média" ind={r?.indicadores.precipitacao} casas={0} periodo={periodo} semComparacao={r && r.meses === r.meses_referencia && (recorte.inicio !== 2015 || recorte.fim !== 2025) ? 'o recorte já inclui todos os meses de 2015–2025 com esses filtros' : undefined}
                  extra={r?.indicadores.precipitacao.anual_equivalente ? `≈ ${fmtInt(r.indicadores.precipitacao.anual_equivalente)} mm/ano` : undefined} />
                <Kpi rotulo="Umidade relativa média" ind={r?.indicadores.umidade} casas={1} periodo={periodo} semComparacao={r && r.meses === r.meses_referencia && (recorte.inicio !== 2015 || recorte.fim !== 2025) ? 'o recorte já inclui todos os meses de 2015–2025 com esses filtros' : undefined} />
                <div className="ed-kpi">
                  <dt className="ed-kpi__rotulo">Municípios com dados</dt>
                  <dd className="ed-kpi__valor">{r ? fmtInt(r.municipios_com_dados) : <Pulso />}</dd>
                  <dd className="ed-kpi__comp">{r && `${r.meses} meses no recorte`}</dd>
                  <dd className="ed-kpi__criterio">{r && `De ${fmtInt(r.municipios_cadastrados)} na malha do IBGE; ilhas e áreas de lagoa ficam fora da grade do ERA5-Land.`}</dd>
                </div>
                <div className="ed-kpi">
                  <dt className="ed-kpi__rotulo">Anomalias identificadas</dt>
                  <dd className="ed-kpi__valor">{totalAnom !== undefined ? fmtInt(totalAnom) : anomalias.erro ? '—' : <Pulso />}<small>eventos</small></dd>
                  <dd className="ed-kpi__comp">{anomalias.dados && `${anomalias.dados.recorte.inicio}–${anomalias.dados.recorte.fim}, 5 variáveis`}</dd>
                  <dd className="ed-kpi__criterio">Soma dos eventos (dias anômalos consecutivos = 1 evento) de chuva, temperatura e umidade, acima e abaixo do esperado.</dd>
                </div>
              </dl>

              <div className="ed-grade ed-grade--2 est-indicadores-extra">
                <div>
                  <h3 className="ed-figura__titulo">Extremos mensais do recorte</h3>
                  <p className="ed-figura__unidade" style={{ marginBottom: 8 }}>{r?.extremos_mensais.metodo}</p>
                  <ul className="est-extremos">
                    <Extremo rotulo="Maior temperatura média mensal" e={r?.extremos_mensais.temperatura_max} casas={1} />
                    <Extremo rotulo="Menor temperatura média mensal" e={r?.extremos_mensais.temperatura_min} casas={1} />
                    <Extremo rotulo="Maior chuva em um mês" e={r?.extremos_mensais.precipitacao_max} casas={0} />
                    <Extremo rotulo="Menor umidade média mensal" e={r?.extremos_mensais.umidade_min} casas={1} />
                  </ul>
                </div>
                <div>
                  <h3 className="ed-figura__titulo">Distribuição das anomalias por variável</h3>
                  <p className="ed-figura__unidade" style={{ marginBottom: 8 }}>Eventos no recorte e taxa por 1.000 município-dias válidos</p>
                  {anomalias.dados
                    ? (
                      <div className="ed-tabela-wrap">
                        <table className={`ed-tabela${anomalias.carregando ? ' ed-atualizando' : ''}`}>
                          <thead><tr><th>Variável</th><th>Eventos</th><th>Taxa</th><th>Extremos</th></tr></thead>
                          <tbody>
                            {anomalias.dados.variaveis.map((v) => (
                              <tr key={v.variavel}>
                                <td><button type="button" className="ed-link" onClick={() => { setVarAnomalia(v.variavel); document.getElementById('anomalias')?.scrollIntoView({ behavior: 'smooth' }) }}>{ROTULO_ANOMALIA[v.variavel]}</button></td>
                                <td>{fmtInt(v.totais.todas.eventos)}</td>
                                <td>{fmt(v.totais.todas.taxa, 2)}</td>
                                <td>{fmtInt(v.totais.extremos.eventos)}</td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    )
                    : anomalias.erro ? <Estado tipo="erro">{anomalias.erro}</Estado> : <Estado tipo="carregando" altura={180}>Carregando anomalias</Estado>}
                </div>
              </div>
              <p className="ed-kpi__criterio" style={{ marginTop: 16 }}>
                {r?.metodo.ponderacao} {r?.metodo.comparacao}
              </p>
            </>
          )}
        </Bloco>

        {/* ---------- 2. Tempo ---------- */}
        <Bloco id="evolucao" titulo="Evolução temporal">
          <SecaoTemporal serie={serie} recorte={recorte} escopo={escopo} numero={1} />
        </Bloco>

        {/* ---------- 3. Estações ---------- */}
        <Bloco id="sazonal" titulo="Distribuição sazonal"
          intro="Estações meteorológicas do Hemisfério Sul: verão (dez–fev), outono (mar–mai), inverno (jun–ago) e primavera (set–nov).">
          <SecaoSazonal sazonal={sazonal} escopo={escopo} numero={2} estacaoFiltro={recorte.estacao} />
        </Bloco>

        {/* ---------- 4. Anomalias ---------- */}
        <Bloco id="anomalias" titulo="Anomalias e eventos extremos" variante="alerta"
          intro="Dias em que o clima fugiu do esperado pelo modelo de cada município. Anomalia estatística e evento extremo são classificações diferentes e aparecem separadas.">
          <SecaoAnomalias anomalias={anomalias} variavel={varAnomalia} onVariavel={setVarAnomalia} numero={3} />
        </Bloco>

        {/* ---------- 5. Mapa ---------- */}
        <Bloco id="mapa" titulo="Distribuição geográfica"
          intro="Valor de cada um dos municípios no recorte de período, estação e fase ENSO escolhido.">
          <SecaoMapa recorte={recorte} variavelAnomalia={varAnomalia} numero={4} />
        </Bloco>

        {/* ---------- 6. Regiões ---------- */}
        <Bloco id="regioes" titulo="Análise regional"
          intro="Norte, Nordeste, Centro-Oeste, Sudeste e Sul comparados no mesmo recorte de período, estação e fase ENSO.">
          <SecaoRegional regioes={regioes} numero={5} destaque={recorte.regiao} />
        </Bloco>

        {/* ---------- 7. ENSO ---------- */}
        <Bloco id="enso" titulo="Relação com o ENSO" variante="exemplo"
          intro="Como temperatura, chuva e umidade se comportaram nos meses de El Niño, La Niña e neutros, depois de remover o ciclo sazonal de cada município.">
          <SecaoEnso enso={enso} numero={6} regiaoFiltro={recorte.regiao} ensoFiltro={recorte.enso} />
        </Bloco>

        <Bloco titulo="Continue explorando">
          <ul className="inicio-destinos">
            <li><button type="button" className="inicio-destino" onClick={() => onNavegar('explorar')}><b>Explorar município →</b><span>Série diária e mensal de um município, comparação e eventos com notícias.</span></button></li>
            <li><button type="button" className="inicio-destino" onClick={() => onNavegar('analise')}><b>Mapa de anomalias →</b><span>Intensidade, sazonalidade e razão ENSO dos eventos em cada município.</span></button></li>
            <li><button type="button" className="inicio-destino" onClick={() => onNavegar('inicio')}><b>Metodologia →</b><span>Fontes, processamento e métodos estatísticos na página inicial.</span></button></li>
            <li><button type="button" className="inicio-destino" onClick={() => onNavegar('sobre')}><b>Sobre →</b><span>Equipe e detalhes do projeto.</span></button></li>
          </ul>
        </Bloco>
      </div>
      <Rodape />
    </div>
  )
}

function Pulso() {
  return <span className="ed-carregando" style={{ display: 'block', height: 36, width: '70%' }} />
}

function Kpi({ rotulo, ind, casas, periodo, extra, semComparacao }: { rotulo: string; ind?: Indicador; casas: number; periodo: string; extra?: string; semComparacao?: string }) {
  const dif = ind?.diferenca
  return (
    <div className="ed-kpi">
      <dt className="ed-kpi__rotulo">{rotulo}</dt>
      <dd className="ed-kpi__valor">{ind ? <>{fmt(ind.valor, casas)}<small>{ind.unidade}</small></> : <Pulso />}</dd>
      <dd className="ed-kpi__comp">
        {ind && (dif !== null && dif !== undefined
          ? <><b>{fmtSinal(dif, casas === 0 ? 0 : 2)} {ind.unidade}</b> vs. 2015–2025 ({fmt(ind.referencia_2015_2025, casas)})</>
          : <>{periodo}{extra ? ` · ${extra}` : ''}{semComparacao ? ` · ${semComparacao}` : ''}</>)}
      </dd>
      <dd className="ed-kpi__criterio">
        {ind && <>Média simples dos municípios: {fmt(ind.media_simples_municipios, casas)} {ind.unidade}. </>}
        <details className="est-criterio"><summary>Critério de cálculo</summary>{ind?.metodo}</details>
      </dd>
    </div>
  )
}

function Extremo({ rotulo, e, casas }: { rotulo: string; e?: ExtremoMensal | null; casas: number }) {
  return (
    <li>
      <span>{rotulo}</span>
      {e
        ? <b>{fmt(e.valor, casas)} {e.unidade} <small>{e.municipio} — {e.uf}, {MESES_CURTOS[e.mes - 1]}/{e.ano}</small></b>
        : e === null ? <b>—</b> : <Pulso />}
    </li>
  )
}
