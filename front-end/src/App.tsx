import { useEffect, useState } from 'react'
import { Header, type Pagina } from './components/Header/Header'
import HomePage from './pages/HomePage'
import Sobre from './pages/Sobre'
import AnaliseEspacial from './pages/AnaliseEspacial'
import Inicio from './pages/Inicio'
import Estatisticas from './pages/Estatisticas'

/** Sub-abas da aba Estatísticas: o panorama climático e o mapa nacional de anomalias. */
function AbasEstatisticas({ pagina, onNavegar }: { pagina: Pagina; onNavegar: (p: Pagina) => void }) {
  const abas = [
    ['estatisticas', 'Panorama climático', 'Temperatura, chuva, umidade, regiões e ENSO'],
    ['analise', 'Mapa de anomalias', 'Frequência, intensidade e sazonalidade dos eventos'],
  ] as const
  return (
    <nav className="abas-secao" aria-label="Seções de Estatísticas">
      <div className="abas-secao__inner" role="tablist">
        {abas.map(([id, rotulo, descricao]) => (
          <button
            key={id}
            type="button"
            role="tab"
            aria-selected={pagina === id}
            className={pagina === id ? 'abas-secao__aba is-ativa' : 'abas-secao__aba'}
            onClick={() => onNavegar(id)}
          >
            <b>{rotulo}</b>
            <span>{descricao}</span>
          </button>
        ))}
      </div>
    </nav>
  )
}

const PAGINAS: Pagina[] = ['inicio', 'estatisticas', 'explorar', 'analise', 'sobre']

/** A página fica no hash (#estatisticas) para que cada uma tenha endereço próprio e o "voltar" funcione. */
function paginaDoHash(): Pagina {
  const h = window.location.hash.replace(/^#\/?/, '')
  return (PAGINAS as string[]).includes(h) ? (h as Pagina) : 'inicio'
}

function App() {
  const [pagina, setPagina] = useState<Pagina>(paginaDoHash)
  // Explorar, Estatísticas e Mapa nacional são montados na primeira visita
  // (baixam malha e séries) e depois ficam montados para não perder o estado
  const [visitadas, setVisitadas] = useState<Set<Pagina>>(() => new Set([paginaDoHash()]))

  useEffect(() => {
    function aoMudarHash() {
      const p = paginaDoHash()
      setPagina(p)
      setVisitadas((v) => (v.has(p) ? v : new Set(v).add(p)))
      window.scrollTo({ top: 0 })
    }
    window.addEventListener('hashchange', aoMudarHash)
    return () => window.removeEventListener('hashchange', aoMudarHash)
  }, [])

  function navegar(p: Pagina) {
    if (p === pagina) {
      window.scrollTo({ top: 0 })
      return
    }
    window.location.hash = p === 'inicio' ? '' : p
    if (p === 'inicio') {
      // hash vazio não dispara hashchange em todos os navegadores ao remover só o '#'
      history.replaceState(null, '', window.location.pathname + window.location.search)
      setPagina('inicio')
      window.scrollTo({ top: 0 })
    }
  }

  return (
    <div className="app-shell">
      <Header pagina={pagina} onNavegar={navegar} />
      <main>
        {pagina === 'inicio' && <Inicio onNavegar={navegar} />}
        {(pagina === 'estatisticas' || pagina === 'analise') && <AbasEstatisticas pagina={pagina} onNavegar={navegar} />}
        {visitadas.has('estatisticas') && (
          <div hidden={pagina !== 'estatisticas'}>
            <Estatisticas onNavegar={navegar} visivel={pagina === 'estatisticas'} />
          </div>
        )}
        {visitadas.has('explorar') && (
          <div hidden={pagina !== 'explorar'}>
            <HomePage />
          </div>
        )}
        {visitadas.has('analise') && (
          <div hidden={pagina !== 'analise'}>
            <AnaliseEspacial />
          </div>
        )}
        {pagina === 'sobre' && <Sobre />}
      </main>
    </div>
  )
}

export default App
