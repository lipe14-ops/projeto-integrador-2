import { useId, useState, type ReactNode } from 'react'
import { IconChevronDown, IconDatabase, IconWaves } from './Icons'

const FAQ: { pergunta: string; resposta: ReactNode }[] = [
  {
    pergunta: 'O que é reanálise climática?',
    resposta:
      'É uma reconstrução do clima passado que combina observações (estações, satélites, balões) com um modelo numérico da atmosfera. O resultado é uma série contínua, em grade regular, mesmo onde não existem estações. Por isso os valores são estimativas e podem diferir de medições pontuais.',
  },
  {
    pergunta: 'Como El Niño e La Niña afetam o Brasil?',
    resposta:
      'Os efeitos variam por região. De forma geral, El Niño tende a deixar o Norte e o Nordeste mais secos e quentes e o Sul mais chuvoso; La Niña costuma inverter esse padrão. No Centro-Oeste a influência é mais sutil e depende da época do ano, por isso os episódios aparecem como faixas coloridas para você comparar com as séries.',
  },
]

function Item({ pergunta, resposta }: { pergunta: string; resposta: ReactNode }) {
  const [aberto, setAberto] = useState(false)
  const id = useId()
  return (
    <div className={aberto ? 'faq__item is-open' : 'faq__item'}>
      <h3>
        <button type="button" aria-expanded={aberto} aria-controls={id} onClick={() => setAberto((v) => !v)}>
          {pergunta}
          <IconChevronDown size={20} className="faq__chev" />
        </button>
      </h3>
      <div id={id} role="region" className="faq__panel" hidden={!aberto}>
        <p>{resposta}</p>
      </div>
    </div>
  )
}

export function Methodology() {
  return (
    <section className="card methodology" aria-labelledby="metodologia-titulo">
      <p className="mono-label">Metodologia</p>
      <h2 id="metodologia-titulo" className="section-title">
        Sobre os dados
      </h2>
      <div className="methodology__sources">
        <p>
          <IconDatabase size={26} />
          <span>
            <strong>ERA5-Land · Copernicus/ECMWF.</strong> Estimativas de reanálise climática em grade de ~9 km, agregadas por município. Não são medições diretas de estações locais.
          </span>
        </p>
        <p>
          <IconWaves size={26} />
          <span>
            <strong>El Niño e La Niña · NOAA/CPC.</strong> Períodos definidos pelo Índice Oceânico Niño (ONI), com anomalia de ±0,5 °C por 5 trimestres consecutivos.
          </span>
        </p>
      </div>
      <div className="faq">
        {FAQ.map((f) => (
          <Item key={f.pergunta} {...f} />
        ))}
      </div>
    </section>
  )
}
