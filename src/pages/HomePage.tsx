import { useEffect, useMemo, useState } from 'react'
import { Alert, Col, Row, Spin } from 'antd'
import { AnalysisSection } from '../components/AnalysisSection'
import { MunicipioCard } from '../components/MunicipioCard'
import { Methodology } from '../components/Methodology'
import { SearchFilters, type Filtros } from '../components/SearchFilters'
import { SummaryCards } from '../components/SummaryCards'
import MapaBrasil from '../components/MapaBrasil/MapaBrasil'
import { ANO_FIM, ANO_INICIO, mediaPeriodo, mesFinalDoAno, mesInicialDoAno, registrarSerieReal, type Municipio, type SerieClima } from '../data/climate'
import { carregarClima, carregarMunicipios } from '../data/api'

export default function HomePage() {
  const [municipios, setMunicipios] = useState<Municipio[]>([])
  const [filtros, setFiltros] = useState<Filtros | null>(null)
  const [serie, setSerie] = useState<SerieClima | null>(null)
  const [enso, setEnso] = useState<{ year: number; month: number; enso_index: number | null }[]>([])
  const [carregandoLista, setCarregandoLista] = useState(true)
  const [carregandoClima, setCarregandoClima] = useState(false)
  const [erro, setErro] = useState('')

  useEffect(() => {
    carregarMunicipios().then((lista) => {
      setMunicipios(lista)
      const inicial = lista.find((m) => m.ibge === '5218805') ?? lista[0]
      if (inicial) setFiltros({ municipio: inicial, de: ANO_INICIO, ate: ANO_FIM })
    }).catch((e: unknown) => setErro(e instanceof Error ? e.message : 'Não foi possível carregar os municípios.'))
      .finally(() => setCarregandoLista(false))
  }, [])

  useEffect(() => {
    if (!filtros) return
    let ativo = true
    setCarregandoClima(true)
    setErro('')
    carregarClima(filtros.municipio, filtros.de, filtros.ate).then(({ serie: dados, enso: indices }) => {
      if (!ativo) return
      registrarSerieReal(filtros.municipio, dados)
      setSerie(dados)
      setEnso(indices)
    }).catch((e: unknown) => { if (ativo) { setSerie(null); setErro(e instanceof Error ? e.message : 'Não foi possível carregar os dados climáticos.') } })
      .finally(() => { if (ativo) setCarregandoClima(false) })
    return () => { ativo = false }
  }, [filtros])

  const mesDe = filtros ? mesInicialDoAno(filtros.de) : 0
  const mesAte = filtros ? mesFinalDoAno(filtros.ate) : 0
  const resumo = useMemo(() => serie ? ({
    temp: mediaPeriodo(serie.temp, mesDe, mesAte),
    chuva: mediaPeriodo(serie.chuva, mesDe, mesAte),
    umid: mediaPeriodo(serie.umid, mesDe, mesAte),
  }) : null, [serie, mesDe, mesAte])

  const selecionarNoMapa = (selecionado: { codigo: string }) => {
    const municipio = municipios.find((m) => m.ibge === selecionado.codigo)
    if (municipio && filtros) setFiltros({ ...filtros, municipio })
  }

  return (
    <div className="page">
      <section className="hero" aria-labelledby="hero-titulo">
        <h1 id="hero-titulo" style={{ fontSize: 40 }}>Explore o clima de qualquer município do Brasil</h1>
        <p className="hero__lead">Temperatura, chuva e umidade de 2015 a 2025, com os episódios de El Niño e La Niña em destaque.</p>
      </section>
      {erro && <Alert type="error" showIcon message="Falha ao carregar dados" description={erro} style={{ marginBottom: 16 }} />}
      {carregandoLista && <Spin tip="Carregando municípios da API…" />}
      {filtros && <>
        <SearchFilters municipios={municipios} filtros={filtros} onAplicar={setFiltros} carregando={carregandoLista} />
        <Row gutter={[16, 24]}>
          <Col xs={24} sm={24} lg={17}><MapaBrasil onSelectMunicipio={selecionarNoMapa} /></Col>
          <Col xs={24} sm={24} lg={7}><MunicipioCard municipio={filtros.municipio} /></Col>
        </Row>
        {carregandoClima && <Spin tip="Carregando dados climáticos…" />}
        {resumo && !carregandoClima && <>
          <SummaryCards {...resumo} />
          <AnalysisSection municipio={filtros.municipio} mesDe={mesDe} mesAte={mesAte} serie={serie!} enso={enso} />
        </>}
      </>}
      <Methodology />
    </div>
  )
}
