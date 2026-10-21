import { useMemo, useState } from 'react'
import { AnalysisSection } from '../components/AnalysisSection'
import { MunicipioCard } from '../components/MunicipioCard'
import MapaBrasil from '../components/MapaBrasil'
import { Methodology } from '../components/Methodology'
import { SearchFilters, type Filtros } from '../components/SearchFilters'
import { SummaryCards } from '../components/SummaryCards'
import { ANO_FIM, ANO_INICIO, MUNICIPIO_PADRAO, mediaPeriodo, mesFinalDoAno, mesInicialDoAno, serieDoMunicipio } from '../data/climate'

const PADRAO: Filtros = { municipio: MUNICIPIO_PADRAO, de: ANO_INICIO, ate: ANO_FIM }

export default function HomePage() {
  const [filtros, setFiltros] = useState<Filtros>(PADRAO)
  // muda a chave do formulário quando o mapa troca o município, para sincronizar o campo de busca
  const [versaoForm, setVersaoForm] = useState(0)

  const mesDe = mesInicialDoAno(filtros.de)
  const mesAte = mesFinalDoAno(filtros.ate)
  const resumo = useMemo(() => {
    const s = serieDoMunicipio(filtros.municipio)
    return {
      temp: mediaPeriodo(s.temp, mesDe, mesAte),
      chuva: mediaPeriodo(s.chuva, mesDe, mesAte),
      umid: mediaPeriodo(s.umid, mesDe, mesAte),
    }
  }, [filtros.municipio, mesDe, mesAte])

  return (
    <div className="page">
      <section className="hero" aria-labelledby="hero-titulo">
        <p className="mono-label">Projeto Integrador · Ciência da Computação</p>
        <h1 id="hero-titulo">Explore o clima de qualquer município do Brasil</h1>
        <p className="hero__lead">Temperatura, chuva e umidade desde 2010, com os episódios de El Niño e La Niña em destaque.</p>
      </section>

      <SearchFilters key={versaoForm} aplicado={filtros} padrao={PADRAO} onAplicar={(f) => setFiltros(f)} />

      <section className="explore" aria-label="Mapa e dados do município">
        <MapaBrasil onSelectMunicipio={(m: any) => console.log(m)} />
        <MunicipioCard municipio={filtros.municipio} />
      </section>

      <SummaryCards {...resumo} />

      <AnalysisSection municipio={filtros.municipio} mesDe={mesDe} mesAte={mesAte} />

      <Methodology />
    </div>
  )
}
