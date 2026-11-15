import { GiEarthAmerica } from "react-icons/gi";

export type Pagina = 'inicio' | 'estatisticas' | 'explorar' | 'analise' | 'sobre'

interface HeaderProps {
  pagina: Pagina
  onNavegar: (p: Pagina) => void
}

export function Header({ pagina, onNavegar }: HeaderProps) {
  return (
    <header className="site-header">
      <div className="site-header__inner">
        <button type="button" className="brand" onClick={() => onNavegar('inicio')} aria-label="Clima Brasil — ir para o início">
          <GiEarthAmerica size={50} />
          <span className="brand__text">
            <span className="brand__title">Clima Brasil</span>
            <span className="brand__subtitle">Dados climáticos dos municípios brasileiros</span>
          </span>
        </button>
        <nav aria-label="Principal" className="main-nav">
          {(
            [
              ['inicio', 'Início'],
              ['estatisticas', 'Estatísticas'],
              ['explorar', 'Explorar'],
              ['sobre', 'Sobre'],
            ] as const
          ).map(([id, label]) => {
            // "Estatísticas" reúne o panorama climático e o mapa nacional de anomalias (#analise)
            const ativo = pagina === id || (id === 'estatisticas' && pagina === 'analise')
            return (
              <button
                key={id}
                type="button"
                className={ativo ? 'main-nav__link is-active' : 'main-nav__link'}
                aria-current={ativo ? 'page' : undefined}
                onClick={() => onNavegar(id)}
              >
                {label}
              </button>
            )
          })}
        </nav>
      </div>
    </header>
  )
}
