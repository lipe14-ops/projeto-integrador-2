import { useId, useMemo, useState } from 'react'
import { ANOS, normalizar, rotuloMunicipio, type Municipio } from '../data/climate'
import { IconInfo, IconReset, IconSearch, IconSliders, IconX } from './Icons'

export interface Filtros {
  municipio: Municipio | null
  de: number
  ate: number
}

interface Props {
  aplicado: Filtros
  padrao: Filtros
  municipios: Municipio[]
  onAplicar: (f: Filtros) => void
  carregandoMunicipios?: boolean
}

export function SearchFilters({ aplicado, padrao, municipios, onAplicar, carregandoMunicipios = false }: Props) {
  const listId = useId()
  const [estado, setEstado] = useState(aplicado.municipio?.uf ?? '')
  const [texto, setTexto] = useState(aplicado.municipio ? rotuloMunicipio(aplicado.municipio) : '')
  const [de, setDe] = useState(aplicado.de)
  const [ate, setAte] = useState(aplicado.ate)
  const [aberto, setAberto] = useState(false)
  const [ativo, setAtivo] = useState(-1)
  const [erro, setErro] = useState<string | null>(null)

  const estados = useMemo(() => Array.from(new Map(
    municipios.map((m) => [m.uf, m.estado ? `${m.estado} — ${m.uf}` : m.uf]),
  ).entries()).sort((a, b) => a[1].localeCompare(b[1], 'pt-BR')), [municipios])
  const municipiosDoEstado = useMemo(() => municipios.filter((m) => m.uf === estado), [municipios, estado])

  const sugestoes = useMemo(() => {
    const t = normalizar(texto)
    const todos = municipiosDoEstado
    // mostra tudo quando o texto é exatamente o município aplicado
    if (!t || (aplicado.municipio && t === normalizar(rotuloMunicipio(aplicado.municipio)))) return todos.slice(0, 50)
    return todos.filter((m) => normalizar(rotuloMunicipio(m)).includes(t)).slice(0, 50)
  }, [texto, aplicado.municipio, municipiosDoEstado])

  function escolher(m: Municipio) {
    setTexto(rotuloMunicipio(m))
    setAberto(false)
    setAtivo(-1)
    setErro(null)
  }

  function aplicar() {
    const chave = normalizar(texto)
    if (!estado) {
      setErro('Escolha um estado antes de selecionar o município.')
      return
    }
    const m = municipiosDoEstado.find((municipio) => normalizar(rotuloMunicipio(municipio)) === chave || normalizar(municipio.nome) === chave)
      ?? (sugestoes.length === 1 ? sugestoes[0] : undefined)
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
    setEstado('')
    setTexto('')
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
      <div className="field field--state">
        <label className="field__label" htmlFor="estado">Estado</label>
        <select
          id="estado"
          className="input"
          value={estado}
          disabled={carregandoMunicipios || estados.length === 0}
          onChange={(e) => {
            setEstado(e.target.value)
            setTexto('')
            setAberto(false)
            setAtivo(-1)
            setErro(null)
          }}
        >
          <option value="">{carregandoMunicipios ? 'Carregando estados…' : 'Selecione um estado'}</option>
          {estados.map(([uf, nome]) => <option key={uf} value={uf}>{nome}</option>)}
        </select>
      </div>
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
              disabled={!estado}
              role="combobox"
              aria-expanded={aberto}
              aria-controls={listId}
              aria-autocomplete="list"
              aria-invalid={erro ? true : undefined}
              autoComplete="off"
              placeholder={estado ? 'Busque um município' : 'Escolha primeiro um estado'}
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
          {aberto && estado && (
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
