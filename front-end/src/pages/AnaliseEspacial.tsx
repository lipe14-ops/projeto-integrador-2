import { useEffect, useMemo, useRef, useState } from 'react'
import { MapaCoropletico, type NomeMunicipio } from '../components/Analise/MapaCoropletico'
import { Legenda } from '../components/Analise/Legenda'
import { PainelMunicipio } from '../components/Analise/PainelMunicipio'
import { SecaoRegioes } from '../components/Analise/SecaoRegioes'
import { SecaoNoticias } from '../components/Analise/SecaoNoticias'
import { ResumoDados } from '../components/Analise/ResumoDados'
import '../components/Analise/Analise.css'
import { carregarMunicipios } from '../data/api'
import {
  carregarAnaliseMunicipio, carregarCoropletico, carregarDefinicoes, carregarGeometrias, carregarRegioes, ehAbort,
  type AnaliseMunicipio, type ClasseEvento, type Coropletico, type Definicoes, type FaseComparacao,
  type FaseEnsoAnalise, type FiltrosAnalise, type Geometrias, type Metrica, type Regioes, type Variavel,
} from '../data/analise'
import { NOMES_ESTACAO, ORDEM_ESTACOES, type Estacao } from '../data/seasons'

const ANOS = Array.from({ length: 11 }, (_, i) => 2015 + i)
const PORTO_ALEGRE = '4314902'

const ORDEM_METRICAS: Metrica[] = [
  'taxa', 'contagem', 'intensidade', 'participacao', 'outono_inverno', 'concentracao', 'estacao_dominante', 'razao_enso',
]
const ORDEM_VARIAVEIS: Variavel[] = ['precipitacao', 'temperatura_alta', 'temperatura_baixa', 'umidade_alta', 'umidade_baixa']
const ORDEM_CLASSES: ClasseEvento[] = ['todas', 'estatisticas', 'extremos', 'impacto']
const ROTULO_CLASSE: Record<ClasseEvento, string> = {
  todas: 'Todas as anomalias', estatisticas: 'Só anomalias estatísticas', extremos: 'Só extremos', impacto: 'Só com notícia (impacto)',
}
// métricas calculadas com as 4 estações juntas: o filtro de estação não se aplica
const SEM_ESTACAO = new Set<Metrica>(['outono_inverno', 'concentracao', 'estacao_dominante'])

const PADRAO: FiltrosAnalise = {
  variable: 'precipitacao', event_class: 'todas', start_year: 2017, end_year: 2025, season: null, enso_phase: null,
}

const mensagem = (e: unknown, padrao: string) => (e instanceof Error ? e.message : padrao)

type Resultado<T> = { chave: string; dados?: T; erro?: string }

