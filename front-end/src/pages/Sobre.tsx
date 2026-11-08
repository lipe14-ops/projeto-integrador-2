import { FaTemperatureQuarter } from 'react-icons/fa6'
import { FiCloudRain } from 'react-icons/fi'
import { MdOutlineWaterDrop } from 'react-icons/md'
import { LuWaves } from 'react-icons/lu'
import { GoDatabase } from 'react-icons/go'
import { CiSearch } from 'react-icons/ci'


const indicadores = [
  {
    titulo: 'Temperatura',
    texto: 'Acompanhe a temperatura média do ar, em graus Celsius, por município e ao longo do período selecionado.',
    Icone: FaTemperatureQuarter,
  },
  {
    titulo: 'Precipitação',
    texto: 'Consulte o volume de chuva acumulado em milímetros e observe sua variação entre meses e anos.',
    Icone: FiCloudRain,
  },
  {
    titulo: 'Umidade relativa',
    texto: 'Explore a umidade do ar em porcentagem, estimada a partir da temperatura e do ponto de orvalho.',
    Icone: MdOutlineWaterDrop,
  },
  {
    titulo: 'Fenômenos ENSO',
    texto: 'Veja nos gráficos os períodos associados ao El Niño e à La Niña para comparar com as séries climáticas.',
    Icone: LuWaves,
  },
]

export default function Sobre() {
  return (
    <div className="page page--about">
      <section className="hero" aria-labelledby="about-title">
        <p className="mono-label">Sobre o projeto</p>
        <h1 id="about-title">Sobre o Clima Brasil</h1>
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
        <div className="about-callout"><CiSearch size={21} /><p>As faixas coloridas nos gráficos indicam episódios de El Niño e La Niña, facilitando a comparação visual com temperatura, chuva e umidade.</p></div>
      </section>

      <section className="about-section" aria-labelledby="about-sources">
        <div className="about-section__heading">
          <p className="mono-label">Origem e leitura dos dados</p>
          <h2 id="about-sources" className="section-title">Como interpretar as informações</h2>
        </div>
        <div className="about-grid about-grid--sources">
          <article className="card about-feature">
            <GoDatabase size={28} className="about-feature__icon" />
            <h3>Reanálise ERA5-Land</h3>
            <p>As variáveis climáticas vêm do ERA5-Land, produto de reanálise do Copernicus/ECMWF em grade aproximada de 9 km. Os valores são estimativas de modelo associadas aos municípios, não medições diretas de uma estação meteorológica local.</p>
          </article>
          <article className="card about-feature">
            <LuWaves size={28} className="about-feature__icon" />
            <h3>El Niño e La Niña</h3>
            <p>A identificação dos episódios usa o Índice Oceânico Niño (ONI), da NOAA/CPC. O critério apresentado considera anomalia de pelo menos +0,5 °C ou no máximo −0,5 °C por cinco trimestres consecutivos.</p>
          </article>
        </div>
      </section>

      <section className="about-section" aria-labelledby="about-climate-context">
        <div className="about-section__heading">
          <p className="mono-label">Entenda o contexto</p>
          <h2 id="about-climate-context" className="section-title">Reanálise climática e El Niño</h2>
        </div>
        <div className="about-grid">
          <article className="card about-feature">
            <GoDatabase size={28} className="about-feature__icon" />
            <h3>O que é uma reanálise climática?</h3>
            <p>É uma reconstrução consistente das condições do tempo no passado. Sistemas como o ERA5-Land combinam observações disponíveis — por exemplo, de estações, satélites e outras fontes — com modelos numéricos para estimar variáveis em uma grade espacial regular. Isso permite consultar áreas com poucas estações, mas os valores continuam sendo estimativas: podem diferir do que foi medido em um ponto específico.</p>
          </article>
          <article className="card about-feature">
            <LuWaves size={28} className="about-feature__icon" />
            <h3>Como o El Niño pode afetar o Brasil?</h3>
            <p>O El Niño altera a circulação atmosférica e pode influenciar os padrões de chuva e temperatura. Em termos gerais, costuma favorecer mais chuva no Sul e condições mais secas em partes do Norte e do Nordeste. A intensidade e a distribuição desses efeitos variam de um episódio para outro, conforme a estação e outros fatores climáticos; por isso, essa tendência não prevê o tempo de uma cidade específica.</p>
          </article>
          <p className="about-context-note">As faixas de El Niño e La Niña nos gráficos servem como referência para explorar coincidências nas séries. Elas não indicam, sozinhas, uma relação de causa e efeito para cada município.</p>
        </div>
      </section>
    </div>
  )
}
