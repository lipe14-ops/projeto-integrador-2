// Página inicial (landing): apresenta o Clima Brasil com a identidade visual do
// site (tokens de index.css). Todo número e gráfico vem da API — nada é preenchido à mão.
import { useEffect, useState, type ReactNode } from 'react'
import { Bar, BarChart, Cell, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import {
  FaChartLine, FaCloudSunRain, FaDatabase, FaEnvelope, FaGithub, FaGlobeAmericas, FaNewspaper, FaServer,
} from 'react-icons/fa'
import { Bloco, Estado, Segmentos } from '../components/Editorial/Editorial'
import { useRecurso } from '../components/Editorial/useRecurso'
import { MapaUF } from '../components/Editorial/MapaUF'
import type { Pagina } from '../components/Header/Header'
import { carregarVisaoGeral, type VisaoGeral } from '../data/analise'
import {
  carregarAbrangencia, carregarAnomalias, carregarRegioes, carregarSazonal, carregarSerie, carregarUfs,
  COR_CLASSE, COR_FASE, COR_REGIAO, COR_VARIAVEL, fmt, fmtInt, MESES_CURTOS, NOME_FASE, NOME_VARIAVEL,
  RECORTE_PADRAO, type VariavelClima,
} from '../data/estatisticas'
import { NOMES_ESTACAO } from '../data/seasons'
import { COR_ESTACAO } from '../components/Analise/cores'
import '../styles/editorial.css'
import './Inicio.css'

const UNIDADE_UF: Record<VariavelClima, string> = { temperatura: '°C', precipitacao: 'mm/ano', umidade: '%' }

export default function Inicio({ onNavegar }: { onNavegar: (p: Pagina) => void }) {
  const abr = useRecurso('abr', carregarAbrangencia)
  const ufs = useRecurso('ufs', carregarUfs)
  const regioes = useRecurso('reg', (s) => carregarRegioes(RECORTE_PADRAO, s))
  const serie = useRecurso('serie', (s) => carregarSerie(RECORTE_PADRAO, s))
  const sazonal = useRecurso('saz', (s) => carregarSazonal(RECORTE_PADRAO, s))
  const anomalias = useRecurso('anom', (s) => carregarAnomalias(RECORTE_PADRAO, s))
  const [visao, setVisao] = useState<VisaoGeral | null>(null)
  useEffect(() => {
    let ativo = true
    carregarVisaoGeral().then((v) => { if (ativo) setVisao(v) }).catch(() => { /* opcional */ })
    return () => { ativo = false }
  }, [])
  const [varMapa, setVarMapa] = useState<VariavelClima>('temperatura')

  // a UF mostra precipitação anual (mm/ano) para ficar legível no mapa
  const ufsMapa = ufs.dados?.map((u) => ({ ...u, precipitacao: u.precipitacao === null ? null : u.precipitacao * 12 })) ?? null
  const a = abr.dados
  const chuva = anomalias.dados?.variaveis.find((v) => v.variavel === 'precipitacao')
  const ciclo = serie.dados?.ciclo_mensal.filter((p) => p.precipitacao !== null) ?? []
  const cicloChuva = ciclo.length === 12
    ? {
      max: MESES_CURTOS[ciclo.reduce((a, b) => (b.precipitacao! > a.precipitacao! ? b : a)).mes - 1],
      min: MESES_CURTOS[ciclo.reduce((a, b) => (b.precipitacao! < a.precipitacao! ? b : a)).mes - 1],
    }
    : null
  const totalAnomalias = anomalias.dados?.variaveis.reduce((s, v) => s + v.totais.todas.eventos, 0)

  return (
    <div className="ed inicio">
      {/* ---------- Hero (faixa de título do pôster) ---------- */}
      <header className="inicio-hero">
        <div className="ed-container inicio-hero__grade">
          <div className="inicio-hero__texto">
            <p className="ed-kicker">Plataforma científica de análise climática</p>
            <h1>Clima Brasil</h1>
            <p className="inicio-hero__frase">
              O clima de cada município brasileiro, de {a?.periodo.inicio ?? 2015} a {a?.periodo.fim ?? 2025}, com
              El Niño e La Niña em destaque.
            </p>
            <p className="ed-faixa__sub">
              Temperatura, umidade e chuva da reanálise ERA5-Land para {a ? fmtInt(a.municipios_com_dados) : 'os'} municípios,
              dias fora do padrão detectados por modelos estatísticos e conferidos com notícias da época, em mapas e
              séries que qualquer pessoa pode explorar.
            </p>
            <div className="inicio-hero__acoes">
              <button type="button" className="ed-botao" onClick={() => onNavegar('estatisticas')}>Explorar estatísticas</button>
              <a className="ed-botao ed-botao--sec" href="#plataforma">Conhecer a plataforma</a>
            </div>
            <p className="inicio-hero__autoria">
              Filipe Nascimento Soares e Guilherme Marinheiro de Oliveira · Bacharelado em Ciência da Computação,
              IF Goiano — Campus Rio Verde
            </p>
          </div>
          <figure className="inicio-hero__mapa">
            <MapaUF ufs={ufs.dados} variavel="temperatura" titulo="Temperatura média" unidade="°C" compacto />
            <figcaption>
              <b>Temperatura média 2015–2025 por UF</b> — ERA5-Land, média ponderada pela área dos municípios.
            </figcaption>
          </figure>
        </div>
      </header>

      {/* ---------- Abrangência ---------- */}
      <section className="ed-container" aria-label="Abrangência dos dados">
        <dl className="ed-kpis inicio-abrangencia">
          <Numero rotulo="Municípios com dados" valor={a ? fmtInt(a.municipios_com_dados) : null}
            nota={a ? `de ${fmtInt(a.municipios_cadastrados)} na malha do IBGE; os demais (ilhas e áreas de lagoa) ficam fora da grade do ERA5-Land` : undefined} />
          <Numero rotulo="Período histórico" valor={a ? `${a.periodo.inicio}–${a.periodo.fim}` : null}
            nota={a ? `${a.meses} meses consecutivos` : undefined} />
          <Numero rotulo="Resolução temporal" valor="2 leituras/dia" nota={a?.resolucao_temporal} />
          <Numero rotulo="Variáveis" valor={a ? String(a.variaveis.length) : null} nota={a?.variaveis.join(', ')} />
          <Numero rotulo="Registros climáticos" valor={visao?.climate_records ? `${fmt(visao.climate_records / 1e6, 1)} mi` : null}
            nota="leituras município × horário no banco" />
          <Numero rotulo="Fonte" valor="ERA5-Land" nota={a?.resolucao_espacial} />
        </dl>
        {abr.erro && <Estado tipo="erro">Não foi possível carregar a abrangência: {abr.erro}</Estado>}
      </section>

      <div className="ed-container">
        {/* ---------- A plataforma ---------- */}
        <Bloco id="plataforma" titulo="A plataforma">
          <div className="ed-grade ed-grade--2">
            <div className="ed-texto">
              <h3 className="ed-subtitulo">O que é</h3>
              <p>
                O Clima Brasil é uma plataforma web gratuita que reúne, em um só lugar, a série histórica de
                temperatura, umidade relativa e precipitação de todos os municípios brasileiros com dado na reanálise
                ERA5-Land, os episódios de El Niño e La Niña (índice ONI do NOAA) e os dias de comportamento anômalo.
              </p>
              <h3 className="ed-subtitulo">Qual problema resolve</h3>
              <p>
                Os dados climáticos existem, mas estão espalhados em arquivos de grade, tabelas de órgãos diferentes e
                notícias soltas. Ligar o clima de um município ao El Niño, comparar regiões ou saber se um dia de chuva
                foi de fato excepcional exige processamento que a maioria das pessoas não consegue fazer.
              </p>
              <h3 className="ed-subtitulo">Abrangência</h3>
              <ul className="ed-lista">
                <li><b>Espacial:</b> {a ? fmtInt(a.municipios_com_dados) : '—'} municípios, {a?.ufs ?? 27} UFs e as 5 regiões.</li>
                <li><b>Temporal:</b> {a ? `${a.periodo.inicio} a ${a.periodo.fim}` : '2015 a 2025'}, leituras às 00 e 12 UTC.</li>
                <li><b>Dados:</b> ERA5-Land (ECMWF/Copernicus), malha e atributos do IBGE, ONI do NOAA/CPC e notícias verificadas.</li>
              </ul>
            </div>
            <div className="ed-texto">
              <h3 className="ed-subtitulo">Perguntas que a plataforma responde</h3>
              <ol className="ed-enum">
                <li><b>Impacto local:</b> como foi o clima de um município durante o El Niño e a La Niña?</li>
                <li><b>Comparação:</b> como dois municípios — ou duas regiões — se diferenciam?</li>
                <li><b>Eventos:</b> quando choveu (ou esquentou) fora do padrão, e o que os jornais disseram?</li>
                <li><b>Panorama:</b> quais padrões o país mostra por estação, por região e por fase do ENSO?</li>
              </ol>
              <h3 className="ed-subtitulo">Análises oferecidas</h3>
              <ul className="ed-lista">
                <li>Séries mensais por município com El Niño e La Niña ao fundo e comparação entre municípios.</li>
                <li>Detecção de anomalias e classificação de extremos para o local e a época.</li>
                <li>Eventos de chuva com notícias conferidas na página original.</li>
                <li>Mapas coropléticos municipais e estatísticas nacionais e regionais.</li>
              </ul>
            </div>
          </div>
        </Bloco>

        {/* ---------- O Brasil em dados ---------- */}
        <Bloco id="brasil" titulo="O Brasil em dados"
          intro="Média de 2015 a 2025 em cada unidade federativa, calculada a partir dos municípios (ponderada pela área). O mapa municipal completo, com filtros, está em Estatísticas gerais.">
          <div className="ed-grade inicio-brasil">
            <div>
              <div className="ed-controles">
                <Segmentos rotulo="Variável do mapa" valor={varMapa} onChange={setVarMapa}
                  opcoes={[['temperatura', 'Temperatura'], ['precipitacao', 'Precipitação'], ['umidade', 'Umidade']]} />
              </div>
              {ufs.erro
                ? <Estado tipo="erro">Não foi possível carregar as médias por UF: {ufs.erro}</Estado>
                : <MapaUF ufs={ufsMapa} variavel={varMapa} titulo={`${NOME_VARIAVEL[varMapa]} média`} unidade={UNIDADE_UF[varMapa]} />}
            </div>
            <div>
              <h3 className="ed-subtitulo">As cinco regiões</h3>
              {regioes.dados
                ? (
                  <div className="ed-tabela-wrap">
                    <table className="ed-tabela">
                      <caption>Médias 2015–2025, ponderadas pela área municipal</caption>
                      <thead><tr><th>Região</th><th>Municípios</th><th>Temp. (°C)</th><th>Chuva (mm/ano)</th><th>Umidade (%)</th></tr></thead>
                      <tbody>
                        {regioes.dados.regioes.map((r) => (
                          <tr key={r.regiao}>
                            <td><i className="inicio-ponto" style={{ background: COR_REGIAO[r.regiao] }} />{r.regiao}</td>
                            <td>{fmtInt(r.municipios)}</td>
                            <td>{fmt(r.temperatura, 1)}</td>
                            <td>{fmt(r.precipitacao === null ? null : r.precipitacao * 12, 0)}</td>
                            <td>{fmt(r.umidade, 1)}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )
                : regioes.erro ? <Estado tipo="erro">{regioes.erro}</Estado> : <Estado tipo="carregando" altura={220} />}
              <p className="ed-texto inicio-nota">
                Temperatura e umidade são médias das leituras das 00 e 12 UTC (21 h e 9 h de Brasília), não médias de
                24 horas. Chuva anual = média dos totais mensais × 12.
              </p>
              <button type="button" className="ed-botao ed-botao--sec" onClick={() => onNavegar('estatisticas')}>Ver o mapa municipal</button>
            </div>
          </div>
        </Bloco>

        {/* ---------- Capacidades ---------- */}
        <Bloco id="capacidades" titulo="Capacidades analíticas" variante="exemplo"
          intro="Cada exemplo abaixo é desenhado com os dados reais da plataforma (Brasil, 2015–2025).">
          <div className="inicio-capacidades">
            <Capacidade titulo="Temperatura" texto="Série mensal nacional; no Explorar, a de qualquer município." onAbrir={() => onNavegar('estatisticas')}>
              {serie.dados ? <Mini tipo="linha" dados={serie.dados.mensal.map((p) => ({ x: `${MESES_CURTOS[p.mes - 1]}/${p.ano}`, y: p.temperatura }))} cor={COR_VARIAVEL.temperatura} unidade="°C" casas={1} /> : <MiniEstado erro={serie.erro} />}
            </Capacidade>
            <Capacidade titulo="Precipitação" texto={cicloChuva ? `Ciclo anual médio: ${cicloChuva.max} é o mês mais chuvoso e ${cicloChuva.min} o mais seco (média nacional).` : 'Ciclo anual médio da chuva no Brasil.'} onAbrir={() => onNavegar('estatisticas')}>
              {serie.dados ? <Mini tipo="barra" dados={serie.dados.ciclo_mensal.map((p) => ({ x: MESES_CURTOS[p.mes - 1], y: p.precipitacao }))} cor={COR_VARIAVEL.precipitacao} unidade="mm/mês" casas={0} /> : <MiniEstado erro={serie.erro} />}
            </Capacidade>
            <Capacidade titulo="Umidade" texto="Umidade relativa média por mês do ano, das leituras das 00 e 12 UTC." onAbrir={() => onNavegar('estatisticas')}>
              {serie.dados ? <Mini tipo="linha" dados={serie.dados.ciclo_mensal.map((p) => ({ x: MESES_CURTOS[p.mes - 1], y: p.umidade }))} cor={COR_VARIAVEL.umidade} unidade="%" casas={1} /> : <MiniEstado erro={serie.erro} />}
            </Capacidade>
            <Capacidade titulo="Anomalias" texto={`${totalAnomalias ? fmtInt(totalAnomalias) : '—'} eventos detectados (5 variáveis). Na figura: anomalias estatísticas de chuva por ano.`} onAbrir={() => onNavegar('estatisticas')}>
              {chuva ? <Mini tipo="barra" dados={chuva.por_ano.map((p) => ({ x: String(p.ano), y: p.estatisticas }))} cor={COR_CLASSE.estatisticas} unidade="eventos" casas={0} /> : <MiniEstado erro={anomalias.erro} />}
            </Capacidade>
            <Capacidade titulo="Eventos extremos" texto="Chuvas raras para o local e a época (acima do percentil da climatologia local), por ano." onAbrir={() => onNavegar('estatisticas')}>
              {chuva ? <Mini tipo="barra" dados={chuva.por_ano.map((p) => ({ x: String(p.ano), y: p.extremos }))} cor={COR_CLASSE.extremos} unidade="eventos" casas={0} /> : <MiniEstado erro={anomalias.erro} />}
            </Capacidade>
            <Capacidade titulo="Sazonalidade" texto="Chuva total média de cada estação do Hemisfério Sul (DJF, MAM, JJA, SON)." onAbrir={() => onNavegar('estatisticas')}>
              {sazonal.dados
                ? <Mini tipo="barra" dados={sazonal.dados.resumo.map((s) => ({ x: NOMES_ESTACAO[s.estacao], y: s.precipitacao_total.media, cor: COR_ESTACAO[s.estacao] }))} cor="#888" unidade="mm/estação" casas={0} />
                : <MiniEstado erro={sazonal.erro} />}
            </Capacidade>
            <Capacidade titulo="Relação com o ENSO" texto="Índice ONI mês a mês: vermelho nos episódios de El Niño, azul nos de La Niña." onAbrir={() => onNavegar('estatisticas')}>
              {serie.dados
                ? <Mini tipo="barra" dados={serie.dados.mensal.map((p) => ({ x: `${MESES_CURTOS[p.mes - 1]}/${p.ano}`, y: p.oni, cor: COR_FASE[p.fase ?? 'neutro'] }))} cor="#888" unidade="°C (ONI)" casas={2} />
                : <MiniEstado erro={serie.erro} />}
            </Capacidade>
            <Capacidade titulo="Séries temporais" texto="Precipitação mensal do Brasil; o modelo ARIMA de cada município prevê o dia e mede o resíduo." onAbrir={() => onNavegar('explorar')} acao="Abrir o Explorar">
              {serie.dados ? <Mini tipo="linha" dados={serie.dados.mensal.map((p) => ({ x: `${MESES_CURTOS[p.mes - 1]}/${p.ano}`, y: p.precipitacao }))} cor={COR_VARIAVEL.precipitacao} unidade="mm/mês" casas={0} /> : <MiniEstado erro={serie.erro} />}
            </Capacidade>
          </div>
          <p className="ed-texto inicio-nota">
            Legenda ENSO: <span style={{ color: COR_FASE.el_nino, fontWeight: 500 }}>■ {NOME_FASE.el_nino}</span>{' '}
            <span style={{ color: COR_FASE.la_nina, fontWeight: 500 }}>■ {NOME_FASE.la_nina}</span>{' '}
            <span style={{ color: COR_FASE.neutro, fontWeight: 500 }}>■ {NOME_FASE.neutro}</span>{' '}
            (regra de episódio do NOAA/CPC: ONI ≥ +0,5 ou ≤ −0,5 °C por 5 trimestres seguidos).
          </p>
        </Bloco>

        {/* ---------- Metodologia ---------- */}
        <Bloco id="metodologia" titulo="Metodologia" variante="alerta">
          <p className="ed-subtitulo" style={{ marginTop: 0 }}>Como os dados chegam até o site:</p>
          <div className="ed-fluxo" role="list" aria-label="Fluxo dos dados">
            <Passo icone={<FaCloudSunRain size={26} />} titulo="Dados" texto="ERA5-Land, IBGE e NOAA" />
            <Passo icone={<FaDatabase size={24} />} titulo="Banco" texto="PostgreSQL + PostGIS" />
            <Passo icone={<FaChartLine size={24} />} titulo="Análise" texto="dias fora do padrão" />
            <Passo icone={<FaNewspaper size={24} />} titulo="Notícias" texto="busca e conferência" />
            <Passo icone={<FaServer size={22} />} titulo="API" texto="FastAPI" />
            <Passo icone={<FaGlobeAmericas size={24} />} titulo="Site" texto="React + Leaflet" />
          </div>
          <div className="ed-grade ed-grade--2" style={{ marginTop: 32 }}>
            <ul className="ed-lista">
              <li><b>ERA5-Land:</b> reanálise do ECMWF (grade de ≈ 9 km) que combina modelo e observações; temperatura
                a 2 m, ponto de orvalho e precipitação às 00 e 12 UTC, amostrados em cada município.</li>
              <li><b>Processamento das séries:</b> umidade relativa pela fórmula de Magnus; chuva diária = soma das duas
                metades de 12 h; agregados mensais em uma visão materializada.</li>
              <li><b>Métodos estatísticos:</b> um modelo ARIMA prevê a chuva de cada dia; temperatura e umidade usam
                harmônicos sazonais com termo autorregressivo. O <i>resíduo</i> é o erro da previsão.</li>
              <li><b>Anomalia × extremo:</b> se o resíduo passa de 3 desvios-padrão (|Z| &gt; 3), o dia é
                <i> anomalia</i>; só é <i>extremo</i> se o valor também for raro para o local e a época (percentis da
                climatologia local). Uma anomalia não é, por si, um evento extremo.</li>
            </ul>
            <ul className="ed-lista">
              <li><b>Análise espacial:</b> taxas de eventos por 1.000 dias válidos (comparáveis entre municípios),
                estação predominante com teste qui-quadrado e correção FDR, autocorrelação espacial (I de Moran).</li>
              <li><b>ENSO:</b> fase de cada mês pela regra de episódio do NOAA/CPC; comparações feitas sobre anomalias,
                depois de remover o ciclo sazonal. Associação estatística não prova causa.</li>
              <li><b>Investigação de ocorrências:</b> busca de notícias de 3 dias antes a 7 dias depois do evento, com
                conferência de data, cidade e tema na página original. Teste com 67 notícias simuladas e gabarito
                prévio: 91% das corretas aceitas, F1 = 0,81.</li>
              <li><b>Limitações:</b> reanálise não é estação meteorológica; duas leituras por dia não captam máximas e
                mínimas diárias; as notícias ainda não foram avaliadas por humanos.</li>
            </ul>
          </div>
        </Bloco>

        {/* ---------- Navegação ---------- */}
        <Bloco id="navegar" titulo="Por onde começar">
          <ul className="inicio-destinos">
            <Destino titulo="Estatísticas gerais" texto="Panorama climático nacional (indicadores, séries, estações, regiões e ENSO) e o mapa de anomalias." onClick={() => onNavegar('estatisticas')} />
            <Destino titulo="Explorar município" texto="Gráficos de um município com El Niño e La Niña ao fundo, comparação e eventos com notícias." onClick={() => onNavegar('explorar')} />
            <Destino titulo="Mapa de anomalias" texto="Em Estatísticas: frequência, intensidade e sazonalidade dos eventos anômalos em cada município." onClick={() => onNavegar('analise')} />
            <Destino titulo="Sobre" texto="Equipe, fontes de dados e detalhes do projeto." onClick={() => onNavegar('sobre')} />
          </ul>
        </Bloco>
      </div>

      <Rodape />
    </div>
  )
}

export function Rodape() {
  return (
    <footer className="ed-rodape">
      <div className="ed-container ed-rodape__inner">
        <a href="https://github.com/lipe14-ops/projeto-integrador-2" target="_blank" rel="noreferrer"><FaGithub aria-hidden="true" /> lipe14-ops/projeto-integrador-2</a>
        <a href="mailto:filipe.soares@estudante.ifgoiano.edu.br"><FaEnvelope aria-hidden="true" /> filipe.soares@estudante.ifgoiano.edu.br</a>
        <a href="mailto:guilherme.marinheiro@estudante.ifgoiano.edu.br"><FaEnvelope aria-hidden="true" /> guilherme.marinheiro@estudante.ifgoiano.edu.br</a>
      </div>
    </footer>
  )
}

function Numero({ rotulo, valor, nota }: { rotulo: string; valor: string | null; nota?: string }) {
  return (
    <div className="ed-kpi">
      <dt className="ed-kpi__rotulo">{rotulo}</dt>
      <dd className="ed-kpi__valor">{valor ?? <span className="ed-carregando" style={{ display: 'block', height: 36, width: '70%' }} />}</dd>
      {nota && <dd className="ed-kpi__criterio">{nota}</dd>}
    </div>
  )
}

function Passo({ icone, titulo, texto }: { icone: ReactNode; titulo: string; texto: string }) {
  return (
    <div className="ed-fluxo__caixa" role="listitem">
      {icone}
      <b>{titulo}</b>
      <span>{texto}</span>
    </div>
  )
}

function Capacidade({ titulo, texto, children, onAbrir, acao = 'Ver em Estatísticas' }: {
  titulo: string; texto: string; children: ReactNode; onAbrir: () => void; acao?: string
}) {
  return (
    <article className="inicio-capacidade">
      <h3>{titulo}</h3>
      <div className="inicio-capacidade__grafico">{children}</div>
      <p>{texto}</p>
      <button type="button" className="ed-link" onClick={onAbrir}>{acao} →</button>
    </article>
  )
}

function Destino({ titulo, texto, onClick }: { titulo: string; texto: string; onClick: () => void }) {
  return (
    <li>
      <button type="button" className="inicio-destino" onClick={onClick}>
        <b>{titulo} <span aria-hidden="true">→</span></b>
        <span>{texto}</span>
      </button>
    </li>
  )
}

function MiniEstado({ erro }: { erro: string | null }) {
  return erro ? <p className="inicio-mini-erro">Dados indisponíveis</p> : <div className="ed-carregando" style={{ height: '100%' }} />
}

type PontoMini = { x: string; y: number | null; cor?: string }

function Mini({ tipo, dados, cor, unidade, casas }: { tipo: 'linha' | 'barra'; dados: PontoMini[]; cor: string; unidade: string; casas: number }) {
  const dica = (
    <Tooltip
      cursor={tipo === 'barra' ? { fill: 'rgb(0 0 0 / 6%)' } : { stroke: '#999', strokeWidth: 1 }}
      content={({ active, payload }) => {
        const p = active ? (payload?.[0]?.payload as PontoMini | undefined) : undefined
        if (!p) return null
        return <div className="ed-tooltip"><b>{p.x}</b>: {fmt(p.y, casas)} {unidade}</div>
      }}
    />
  )
  return (
    <ResponsiveContainer width="100%" height="100%">
      {tipo === 'linha'
        ? (
          <LineChart data={dados} margin={{ top: 6, right: 4, bottom: 0, left: 4 }}>
            <XAxis dataKey="x" hide />
            <YAxis hide domain={['auto', 'auto']} />
            {dica}
            <Line type="monotone" dataKey="y" stroke={cor} strokeWidth={2} dot={false} isAnimationActive={false} />
          </LineChart>
        )
        : (
          <BarChart data={dados} margin={{ top: 6, right: 4, bottom: 0, left: 4 }} barCategoryGap={dados.length > 40 ? 0 : 3}>
            <XAxis dataKey="x" hide />
            <YAxis hide domain={[(m: number) => Math.min(0, m), 'auto']} />
            {dica}
            <Bar dataKey="y" fill={cor} radius={dados.length > 40 ? 0 : [3, 3, 0, 0]} isAnimationActive={false}>
              {dados.map((d, i) => <Cell key={i} fill={d.cor ?? cor} />)}
            </Bar>
          </BarChart>
        )}
    </ResponsiveContainer>
  )
}
