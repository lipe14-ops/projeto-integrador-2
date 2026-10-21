import { ANO_FIM, ANO_INICIO, rotuloMunicipio, type Municipio } from '../data/climate'

const fmtCoord = (v: number, pos: string, neg: string) => `${Math.abs(v).toFixed(2)}° ${v >= 0 ? pos : neg}`

export function MunicipioCard({ municipio }: { municipio: Municipio }) {
  const [nome, uf] = rotuloMunicipio(municipio).split(' — ')
  const linhas: [string, string][] = [
    ['Código IBGE', municipio.ibge],
    ['Dados', `${ANO_INICIO}-${ANO_FIM}`],
    ['Atualização', 'março de 2026'],
    ['Região', municipio.regiao],
    ['Localização', `${fmtCoord(municipio.lat, 'N', 'S')}, ${fmtCoord(municipio.lon, 'L', 'O')}`],
  ]
  return (
    <aside className="card municipio-card" aria-labelledby="municipio-titulo">
      <p className="mono-label">Município selecionado</p>
      <h2 id="municipio-titulo" className="municipio-card__title">
        {nome} — <span>{uf}</span>
      </h2>
      <dl className="data-list">
        {linhas.map(([k, v]) => (
          <div key={k} className="data-list__row">
            <dt>{k}</dt>
            <dd>{v}</dd>
          </div>
        ))}
      </dl>
    </aside>
  )
}
