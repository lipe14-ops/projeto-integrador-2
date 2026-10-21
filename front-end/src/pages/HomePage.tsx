import { useEffect, useMemo, useRef, useState } from 'react'
import { AnalysisSection } from '../components/AnalysisSection'
import { MunicipioCard } from '../components/MunicipioCard'
import MapaBrasil from '../components/MapaBrasil/MapaBrasil'
import { Methodology } from '../components/Methodology'
import { SearchFilters, type Filtros } from '../components/SearchFilters'
import { SummaryCards } from '../components/SummaryCards'
import { ANO_FIM, ANO_INICIO, MUNICIPIO_PADRAO, mediaPeriodo, mesFinalDoAno, mesInicialDoAno, registrarSerieReal, type Municipio, type SerieClima } from '../data/climate'
import { carregarClima, carregarMunicipio, carregarMunicipios } from '../data/api'

const PADRAO: Filtros = { municipio: MUNICIPIO_PADRAO, de: ANO_INICIO, ate: ANO_FIM }

export default function HomePage() {
  const [municipios, setMunicipios] = useState<Municipio[]>([])
  const [filtros, setFiltros] = useState<Filtros>(PADRAO)
  const [serie, setSerie] = useState<SerieClima | null>(null)
  const [enso, setEnso] = useState<{ year: number; month: number; enso_index: number | null }[]>([])
  const [carregando, setCarregando] = useState(true)
  const [erro, setErro] = useState('')
  const [versaoForm, setVersaoForm] = useState(0)
  const selecaoManual = useRef(false)
  const municipioAtual = useRef(filtros.municipio.ibge)
  const requisicaoDetalhes = useRef<AbortController | null>(null)

  useEffect(() => {
    carregarMunicipios().then((lista) => {
      setMunicipios(lista)
      const inicial = lista.find((m) => m.ibge === '5218805') ?? lista[0]
      if (inicial && !selecaoManual.current) {
        municipioAtual.current = inicial.ibge
        setFiltros((atual) => ({ ...atual, municipio: inicial }))
      }
    }).catch((e: unknown) => setErro(e instanceof Error ? e.message : 'Não foi possível carregar os municípios da API.'))
  }, [])

  useEffect(() => {
    const controller = new AbortController()
    const codigoIbge = filtros.municipio.ibge
    const { de, ate } = filtros
    setCarregando(true)
    setErro('')
    carregarClima(codigoIbge, de, ate, controller.signal).then(({ serie: dados, enso: indices }) => {
      if (controller.signal.aborted) return
      registrarSerieReal(codigoIbge, dados)
      setSerie(dados)
      setEnso(indices)
    }).catch((e: unknown) => {
      if (!controller.signal.aborted && !(e instanceof DOMException && e.name === 'AbortError')) {
        setSerie(null)
        setErro(e instanceof Error ? e.message : 'Não foi possível carregar os dados climáticos.')
      }
    }).finally(() => { if (!controller.signal.aborted) setCarregando(false) })
    return () => controller.abort()
  }, [filtros.municipio.ibge, filtros.de, filtros.ate])

  const mesDe = mesInicialDoAno(filtros.de)
  const mesAte = mesFinalDoAno(filtros.ate)
  const resumo = useMemo(() => serie ? ({
    temp: mediaPeriodo(serie.temp, mesDe, mesAte),
    chuva: mediaPeriodo(serie.chuva, mesDe, mesAte),
    umid: mediaPeriodo(serie.umid, mesDe, mesAte),
  }) : null, [serie, mesDe, mesAte])

  async function selecionarNoMapa(selecionado: { codigo: string; nome: string; uf: string }) {
    selecaoManual.current = true
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
        <p className="hero__lead">Temperatura, chuva e umidade de 2015 a 2025, com episódios de El Niño e La Niña em destaque.</p>
      </section>

      {erro && <p role="alert" className="filter-error">{erro}</p>}
      <SearchFilters key={versaoForm} aplicado={filtros} padrao={PADRAO} municipios={municipios} onAplicar={(f) => { selecaoManual.current = true; municipioAtual.current = f.municipio.ibge; requisicaoDetalhes.current?.abort(); setFiltros(f); setVersaoForm((v) => v + 1) }} />

      <section className="explore" aria-label="Mapa e dados do município">
        <MapaBrasil onSelectMunicipio={selecionarNoMapa} />
        <MunicipioCard municipio={filtros.municipio} />
      </section>

      {carregando && <section className="dashboard-loading" role="status" aria-live="polite" aria-busy="true">
        <div className="loading-message"><span className="loading-spinner" />Buscando dados climáticos de {filtros.municipio.nome}…</div>
        <div className="loading-kpis">{[0, 1, 2].map((item) => <div className="loading-skeleton loading-skeleton--kpi" key={item} />)}</div>
        <div className="loading-charts">{[0, 1, 2].map((item) => <div className="loading-skeleton loading-skeleton--chart" key={item} />)}</div>
      </section>}
      {resumo && !carregando && <>
        <SummaryCards {...resumo} />
        <AnalysisSection municipio={filtros.municipio} mesDe={mesDe} mesAte={mesAte} serie={serie!} enso={enso} />
      </>}
      <Methodology />
    </div>
  )
}