export default function AnaliseEspacial() {
  const [filtros, setFiltros] = useState<FiltrosAnalise>(PADRAO)
  const [metrica, setMetrica] = useState<Metrica>('taxa')
  const [comparar, setComparar] = useState<FaseComparacao>('el_nino')
  const [selecionado, setSelecionado] = useState<string | null>(null)
  const mapaRef = useRef<HTMLDivElement>(null)

  // ---- dados fixos: definições, malha e nomes ----
  const [definicoes, setDefinicoes] = useState<Definicoes | null>(null)
  const [geometrias, setGeometrias] = useState<Geometrias | null>(null)
  const [nomes, setNomes] = useState<Map<string, NomeMunicipio>>(new Map())
  const [erroBase, setErroBase] = useState<string | null>(null)
  useEffect(() => {
    carregarDefinicoes().then(setDefinicoes).catch((e: unknown) => setErroBase(mensagem(e, 'Não foi possível carregar as definições.')))
    carregarGeometrias().then(setGeometrias).catch((e: unknown) => setErroBase(mensagem(e, 'Não foi possível carregar a malha municipal.')))
    carregarMunicipios()
      .then((lista) => setNomes(new Map(lista.map((m) => [m.ibge, { nome: m.nome, uf: m.uf }]))))
      .catch(() => { /* sem nomes, o mapa mostra o código IBGE */ })
  }, [])

  // ---- filtros efetivos (combinações sem efeito são neutralizadas) ----
  const efetivos = useMemo<FiltrosAnalise>(() => ({
    ...filtros,
    season: SEM_ESTACAO.has(metrica) ? null : filtros.season,
    enso_phase: metrica === 'razao_enso' ? null : filtros.enso_phase,
  }), [filtros, metrica])
  const metricaInvalida = metrica === 'participacao' && !efetivos.season
  const chaveMapa = JSON.stringify([metrica, efetivos, metrica === 'razao_enso' ? comparar : null])

  // ---- coroplético ----
  const [mapaRes, setMapaRes] = useState<Resultado<Coropletico> | null>(null)
  useEffect(() => {
    if (metricaInvalida) return
    const controller = new AbortController()
    carregarCoropletico(metrica, efetivos, comparar, controller.signal)
      .then((dados) => setMapaRes({ chave: chaveMapa, dados }))
      .catch((e: unknown) => {
        if (!controller.signal.aborted && !ehAbort(e)) setMapaRes({ chave: chaveMapa, erro: mensagem(e, 'Erro ao calcular o mapa.') })
      })
    return () => controller.abort()
  }, [chaveMapa, metrica, efetivos, comparar, metricaInvalida])
  const mapaAtual = mapaRes?.chave === chaveMapa
  const carregandoMapa = !metricaInvalida && !mapaAtual
  // enquanto recalcula, mantém o último mapa válido na tela
  const [ultimoMapa, setUltimoMapa] = useState<Coropletico | null>(null)
  if (mapaAtual && mapaRes?.dados && mapaRes.dados !== ultimoMapa) setUltimoMapa(mapaRes.dados)
  const dadosMapa = mapaAtual && mapaRes?.dados ? mapaRes.dados : ultimoMapa
  const erroMapa = metricaInvalida ? 'Escolha uma estação para a métrica “Participação da estação”.' : mapaAtual ? mapaRes?.erro ?? null : null

  // ---- painel do município ----
  const chavePainel = selecionado ? JSON.stringify([selecionado, efetivos]) : ''
  const [painelRes, setPainelRes] = useState<Resultado<AnaliseMunicipio> | null>(null)
  useEffect(() => {
    if (!selecionado) return
    const controller = new AbortController()
    carregarAnaliseMunicipio(selecionado, efetivos, controller.signal)
      .then((dados) => setPainelRes({ chave: chavePainel, dados }))
      .catch((e: unknown) => {
        if (!controller.signal.aborted && !ehAbort(e)) setPainelRes({ chave: chavePainel, erro: mensagem(e, 'Erro ao carregar o município.') })
      })
    return () => controller.abort()
  }, [chavePainel, selecionado, efetivos])
  const painelAtual = painelRes?.chave === chavePainel

  // ---- regiões (sem recorte de estação) ----
  const filtrosRegiao = useMemo(() => ({ ...efetivos, season: null, enso_phase: filtros.enso_phase }), [efetivos, filtros.enso_phase])
  const chaveRegiao = JSON.stringify(filtrosRegiao)
  const [regiaoRes, setRegiaoRes] = useState<Resultado<Regioes> | null>(null)
  useEffect(() => {
    const controller = new AbortController()
    carregarRegioes(filtrosRegiao, controller.signal)
      .then((dados) => setRegiaoRes({ chave: chaveRegiao, dados }))
      .catch((e: unknown) => {
        if (!controller.signal.aborted && !ehAbort(e)) setRegiaoRes({ chave: chaveRegiao, erro: mensagem(e, 'Erro ao carregar as regiões.') })
      })
    return () => controller.abort()
  }, [chaveRegiao, filtrosRegiao])
  const regiaoAtual = regiaoRes?.chave === chaveRegiao

  // ---- ações ----
  function alterar<K extends keyof FiltrosAnalise>(campo: K, valor: FiltrosAnalise[K]) {
    setFiltros((f) => {
      const novo = { ...f, [campo]: valor }
      if (campo === 'variable' && valor !== 'precipitacao' && novo.event_class === 'impacto') novo.event_class = 'todas'
      if (campo === 'start_year' && novo.end_year < (valor as number)) novo.end_year = valor as number
      if (campo === 'end_year' && novo.start_year > (valor as number)) novo.start_year = valor as number
      return novo
    })
  }

  function verPortoAlegre() {
    setMetrica('outono_inverno')
    setSelecionado(PORTO_ALEGRE)
    mapaRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' })
  }

  const variaveis = definicoes?.variables
  const metricas = definicoes?.metrics
  const estacaoDesativada = SEM_ESTACAO.has(metrica)

  const avisoMapa = !geometrias && !erroBase
    ? 'Carregando a malha dos 5.573 municípios…'
    : carregandoMapa
      ? 'Calculando a métrica para todos os municípios… (a primeira consulta de cada combinação pode levar ~30 s)'
      : null

  const nomeSelecionado = selecionado ? nomes.get(selecionado) : undefined

  return (
    <div className="page analise-pagina">
      <section className="hero" aria-labelledby="analise-titulo">
        <h1 id="analise-titulo" style={{ fontSize: 40 }}>Mapa nacional de eventos anômalos</h1>
        <p className="hero__lead">
          Frequência, intensidade e sazonalidade dos eventos detectados em cada município brasileiro, com dados
          pontuados de 2017 a 2025. Escolha a variável, a métrica e o recorte; clique em um estado e depois em um município para
          ver a sua distribuição por estação.
        </p>
        <ResumoDados />
      </section>

      {erroBase && <p role="alert" className="filter-error">{erroBase}</p>}

      <section className="card analise-filtros" aria-label="Filtros do mapa">
        <label className="field">
          <span className="field__label">Variável</span>
          <select className="input" value={filtros.variable} onChange={(e) => alterar('variable', e.target.value as Variavel)}>
            {ORDEM_VARIAVEIS.map((v) => (
              <option key={v} value={v} disabled={variaveis ? !variaveis[v]?.available : v !== 'precipitacao'}>
                {variaveis?.[v]?.label ?? v}{variaveis && !variaveis[v]?.available ? ' (indisponível)' : ''}
              </option>
            ))}
          </select>
        </label>
        <label className="field">
          <span className="field__label">Classe de evento</span>
          <select className="input" value={filtros.event_class} onChange={(e) => alterar('event_class', e.target.value as ClasseEvento)}
            title={definicoes?.class_filters[filtros.event_class]}>
            {ORDEM_CLASSES.map((c) => (
              <option key={c} value={c} disabled={c === 'impacto' && filtros.variable !== 'precipitacao'}>
                {ROTULO_CLASSE[c]}{c === 'impacto' && filtros.variable !== 'precipitacao' ? ' (só chuva)' : ''}
              </option>
            ))}
          </select>
        </label>
        <label className="field analise-filtros__metrica">
          <span className="field__label">Métrica</span>
          <select className="input" value={metrica} onChange={(e) => setMetrica(e.target.value as Metrica)}>
            {ORDEM_METRICAS.map((m) => (
              <option key={m} value={m} disabled={m === 'participacao' && !filtros.season}>
                {metricas?.[m]?.label ?? m}{m === 'participacao' && !filtros.season ? ' (escolha uma estação)' : ''}
              </option>
            ))}
          </select>
        </label>
        <div className="field">
          <span className="field__label">Período</span>
          <div className="analise-filtros__periodo">
            <select className="input" aria-label="Ano inicial" value={filtros.start_year} onChange={(e) => alterar('start_year', Number(e.target.value))}>
              {ANOS.map((a) => <option key={a} value={a}>{a}</option>)}
            </select>
            <span>a</span>
            <select className="input" aria-label="Ano final" value={filtros.end_year} onChange={(e) => alterar('end_year', Number(e.target.value))}>
              {ANOS.map((a) => <option key={a} value={a}>{a}</option>)}
            </select>
          </div>
        </div>
        <label className="field">
          <span className="field__label">Estação</span>
          <select className="input" value={estacaoDesativada ? '' : filtros.season ?? ''} disabled={estacaoDesativada}
            title={estacaoDesativada ? 'Esta métrica compara as quatro estações; o filtro de estação não se aplica.' : undefined}
            onChange={(e) => alterar('season', (e.target.value || null) as Estacao | null)}>
            <option value="" disabled={metrica === 'participacao'}>Todas as estações</option>
            {ORDEM_ESTACOES.map((s) => <option key={s} value={s}>{definicoes?.seasons[s] ?? NOMES_ESTACAO[s]}</option>)}
          </select>
        </label>
        <label className="field">
          <span className="field__label">Fase ENSO</span>
          <select className="input" value={metrica === 'razao_enso' ? '' : filtros.enso_phase ?? ''} disabled={metrica === 'razao_enso'}
            title={metrica === 'razao_enso' ? 'A razão ENSO já compara a fase escolhida com os meses neutros.' : definicoes?.enso_rule}
            onChange={(e) => alterar('enso_phase', (e.target.value || null) as FaseEnsoAnalise | null)}>
            <option value="">Todas as fases</option>
            {(['el_nino', 'la_nina', 'neutro'] as const).map((f) => <option key={f} value={f}>{definicoes?.enso_phases[f] ?? f}</option>)}
          </select>
        </label>
        {metrica === 'razao_enso' && (
          <label className="field">
            <span className="field__label">Comparar</span>
            <select className="input" value={comparar} onChange={(e) => setComparar(e.target.value as FaseComparacao)}>
              <option value="el_nino">El Niño ÷ neutro</option>
              <option value="la_nina">La Niña ÷ neutro</option>
            </select>
          </label>
        )}
        <p className="analise-filtros__nota">
          {filtros.start_year < 2017 && 'Os eventos são pontuados a partir de 2017 (os anos anteriores servem de base para os modelos). '}
          {estacaoDesativada && 'Esta métrica compara as quatro estações, por isso o filtro de estação fica desativado. '}
          {metrica === 'razao_enso' && 'A razão ENSO usa todos os meses (episódio da fase escolhida vs. neutros). '}
        </p>
      </section>

      {metrica === 'contagem' && (
        <p className="analise-aviso" role="note">
          <b>Atenção:</b> contagens absolutas não são comparáveis entre municípios com cobertura de dados diferente
          (mais dias válidos tendem a gerar mais eventos). Para comparar municípios, use a métrica{' '}
          <button type="button" className="link-btn" onClick={() => setMetrica('taxa')}>“Frequência de eventos” (taxa)</button>.
        </p>
      )}

      <section className="analise-mapa" ref={mapaRef} aria-label="Mapa coroplético">
        <div className="analise-mapa__principal">
          <div className="card analise-mapa__card">
            <MapaCoropletico
              geometrias={geometrias} dados={dadosMapa} nomes={nomes} selecionado={selecionado}
              onSelecionar={setSelecionado} aviso={avisoMapa} erro={erroMapa ? 'Não foi possível atualizar o mapa' : null}
              onVoltar={() => setSelecionado(null)}
            />
          </div>
          {erroMapa && <p role="alert" className="filter-error">{erroMapa}</p>}
          {dadosMapa
            ? <Legenda dados={dadosMapa} definicoes={definicoes} filtros={efetivos} comparar={comparar} desatualizado={carregandoMapa} />
            : !erroMapa && <div className="loading-skeleton analise-mapa__legenda-carregando" />}
        </div>
        <div className="analise-mapa__lateral">
          {selecionado
            ? (
              <PainelMunicipio
                codigo={selecionado}
                nome={nomeSelecionado ? `${nomeSelecionado.nome} — ${nomeSelecionado.uf}` : null}
                analise={painelAtual ? painelRes?.dados ?? null : null}
                carregando={!painelAtual}
                erro={painelAtual ? painelRes?.erro ?? null : null}
                valorMapa={dadosMapa?.values.find((v) => String(v.codigo_ibge) === selecionado)}
                dados={dadosMapa}
                definicoes={definicoes}
                onFechar={() => setSelecionado(null)}
              />
            )
            : (
              <div className="card municipio-vazio">
                <p className="mono-label">Município selecionado</p>
                <h2>Selecione um município</h2>
                <p>Clique em um estado para ver os municípios dele; depois, passe o mouse para ver o valor de cada
                  município e clique para abrir a distribuição sazonal comparada com o estado, a região e o Brasil, e a
                  razão de frequência por fase ENSO.</p>
              </div>
            )}
        </div>
      </section>

      <SecaoRegioes
        dados={regiaoRes?.dados ?? null}
        carregando={!regiaoAtual}
        erro={regiaoAtual ? regiaoRes?.erro ?? null : null}
        definicoes={definicoes}
        filtros={filtrosRegiao}
        onVerPortoAlegre={verPortoAlegre}
      />

      <SecaoNoticias />
    </div>
  )
}
