import { useState } from 'react'
import { Header, type Pagina } from './components/Header/Header'
import HomePage from './pages/HomePage'
import Sobre from './pages/Sobre'

function App() {
  const [pagina, setPagina] = useState<Pagina>('explorar')

  function navegar(p: Pagina) {
    setPagina(p)
    window.scrollTo({ top: 0 })
  }

  return (
    <div className="app-shell">
      <Header pagina={pagina} onNavegar={navegar} />
      <main>
        <div hidden={pagina !== 'explorar'}>
          <HomePage />
        </div>
        {pagina === 'sobre' && <Sobre />}
      </main>
    </div>
  )
}

export default App
