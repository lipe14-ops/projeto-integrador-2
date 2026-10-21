import { useMemo, useState } from 'react'
import {
  MUNICIPIOS,
  agregar,
  janelaEmMeses,
  rotuloMunicipio,
  serieDoMunicipio,
  type Granularidade,
  type Janela,
  type Municipio,
  type SerieClima,
} from '../data/climate'
import { IconChevronDown, IconCompare } from './Icons'
import { TimeSeriesChart, type SerieGrafico } from './TimeSeriesChart'

interface Props {
  municipio: Municipio
  mesDe: number
  mesAte: number
  serie: SerieClima
  enso: { year: number; month: number; enso_index: number | null }[]
}

const COR_COMPARACAO = '#7a5aa6'
const JANELAS: [Janela, string][] = [
  ['12m', '12 meses'],
  ['5a', '5 anos'],
  ['10a', '10 anos'],
  ['custom', 'Personalizado'],
]
const slug = (s: string) => s.normalize('NFD').replace(/[\u0300-\u036f]/g, '').replace(/[^a-z0-9]+/gi, '-').toLowerCase()

export function AnalysisSection({ municipio, mesDe, mesAte, serie, enso }: Props) {
  const [gran, setGran] = useState<Granularidade>('mensal')
  const [janela, setJanela] = useState<Janela>('custom')
  const [comparando, setComparando] = useState(false)
  const [outroId, setOutroId] = useState<string>('')

  const outro = comparando ? MUNICIPIOS.find((m) => m.id === outroId) : undefined
  const janelaEfetiva: Janela = gran === 'anual' && janela === '12m' ? '5a' : janela
  const [ini, fim] = janelaEmMeses(janelaEfetiva, mesDe, mesAte)
  const episodios = useMemo(() => {
    const resultado: { tipo: 'el-nino' | 'la-nina'; inicio: number; fim: number }[] = []
    for (const item of enso) {
      const tipo = (item.enso_index ?? 0) >= 0.5 ? 'el-nino' : (item.enso_index ?? 0) <= -0.5 ? 'la-nina' : null
      if (!tipo) continue
      const mes = (item.year - 2015) * 12 + item.month - 1
      const anterior = resultado[resultado.length - 1]
      if (anterior?.tipo === tipo && anterior.fim === mes) anterior.fim++
      else resultado.push({ tipo, inicio: mes, fim: mes + 1 })
    }
    return resultado
  }, [enso])

  const graficos = useMemo(() => {
    const monta = (campo: 'temp' | 'chuva' | 'umid', cor: string, modo: 'media' | 'soma'): SerieGrafico[] => {
      const lista: [Municipio, string][] = [[municipio, cor]]
      if (outro) lista.push([outro, COR_COMPARACAO])
      return lista.map(([m, c], index) => ({
        nome: rotuloMunicipio(m),
        cor: c,
        pontos: agregar(index === 0 ? serie[campo] : serieDoMunicipio(m)[campo], ini, fim, gran, modo),
      }))
    }
    return {
      temp: monta('temp', '#c0562b', 'media'),
      chuva: monta('chuva', '#1769a8', 'soma'),
      umid: monta('umid', '#2f7d5b', 'media'),
    }
  }, [municipio, outro, ini, fim, gran, serie])

  const chave = `${municipio.id}-${outro?.id ?? 'x'}-${gran}-${ini}-${fim}`
  const arq = (nome: string) => `${nome}_${slug(municipio.nome)}-${slug(municipio.uf)}${outro ? `_vs_${slug(outro.nome)}` : ''}`

  return (
    <section className="analysis" aria-labelledby="analise-titulo">
      <div className="analysis__head">
        <div>
          <p className="mono-label">{rotuloMunicipio(municipio)}</p>
          <h2 id="analise-titulo" className="section-title">
            Análise climática
          </h2>
        </div>
        
      </div>

      <div className={comparando ? 'compare is-open' : 'compare'}>
        <button type="button" className="compare__toggle" aria-expanded={comparando} onClick={() => setComparando((v) => !v)}>
          <IconCompare size={20} />
          Comparar municípios
          <IconChevronDown size={18} className="compare__chev" />
        </button>
        {comparando && (
          <div className="compare__body">
            <label htmlFor="comparar-com">Comparar {municipio.nome} com</label>
            <select id="comparar-com" className="input" value={outroId} onChange={(e) => setOutroId(e.target.value)}>
              <option value="">Selecione um município</option>
              {MUNICIPIOS.filter((m) => m.id !== municipio.id).map((m) => (
                <option key={m.id} value={m.id}>
                  {rotuloMunicipio(m)}
                </option>
              ))}
            </select>
            {outro && (
              <button type="button" className="btn btn--ghost" onClick={() => setOutroId('')}>
                Remover comparação
              </button>
            )}
          </div>
        )}
      </div>

      <div className="charts">
        <TimeSeriesChart
          key={`t-${chave}`}
          className="charts__wide"
          titulo="Temperatura média"
          subtitulo="Temperatura do ar a 2 m · °C"
          unidade="°C"
          tipo="linha"
          series={graficos.temp}
          episodios={episodios}
          decimais={1}
          altura={420}
          passoY={1}
          arquivo={arq('temperatura-media')}
        />
        <TimeSeriesChart
          key={`p-${chave}`}
          titulo="Precipitação acumulada"
          subtitulo="Chuva total no período · mm"
          unidade="mm"
          tipo="barra"
          series={graficos.chuva}
          episodios={episodios}
          decimais={0}
          altura={400}
          passoY={5}
          dominioZero
          arquivo={arq('precipitacao-acumulada')}
        />
        <TimeSeriesChart
          key={`u-${chave}`}
          titulo="Umidade relativa média"
          subtitulo="Derivada da temperatura do ponto de orvalho · %"
          unidade="%"
          tipo="linha"
          series={graficos.umid}
          episodios={episodios}
          decimais={0}
          altura={400}
          passoY={5}
          arquivo={arq('umidade-relativa-media')}
        />
      </div>
    </section>
  )
}
