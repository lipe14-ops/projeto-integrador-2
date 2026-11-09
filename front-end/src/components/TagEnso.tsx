import type { FaseEnso } from '../data/api'

const ROTULO: Record<Exclude<FaseEnso, 'neutral'>, string> = { el_nino: 'El Niño', la_nina: 'La Niña' }

/** Etiqueta da fase ENSO no mês do evento (ONI ≥ 0,5 El Niño; ≤ −0,5 La Niña). Neutro não gera etiqueta. */
export function TagEnso({ fase, oni }: { fase: FaseEnso | null; oni: number | null }) {
  if (!fase || fase === 'neutral') return null
  const valor = oni === null ? '' : ` (ONI ${oni > 0 ? '+' : ''}${oni.toLocaleString('pt-BR', { minimumFractionDigits: 1, maximumFractionDigits: 2 })})`
  return (
    <span
      className={`tag-enso tag-enso--${fase}`}
      title={`O evento ocorreu em um mês de ${ROTULO[fase]}${valor}. Contexto climático: não indica que o fenômeno causou a chuva.`}
    >
      {ROTULO[fase]}
    </span>
  )
}
