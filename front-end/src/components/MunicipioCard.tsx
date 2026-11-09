import { ANO_FIM, ANO_INICIO, rotuloMunicipio, type Municipio } from '../data/climate'


type Linha = [rotulo: string, valor: string | null | undefined, ajuda?: string]
interface Grupo { titulo: string; linhas: Linha[] }

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
  const densidade = municipio.populacao && municipio.areaKm2
    ? `${(municipio.populacao / municipio.areaKm2).toLocaleString('pt-BR', { maximumFractionDigits: 1 })} hab/km²`
    : null
  // grupos do "Mais informações": só aparecem linhas com valor
  const todos: Grupo[] = [
    {
      titulo: 'Divisão regional (IBGE)',
      linhas: [
        ['Mesorregião', municipio.mesorregiao],
        ['Microrregião', municipio.microrregiao],
      ],
    },
    {
      titulo: 'População',
      linhas: [['Densidade demográfica', densidade, 'População dividida pela área do município']],
    },
    {
      titulo: 'Relevo (geomorfologia IBGE)',
      linhas: [
        ['Domínio', municipio.dominioGeomorfologico, 'Domínio morfoestrutural: a grande estrutura geológica da área'],
        ['Região', municipio.regiaoGeomorfologica, 'Região geomorfológica: conjunto de formas de relevo semelhantes'],
        ['Unidade', municipio.geomorfologia, 'Unidade geomorfológica: a forma de relevo predominante no município'],
      ],
    },
    {
      titulo: 'Localização',
      linhas: [['Coordenadas da sede', `${municipio.lat.toFixed(5)}, ${municipio.lon.toFixed(5)}`]],
    },
  ]
  const grupos = todos
    .map((g) => ({ ...g, linhas: g.linhas.filter(([, v]) => v) }))
    .filter((g) => g.linhas.length > 0)

  return (
    <aside className="card municipio-card" aria-labelledby="municipio-titulo">
      <header className="municipio-card__cabecalho">
        <p className="mono-label">Município selecionado</p>
        <h2 id="municipio-titulo" className="municipio-card__title">
          {nome} — <span>{uf}</span>
        </h2>
      </header>
      {/* nome e UF ficam fixos; o restante rola dentro do cartão (altura do mapa) */}
      <div className="municipio-card__corpo">
        <dl className="data-list">
          {linhas.map(([k, v]) => (
            <div key={k} className="data-list__row">
              <dt>{k}</dt>
              <dd>{v}</dd>
            </div>
          ))}
        </dl>
        {grupos.map((g) => (
          <section key={g.titulo} className="municipio-mais__grupo" aria-label={g.titulo}>
            <h3>{g.titulo}</h3>
            <dl className="data-list">
              {g.linhas.map(([k, v, ajuda]) => (
                <div key={k} className="data-list__row">
                  <dt title={ajuda}>{k}</dt>
                  <dd>{v}</dd>
                </div>
              ))}
            </dl>
          </section>
        ))}
        {grupos.length > 0 && (
          <p className="municipio-mais__fonte">Fonte: IBGE (malha municipal 2025, estimativas de população e mapeamento geomorfológico).</p>
        )}
      </div>
    </aside>
  )
}
