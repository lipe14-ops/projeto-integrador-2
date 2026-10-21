import { useMemo, useState } from 'react'
import {
  EPISODIOS_ENSO,
  MUNICIPIOS,
  agregar,
  janelaEmMeses,
  rotuloMunicipio,
  serieDoMunicipio,
  type Granularidade,
  type Janela,
  type Municipio,
} from '../data/climate'
import { IconChevronDown, IconCompare } from './Icons'
import { TimeSeriesChart, type SerieGrafico } from './TimeSeriesChart'

interface Props {
  municipio: Municipio
  mesDe: number
  mesAte: number
}

const COR_COMPARACAO = '#7a5aa6'
const JANELAS: [Janela, string][] = [
  ['12m', '12 meses'],
  ['5a', '5 anos'],
  ['10a', '10 anos'],
  ['custom', 'Personalizado'],
]
const slug = (s: string) => s.normalize('NFD').replace(/[\u0300-\u036f]/g, '').replace(/[^a-z0-9]+/gi, '-').toLowerCase()

export function AnalysisSection({ municipio, mesDe, mesAte }: Props) {
  const [gran, setGran] = useState<Granularidade>('mensal')
  const [janela, setJanela] = useState<Janela>('custom')
  const [comparando, setComparando] = useState(false)
  const [outroId, setOutroId] = useState<string>('')

  const outro = comparando ? MUNICIPIOS.find((m) => m.id === outroId) : undefined
  const janelaEfetiva: Janela = gran === 'anual' && janela === '12m' ? '5a' : janela
  const [ini, fim] = janelaEmMeses(janelaEfetiva, mesDe, mesAte)

  const graficos = useMemo(() => {
    const monta = (campo: 'temp' | 'chuva' | 'umid', cor: string, modo: 'media' | 'soma'): SerieGrafico[] => {
      const lista: [Municipio, string][] = [[municipio, cor]]
      if (outro) lista.push([outro, COR_COMPARACAO])
      return lista.map(([m, c]) => ({
        nome: rotuloMunicipio(m),
        cor: c,
        pontos: agregar(serieDoMunicipio(m)[campo], ini, fim, gran, modo),
      }))
    }
    return {
      temp: monta('temp', '#c0562b', 'media'),
      chuva: monta('chuva', '#1769a8', 'soma'),
      umid: monta('umid', '#2f7d5b', 'media'),
    }
  }, [municipio, outro, ini, fim, gran])

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
        <div className="analysis__controls">
          <div className="segmented" role="group" aria-label="Granularidade">
            {(
              [
                ['mensal', 'Mensal'],
                ['anual', 'Anual'],
              ] as const
            ).map(([id, label]) => (
              <button key={id} type="button" className={gran === id ? 'is-active' : ''} aria-pressed={gran === id} onClick={() => setGran(id)}>
                {label}
              </button>
            ))}
          </div>
          <div className="segmented" role="group" aria-label="Intervalo de tempo">
            {JANELAS.map(([id, label]) => (
              <button
                key={id}
                type="button"
                className={janelaEfetiva === id ? 'is-active' : ''}
                aria-pressed={janelaEfetiva === id}
                disabled={gran === 'anual' && id === '12m'}
                onClick={() => setJanela(id)}
              >
                {label}
              </button>
            ))}
          </div>
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
          episodios={EPISODIOS_ENSO}
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
          episodios={EPISODIOS_ENSO}
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
          episodios={EPISODIOS_ENSO}
          decimais={0}
          altura={400}
          passoY={5}
          arquivo={arq('umidade-relativa-media')}
        />
      </div>
    </section>
  )
}
