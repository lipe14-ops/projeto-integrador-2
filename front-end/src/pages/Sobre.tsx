export default function Sobre() {
  return (
    <div className="page page--narrow">
      <section className="hero" aria-labelledby="about-title">
        <p className="mono-label">Sobre o projeto</p>
        <h1 id="about-title">Entender o clima é entender o lugar</h1>
        <p className="hero__lead">
          O Clima Brasil reúne informações climáticas para aproximar as pessoas das características ambientais dos municípios brasileiros.
        </p>
      </section>
      <section className="card about-card">
        <h2 className="section-title">Conhecimento para todos</h2>
        <p>
          Nosso objetivo é apresentar dados de forma clara e acessível, apoiando a curiosidade, o aprendizado e a compreensão das diferenças entre as regiões do país.
        </p>
      </section>
    </div>
  )
}
