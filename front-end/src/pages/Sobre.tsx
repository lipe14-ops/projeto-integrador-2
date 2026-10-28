import { IconCloudRain, IconCompare, IconDatabase, IconDroplets, IconSearch, IconThermometer, IconWaves } from '../components/Icons'

const indicadores = [
  {
    titulo: 'Temperatura',
    texto: 'Acompanhe a temperatura média do ar, em graus Celsius, por município e ao longo do período selecionado.',
    Icone: IconThermometer,
  },
  {
    titulo: 'Precipitação',
    texto: 'Consulte o volume de chuva acumulado em milímetros e observe sua variação entre meses e anos.',
    Icone: IconCloudRain,
  },
  {
    titulo: 'Umidade relativa',
    texto: 'Explore a umidade do ar em porcentagem, estimada a partir da temperatura e do ponto de orvalho.',
    Icone: IconDroplets,
  },
  {
    titulo: 'Fenômenos ENSO',
    texto: 'Veja nos gráficos os períodos associados ao El Niño e à La Niña para comparar com as séries climáticas.',
    Icone: IconWaves,
  },
]

export default function Sobre() {
  return (
    <div className="page page--about">
      <section className="hero" aria-labelledby="about-title">
        <p className="mono-label">Sobre o projeto</p>
        <h1 id="about-title">Entender o clima é entender o lugar</h1>
        <p className="hero__lead">
          O Clima Brasil é uma plataforma de consulta e visualização do histórico climático dos municípios brasileiros. Ela transforma séries de dados em gráficos acessíveis para ajudar você a conhecer e comparar as características climáticas de cada localidade.
        </p>
      </section>

      <section className="about-section" aria-labelledby="about-purpose">
        <div className="about-section__heading">
          <p className="mono-label">Propósito</p>
          <h2 id="about-purpose" className="section-title">Informação climática para explorar e aprender</h2>
        </div>
        <p>
          A plataforma foi criada para aproximar os dados climáticos do público. Estudantes, educadores, pesquisadores e pessoas curiosas podem consultar um município, observar mudanças ao longo do tempo e levantar perguntas sobre as diferenças entre regiões. Os gráficos apoiam a exploração e o aprendizado; não substituem uma análise técnica ou uma previsão do tempo.
        </p>
      </section>

      <section className="about-section" aria-labelledby="about-indicators">
        <div className="about-section__heading">
          <p className="mono-label">O que você encontra</p>
          <h2 id="about-indicators" className="section-title">Quatro perspectivas do clima</h2>
        </div>
        <div className="about-grid">
          {indicadores.map(({ titulo, texto, Icone }) => (
            <article className="card about-feature" key={titulo}>
              <Icone size={28} className="about-feature__icon" />
              <h3>{titulo}</h3>
              <p>{texto}</p>
            </article>
          ))}
        </div>
      </section>

      <section className="card about-card" aria-labelledby="about-how">
        <p className="mono-label">Como usar</p>
        <h2 id="about-how" className="section-title">Explore os dados em poucos passos</h2>
        <ol className="about-steps">
          <li><span>1</span><p><strong>Escolha uma localidade.</strong> Selecione o estado e o município nos filtros ou clique em um município disponível no mapa.</p></li>
          <li><span>2</span><p><strong>Defina o período.</strong> Escolha os anos que deseja analisar e aplique os filtros para atualizar os resultados.</p></li>
          <li><span>3</span><p><strong>Leia e compare.</strong> Passe pelos gráficos, compare com outro município e use o controle abaixo do gráfico para ampliar um intervalo. Você também pode baixar os dados exibidos em CSV.</p></li>
        </ol>
        <div className="about-callout"><IconSearch size={21} /><p>As faixas coloridas nos gráficos indicam episódios de El Niño e La Niña, facilitando a comparação visual com temperatura, chuva e umidade.</p></div>
      </section>

      <section className="about-section" aria-labelledby="about-sources">
        <div className="about-section__heading">
          <p className="mono-label">Origem e leitura dos dados</p>
          <h2 id="about-sources" className="section-title">Como interpretar as informações</h2>
        </div>
        <div className="about-grid about-grid--sources">
          <article className="card about-feature">
            <IconDatabase size={28} className="about-feature__icon" />
            <h3>Reanálise ERA5-Land</h3>
            <p>As variáveis climáticas vêm do ERA5-Land, produto de reanálise do Copernicus/ECMWF em grade aproximada de 9 km. Os valores são estimativas de modelo associadas aos municípios, não medições diretas de uma estação meteorológica local.</p>
          </article>
          <article className="card about-feature">
            <IconWaves size={28} className="about-feature__icon" />
            <h3>El Niño e La Niña</h3>
            <p>A identificação dos episódios usa o Índice Oceânico Niño (ONI), da NOAA/CPC. O critério apresentado considera anomalia de pelo menos +0,5 °C ou no máximo −0,5 °C por cinco trimestres consecutivos.</p>
          </article>
          <article className="card about-feature about-feature--wide">
            <IconCompare size={28} className="about-feature__icon" />
            <h3>Comparações com contexto</h3>
            <p>As séries ajudam a observar coincidências e diferenças no período selecionado. Uma associação visual entre um episódio ENSO e uma variável municipal não demonstra, por si só, que um fenômeno causou determinada condição local. Resultados também dependem da resolução e das limitações do conjunto de dados.</p>
          </article>
        </div>
      </section>
    </div>
  )
}
