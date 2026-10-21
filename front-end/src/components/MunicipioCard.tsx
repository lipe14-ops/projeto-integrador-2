import { ANO_FIM, ANO_INICIO, rotuloMunicipio, type Municipio } from '../data/climate'

const fmtCoord = (v: number, pos: string, neg: string) => `${Math.abs(v).toFixed(2)}° ${v >= 0 ? pos : neg}`

export function MunicipioCard({ municipio }: { municipio: Municipio }) {
  const [nome, uf] = rotuloMunicipio(municipio).split(' — ')
  const populacao = municipio.populacao == null ? '—' : `${municipio.populacao.toLocaleString('pt-BR')}${municipio.anoPopulacao ? ` (${municipio.anoPopulacao})` : ''}`
  const area = municipio.areaKm2 == null ? '—' : `${municipio.areaKm2.toLocaleString('pt-BR')} km²`
  const linhas: [string, string][] = [
    ['Código IBGE', municipio.ibge],
    ['Dados', `${ANO_INICIO}-${ANO_FIM}`],
    ...(municipio.estado ? [['Estado', municipio.estado] as [string, string]] : []),
    ['Região', municipio.regiao],
    ['População', populacao],
    ['Bioma', municipio.bioma ?? '—'],
    ['Área', area],
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
