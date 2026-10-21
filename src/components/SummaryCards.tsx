import { Card } from 'antd'
import { IconCloudRain, IconDroplets, IconThermometer } from './Icons'

interface Props {
  temp: number
  chuva: number
  umid: number
}

const fmt = (v: number, d: number) => v.toLocaleString('pt-BR', { minimumFractionDigits: d, maximumFractionDigits: d })

export function SummaryCards({ temp, chuva, umid }: Props) {
  const itens = [
    { cls: 'kpi--temp', titulo: 'Temperatura média', valor: fmt(temp, 1), unidade: '°C', legenda: 'média do período', Icone: IconThermometer },
    { cls: 'kpi--rain', titulo: 'Precipitação', valor: fmt(chuva, 0), unidade: 'mm', legenda: 'média mensal acumulada', Icone: IconCloudRain },
    { cls: 'kpi--hum', titulo: 'Umidade relativa', valor: fmt(umid, 0), unidade: '%', legenda: 'média do período', Icone: IconDroplets },
  ]
  return (
    <section className="kpis" aria-label="Resumo do período">
      {itens.map(({ cls, titulo, valor, unidade, legenda, Icone }) => (
        // <article key={titulo} className={`card kpi ${cls}`}>
        <Card size='small' className={`card kpi ${cls}`}>
          <header className="kpi__head">
            <h3>{titulo}</h3>
            <Icone size={26} />
          </header>
          <p className="kpi__value">
            {valor}
            <span>{unidade}</span>
          </p>
          <p className="kpi__caption">{legenda}</p>
        </Card>
        // </article>
      ))}
    </section>
  )
}
