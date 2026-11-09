import { useEffect, useMemo, useRef, useState } from 'react'
import { AnalysisSection } from '../components/AnalysisSection'
import { IconNews } from '../components/Icons'
import { MunicipioCard } from '../components/MunicipioCard'
import MapaBrasil from '../components/MapaBrasil/MapaBrasil'
import { SearchFilters, type Filtros } from '../components/SearchFilters'
import { SummaryCards } from '../components/SummaryCards'
import { ANO_FIM, ANO_INICIO, mediaPeriodo, mesFinalDoAno, mesInicialDoAno, registrarSerieReal, type Municipio, type SerieClima } from '../data/climate'
import { carregarClima, carregarMunicipio, carregarMunicipios, carregarMunicipiosAnalisados, type MunicipioAnalisado } from '../data/api'

type Enso = { year: number; month: number; enso_index: number | null }

const PADRAO: Filtros = { municipio: null, de: ANO_INICIO, ate: ANO_FIM }

export default function HomePage() {
  const [municipios, setMunicipios] = useState<Municipio[]>([])
  const [filtros, setFiltros] = useState<Filtros>(PADRAO)
  // dados climáticos indexados pelo município: o período é recortado no cliente
  const [dados, setDados] = useState<{ ibge: string; serie: SerieClima; enso: Enso[] } | null>(null)
  const [erroClima, setErroClima] = useState<{ ibge: string; mensagem: string } | null>(null)
  const [carregandoMunicipios, setCarregandoMunicipios] = useState(true)
  const [erro, setErro] = useState('')
  const [versaoForm, setVersaoForm] = useState(0)
  const municipioAtual = useRef<string | null>(null)
  const requisicaoDetalhes = useRef<AbortController | null>(null)

  useEffect(() => {
    carregarMunicipios().then((lista) => {
      setMunicipios(lista)
    }).catch((e: unknown) => setErro(e instanceof Error ? e.message : 'Não foi possível carregar os municípios da API.'))
      .finally(() => setCarregandoMunicipios(false))
  }, [])

  // pontos de notícias no mapa: as contagens seguem o período escolhido
  const [pontosRes, setPontosRes] = useState<{ chave: string; lista?: MunicipioAnalisado[]; erro?: boolean } | null>(null)
  const chavePontos = `${filtros.de}-${filtros.ate}`
  useEffect(() => {
    const controller = new AbortController()
    carregarMunicipiosAnalisados(controller.signal, { anoDe: filtros.de, anoAte: filtros.ate, fonte: '' })
      .then((lista) => setPontosRes({ chave: chavePontos, lista }))
      .catch(() => { if (!controller.signal.aborted) setPontosRes({ chave: chavePontos, erro: true }) })
    return () => controller.abort()
  }, [chavePontos, filtros.de, filtros.ate])
  // enquanto troca o período, mantém os pontos anteriores na tela
  const pontosNoticias = pontosRes?.lista ?? null
  const statusNoticias: 'carregando' | 'erro' | 'ok' =
    pontosRes?.chave !== chavePontos ? 'carregando' : pontosRes.erro ? 'erro' : 'ok'

  const codigoIbge = filtros.municipio?.ibge ?? null
  // aviso de notícias: aparece ao selecionar município com notícias verificadas
  const [avisoFechado, setAvisoFechado] = useState<string | null>(null)
  const noticiasSelecionado = (codigoIbge && pontosNoticias?.find((p) => p.codigoIbge === codigoIbge)?.noticias) || 0
  const mostrarAviso = Boolean(codigoIbge) && noticiasSelecionado > 0 && avisoFechado !== codigoIbge

  function irParaNoticias() {
    setAvisoFechado(codigoIbge)
    const secao = document.getElementById('noticias-eventos')
    if (secao) secao.scrollIntoView({ behavior: 'smooth', block: 'start' })
    else window.scrollTo({ top: document.documentElement.scrollHeight, behavior: 'smooth' })
  }
  useEffect(() => {
    if (!codigoIbge) return
    const controller = new AbortController()
    carregarClima(codigoIbge, controller.signal).then(({ serie: s, enso: indices }) => {
      if (controller.signal.aborted) return
      registrarSerieReal(codigoIbge, s)
      setDados({ ibge: codigoIbge, serie: s, enso: indices })
    }).catch((e: unknown) => {
      if (!controller.signal.aborted && !(e instanceof DOMException && e.name === 'AbortError')) {
        setErroClima({ ibge: codigoIbge, mensagem: e instanceof Error ? e.message : 'Não foi possível carregar os dados climáticos.' })
      }
    })
    return () => controller.abort()
  }, [codigoIbge])

  const serie = codigoIbge && dados?.ibge === codigoIbge ? dados.serie : null
  const enso = serie ? dados!.enso : []
  const erroAtual = codigoIbge && erroClima?.ibge === codigoIbge ? erroClima.mensagem : ''
  const carregando = Boolean(codigoIbge) && !serie && !erroAtual

  const mesDe = mesInicialDoAno(filtros.de)
  const mesAte = mesFinalDoAno(filtros.ate)
  const resumo = useMemo(() => serie ? ({
    temp: mediaPeriodo(serie.temp, mesDe, mesAte),
    chuva: mediaPeriodo(serie.chuva, mesDe, mesAte),
    umid: mediaPeriodo(serie.umid, mesDe, mesAte),
  }) : null, [serie, mesDe, mesAte])

  async function selecionarNoMapa(selecionado: { codigo: string; nome: string; uf: string }) {
    municipioAtual.current = selecionado.codigo
    setErro('')
    const base = municipios.find((m) => m.ibge === selecionado.codigo) ?? {
      id: selecionado.codigo, ibge: selecionado.codigo, nome: selecionado.nome, uf: selecionado.uf,
      regiao: '—', lat: 0, lon: 0, temp: 0, chuva: 0, umid: 0,
    }
    setFiltros((atual) => ({ ...atual, municipio: base }))
    setVersaoForm((versao) => versao + 1)
    requisicaoDetalhes.current?.abort()
    const controller = new AbortController()
    requisicaoDetalhes.current = controller
    try {
      const municipio = await carregarMunicipio(selecionado.codigo, controller.signal)
      if (controller.signal.aborted || municipioAtual.current !== selecionado.codigo) return
      setFiltros((atual) => ({ ...atual, municipio }))
    } catch (e) {
      if (!controller.signal.aborted && municipioAtual.current === selecionado.codigo) {
        setErro(e instanceof Error ? e.message : 'Não foi possível carregar os dados do município selecionado.')
      }
    }
  }

  return (
    <div className="page">
      <section className="hero" aria-labelledby="hero-titulo">
        <h1 id="hero-titulo" style={{ fontSize: 40 }}>Explore o clima de qualquer município do Brasil</h1>
        <p className="hero__lead">Temperatura, chuva e umidade de 2015 a 2025, com episódios de El Niño e La Niña e eventos de chuva extrema em destaque.</p>
      </section>

      {(erro || erroAtual) && <p role="alert" className="filter-error">{erro || erroAtual}</p>}
      <SearchFilters key={versaoForm} aplicado={filtros} padrao={PADRAO} municipios={municipios} carregandoMunicipios={carregandoMunicipios} onAplicar={(f) => { municipioAtual.current = f.municipio?.ibge ?? null; requisicaoDetalhes.current?.abort(); setFiltros(f); setVersaoForm((v) => v + 1) }} />

      <section className="explore" aria-label="Mapa e dados do município">
        <MapaBrasil onSelectMunicipio={selecionarNoMapa} pontosNoticias={pontosNoticias} statusNoticias={statusNoticias} />
        {filtros.municipio
          ? <MunicipioCard municipio={filtros.municipio} />
          : <div className="card municipio-vazio"><p className="mono-label">Município selecionado</p><h2>Selecione um município</h2><p>Escolha um estado e um município nos filtros, ou selecione um no mapa.</p></div>}
      </section>

      {carregando && filtros.municipio && <section className="dashboard-loading" role="status" aria-live="polite" aria-busy="true">
        <div className="loading-message"><span className="loading-spinner" />Buscando dados climáticos de {filtros.municipio.nome}…</div>
        <div className="loading-kpis">{[0, 1, 2].map((item) => <div className="loading-skeleton loading-skeleton--kpi" key={item} />)}</div>
        <div className="loading-charts">{[0, 1, 2].map((item) => <div className="loading-skeleton loading-skeleton--chart" key={item} />)}</div>
      </section>}
      {resumo && !carregando && filtros.municipio && <>
        <SummaryCards {...resumo} />
        <AnalysisSection municipio={filtros.municipio} municipios={municipios} mesDe={mesDe} mesAte={mesAte} serie={serie!} enso={enso} />
      </>}
      {mostrarAviso && filtros.municipio && (
        <div className="aviso-noticias" role="status" aria-live="polite">
          <IconNews size={20} className="aviso-noticias__icone" />
          <button type="button" className="aviso-noticias__acao" onClick={irParaNoticias}>
            <span>
              <b>{noticiasSelecionado} {noticiasSelecionado === 1 ? 'notícia verificada' : 'notícias verificadas'}</b> de
              desastre por chuva em {filtros.municipio.nome}
            </span>
            <span className="aviso-noticias__link">Ver notícias ↓</span>
          </button>
          <button type="button" className="aviso-noticias__fechar" aria-label="Fechar aviso" onClick={() => setAvisoFechado(codigoIbge)}>×</button>
        </div>
      )}
    </div>
  )
}
