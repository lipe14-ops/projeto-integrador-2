import { GiEarthAmerica } from "react-icons/gi";

export type Pagina = 'explorar' | 'sobre'

interface HeaderProps {
  pagina: Pagina
  onNavegar: (p: Pagina) => void
}

export function Header({ pagina, onNavegar }: HeaderProps) {
  return (
    <header className="site-header">
      <div className="site-header__inner">
        <button type="button" className="brand" onClick={() => onNavegar('explorar')} aria-label="Clima Brasil — ir para Explorar">
          <GiEarthAmerica size={50} />
          <span className="brand__text">
            <span className="brand__title">Clima Brasil</span>
            <span className="brand__subtitle">Dados climáticos dos municípios brasileiros</span>
          </span>
        </button>
        <nav aria-label="Principal" className="main-nav">
          {(
            [
              ['explorar', 'Explorar'],
              ['sobre', 'Sobre'],
            ] as const
          ).map(([id, label]) => (
            <button
              key={id}
              type="button"
              className={pagina === id ? 'main-nav__link is-active' : 'main-nav__link'}
              aria-current={pagina === id ? 'page' : undefined}
              onClick={() => onNavegar(id)}
            >
              {label}
            </button>
          ))}
        </nav>
      </div>
    </header>
  )
}
