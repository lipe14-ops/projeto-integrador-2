// Peças comuns dos gráficos das Estatísticas gerais (Recharts).
import type { TooltipContentProps } from 'recharts'
import type { NameType, ValueType } from 'recharts/types/component/DefaultTooltipContent'
import { fmt } from '../../data/estatisticas'

export const EIXO = { stroke: '#8a8a8a', fontSize: 12, tickLine: false } as const
export const GRADE = { stroke: '#e6e6e6', strokeDasharray: '0', vertical: false } as const

type Nomeador = (chave: string) => string

/** Tooltip padrão: título + uma linha por série, com a cor da série ao lado (o texto fica em tinta). */
export function tooltipEd(opts: { unidade: string; casas: number; nome?: Nomeador; titulo?: (label: unknown, payload: unknown) => string; extra?: (payload: Record<string, unknown>) => string | null }) {
  return function Dica({ active, payload, label }: TooltipContentProps<ValueType, NameType>) {
    if (!active || !payload?.length) return null
    const p0 = payload[0].payload as Record<string, unknown>
    const titulo = opts.titulo ? opts.titulo(label, p0) : String(label)
    const extra = opts.extra?.(p0)
    return (
      <div className="ed-tooltip">
        <div className="ed-tooltip__titulo">{titulo}</div>
        {payload.map((item) => (
          <div key={String(item.dataKey)} className="ed-tooltip__linha">
            <span><i style={{ background: item.color as string }} />{opts.nome ? opts.nome(String(item.dataKey)) : item.name}</span>
            <b>{fmt(item.value as number | null, opts.casas)} {opts.unidade}</b>
          </div>
        ))}
        {extra && <div style={{ marginTop: 4, color: '#5f6b6b' }}>{extra}</div>}
      </div>
    )
  }
}
