// Componentes compartilhados das páginas Início e Estatísticas (identidade visual do site).
import type { ReactNode } from 'react'

export function Bloco({ id, titulo, intro, variante, children }: {
  id?: string
  titulo: string
  intro?: ReactNode
  variante?: 'alerta' | 'exemplo'
  children: ReactNode
}) {
  const classe = variante ? `ed-bloco ed-bloco--${variante}` : 'ed-bloco'
  const idTitulo = id ? `${id}-titulo` : undefined
  return (
    <section id={id} className={classe} aria-labelledby={idTitulo}>
      <h2 id={idTitulo} className="ed-bloco__titulo">{titulo}</h2>
      {intro && <p className="ed-bloco__intro">{intro}</p>}
      {children}
    </section>
  )
}

/** Figura numerada: título, unidade, controles, gráfico e legenda "Figura N.". */
export function Figura({ numero, titulo, unidade, controles, legenda, children }: {
  numero?: number
  titulo: string
  unidade?: string
  controles?: ReactNode
  legenda?: ReactNode
  children: ReactNode
}) {
  return (
    <figure className="ed-figura">
      <div className="ed-figura__cabeca">
        <div>
          <h3 className="ed-figura__titulo">{titulo}</h3>
          {unidade && <p className="ed-figura__unidade">{unidade}</p>}
        </div>
        {controles}
      </div>
      {children}
      {legenda && (
        <figcaption>
          {numero !== undefined && <b>Figura {numero}. </b>}
          {legenda}
        </figcaption>
      )}
    </figure>
  )
}

export function Segmentos<T extends string>({ rotulo, opcoes, valor, onChange }: {
  rotulo: string
  opcoes: readonly (readonly [T, string])[]
  valor: T
  onChange: (v: T) => void
}) {
  return (
    <div className="ed-segmentos" role="group" aria-label={rotulo}>
      {opcoes.map(([id, texto]) => (
        <button key={id} type="button" aria-pressed={valor === id} onClick={() => onChange(id)}>{texto}</button>
      ))}
    </div>
  )
}

export function Estado({ tipo, children, altura }: { tipo: 'carregando' | 'erro' | 'vazio'; children?: ReactNode; altura?: number }) {
  if (tipo === 'carregando') {
    return <div className="ed-carregando" style={{ height: altura ?? 240 }} role="status" aria-label={typeof children === 'string' ? children : 'Carregando'} />
  }
  return (
    <div className={tipo === 'erro' ? 'ed-estado ed-estado--erro' : 'ed-estado'} role={tipo === 'erro' ? 'alert' : 'status'} style={{ minHeight: altura }}>
      {children}
    </div>
  )
}

export function ItemLegenda({ cor, texto, linha }: { cor: string; texto: string; linha?: boolean }) {
  return <li><i className={linha ? 'linha' : undefined} style={{ background: cor }} />{texto}</li>
}
