import { useId, useMemo, useState } from 'react'
import { normalizar, rotuloMunicipio, type Municipio } from '../data/climate'
import { IconSearch, IconX } from './Icons'

interface Props {
  id: string
  municipios: Municipio[]
  selecionado: Municipio | undefined
  onSelecionar: (m: Municipio | undefined) => void
  placeholder?: string
}

const LIMITE = 30

/** Campo de busca de município (combobox acessível), reutilizando o estilo dos filtros. */
export function BuscaMunicipio({ id, municipios, selecionado, onSelecionar, placeholder = 'Digite o nome do município' }: Props) {
  const listId = useId()
  const [texto, setTexto] = useState(selecionado ? rotuloMunicipio(selecionado) : '')
  const [aberto, setAberto] = useState(false)
  const [ativo, setAtivo] = useState(-1)

  const sugestoes = useMemo(() => {
    const t = normalizar(texto)
    if (t.length < 2) return []
    // começa com o texto primeiro, depois contém o texto
    const comeca: Municipio[] = []
    const contem: Municipio[] = []
    for (const m of municipios) {
      const nome = normalizar(rotuloMunicipio(m))
      if (nome.startsWith(t)) comeca.push(m)
      else if (nome.includes(t)) contem.push(m)
      if (comeca.length >= LIMITE) break
    }
    return [...comeca, ...contem].slice(0, LIMITE)
  }, [texto, municipios])

  function escolher(m: Municipio) {
    setTexto(rotuloMunicipio(m))
    setAberto(false)
    setAtivo(-1)
    onSelecionar(m)
  }

  return (
    <div className="combo">
      <div className="input-wrap">
        <IconSearch size={18} className="input-wrap__icon" />
        <input
          id={id}
          className="input input--search"
          type="text"
          role="combobox"
          aria-expanded={aberto && sugestoes.length > 0}
          aria-controls={listId}
          aria-autocomplete="list"
          aria-activedescendant={ativo >= 0 ? `${listId}-${ativo}` : undefined}
          autoComplete="off"
          placeholder={placeholder}
          value={texto}
          onChange={(e) => {
            setTexto(e.target.value)
            setAberto(true)
            setAtivo(-1)
          }}
          onFocus={(e) => {
            e.currentTarget.select()
            setAberto(true)
          }}
          onBlur={() => setTimeout(() => setAberto(false), 120)}
          onKeyDown={(e) => {
            if (e.key === 'ArrowDown') {
              e.preventDefault()
              setAberto(true)
              setAtivo((i) => Math.min(sugestoes.length - 1, i + 1))
            } else if (e.key === 'ArrowUp') {
              e.preventDefault()
              setAtivo((i) => Math.max(0, i - 1))
            } else if (e.key === 'Enter') {
              e.preventDefault()
              const m = sugestoes[ativo >= 0 ? ativo : 0]
              if (m) escolher(m)
            } else if (e.key === 'Escape') {
              setAberto(false)
            }
          }}
        />
        {texto && (
          <button
            type="button"
            className="input-wrap__clear"
            aria-label="Limpar busca"
            onClick={() => {
              setTexto('')
              onSelecionar(undefined)
            }}
          >
            <IconX size={18} />
          </button>
        )}
      </div>
      {aberto && normalizar(texto).length >= 2 && (
        <ul id={listId} className="combo__list" role="listbox">
          {sugestoes.length === 0 && <li className="combo__empty">Nenhum município encontrado</li>}
          {sugestoes.map((m, i) => (
            <li
              key={m.ibge}
              id={`${listId}-${i}`}
              role="option"
              aria-selected={i === ativo}
              className={i === ativo ? 'combo__item is-active' : 'combo__item'}
              onMouseDown={(e) => {
                e.preventDefault()
                escolher(m)
              }}
              onMouseEnter={() => setAtivo(i)}
            >
              {rotuloMunicipio(m)}
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
