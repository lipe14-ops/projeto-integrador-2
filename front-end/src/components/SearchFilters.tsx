import { useId, useMemo, useState } from 'react'
import { ANOS, MUNICIPIOS, buscarMunicipio, normalizar, rotuloMunicipio, type Municipio } from '../data/climate'
import { IconInfo, IconReset, IconSearch, IconSliders, IconX } from './Icons'

export interface Filtros {
  municipio: Municipio
  de: number
  ate: number
}

interface Props {
  aplicado: Filtros
  padrao: Filtros
  onAplicar: (f: Filtros) => void
}

export function SearchFilters({ aplicado, padrao, onAplicar }: Props) {
  const listId = useId()
  const [texto, setTexto] = useState(rotuloMunicipio(aplicado.municipio))
  const [de, setDe] = useState(aplicado.de)
  const [ate, setAte] = useState(aplicado.ate)
  const [aberto, setAberto] = useState(false)
  const [ativo, setAtivo] = useState(-1)
  const [erro, setErro] = useState<string | null>(null)

  const sugestoes = useMemo(() => {
    const t = normalizar(texto)
    const todos = MUNICIPIOS
    // mostra tudo quando o texto é exatamente o município aplicado
    if (!t || t === normalizar(rotuloMunicipio(aplicado.municipio))) return todos
    return todos.filter((m) => normalizar(rotuloMunicipio(m)).includes(t))
  }, [texto, aplicado.municipio])

  function escolher(m: Municipio) {
    setTexto(rotuloMunicipio(m))
    setAberto(false)
    setAtivo(-1)
    setErro(null)
  }

  function aplicar() {
    const m = buscarMunicipio(texto) ?? (sugestoes.length === 1 ? sugestoes[0] : undefined)
    if (!m) {
      setErro('Município não encontrado. Escolha uma opção da lista.')
      setAberto(true)
      return
    }
    if (de > ate) {
      setErro('O ano inicial não pode ser maior que o ano final.')
      return
    }
    setErro(null)
    setTexto(rotuloMunicipio(m))
    onAplicar({ municipio: m, de, ate })
  }

  function limpar() {
    setTexto(rotuloMunicipio(padrao.municipio))
    setDe(padrao.de)
    setAte(padrao.ate)
    setErro(null)
    setAberto(false)
    onAplicar(padrao)
  }

  function aoTeclar(e: React.KeyboardEvent<HTMLInputElement>) {
    if (e.key === 'ArrowDown') {
      e.preventDefault()
      setAberto(true)
      setAtivo((i) => Math.min(sugestoes.length - 1, i + 1))
    } else if (e.key === 'ArrowUp') {
      e.preventDefault()
      setAtivo((i) => Math.max(0, i - 1))
    } else if (e.key === 'Enter') {
      e.preventDefault()
      if (aberto && ativo >= 0 && sugestoes[ativo]) escolher(sugestoes[ativo])
      else aplicar()
    } else if (e.key === 'Escape') {
      setAberto(false)
    }
  }

  return (
    <form
      className="card filters"
      onSubmit={(e) => {
        e.preventDefault()
        aplicar()
      }}
    >
      <div className="field field--grow">
        <label className="field__label" htmlFor="municipio">
          Município
        </label>
        <div className="combo">
          <div className="input-wrap">
            <IconSearch size={18} className="input-wrap__icon" />
            <input
              id="municipio"
              className="input input--search"
              type="text"
              role="combobox"
              aria-expanded={aberto}
              aria-controls={listId}
              aria-autocomplete="list"
              aria-invalid={erro ? true : undefined}
              autoComplete="off"
              placeholder="Busque um município"
              value={texto}
              onChange={(e) => {
                setTexto(e.target.value)
                setAberto(true)
                setAtivo(-1)
                setErro(null)
              }}
              onFocus={(e) => {
                e.currentTarget.select()
                setAberto(true)
              }}
              onBlur={() => setTimeout(() => setAberto(false), 120)}
              onKeyDown={aoTeclar}
            />
            {texto && (
              <button type="button" className="input-wrap__clear" aria-label="Limpar busca" onClick={() => setTexto('')}>
                <IconX size={18} />
              </button>
            )}
          </div>
          {aberto && (
            <ul id={listId} className="combo__list" role="listbox">
              {sugestoes.length === 0 && <li className="combo__empty">Nenhum município encontrado</li>}
              {sugestoes.map((m, i) => (
                <li
                  key={m.id}
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
      </div>

      <div className="field">
        <span className="field__label field__label--info">
          Período
          <span className="tip" tabIndex={0} aria-describedby="tip-periodo">
            <IconInfo size={18} />
            <span id="tip-periodo" role="tooltip" className="tip__bubble">
              Os dados mensais cobrem de janeiro de {ANOS[0]} a dezembro de {ANOS[ANOS.length - 1]}.
            </span>
          </span>
        </span>
        <div className="period">
          <select className="input input--mono" aria-label="Ano inicial" value={de} onChange={(e) => setDe(+e.target.value)}>
            {ANOS.map((a) => (
              <option key={a} value={a}>
                {a}
              </option>
            ))}
          </select>
          <span className="period__sep">até</span>
          <select className="input input--mono" aria-label="Ano final" value={ate} onChange={(e) => setAte(+e.target.value)}>
            {ANOS.map((a) => (
              <option key={a} value={a}>
                {a}
              </option>
            ))}
          </select>
        </div>
      </div>

      <div className="filters__actions">
        <button type="submit" className="btn btn--primary">
          <IconSliders size={18} />
          Aplicar filtros
        </button>
        <button type="button" className="btn btn--ghost" onClick={limpar}>
          <IconReset size={18} />
          Limpar
        </button>
      </div>
      {erro && (
        <p className="filters__error" role="alert">
          {erro}
        </p>
      )}
    </form>
  )
}
