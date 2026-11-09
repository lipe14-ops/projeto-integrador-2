import { useState } from 'react'
import { descreverAnomalia, formatarPeriodo, type EventoChuva, type Rotulo } from '../data/eventos'
import { IconAlert, IconChevronDown, IconExternal, IconNews } from './Icons'
import { TagEnso } from './TagEnso'

interface Props {
  municipio: string
  eventos: EventoChuva[]
  descartadas: number
  carregando: boolean
  erro: string
  semAnalise: boolean
  periodo: string
  onVerNoGrafico?: (evento: EventoChuva) => void
}

const NOTICIAS_VISIVEIS = 3
const fmtData = (iso: string | null) =>
  iso ? new Date(iso).toLocaleDateString('pt-BR', { day: '2-digit', month: 'short', year: 'numeric', timeZone: 'America/Sao_Paulo' }) : 'data não informada'

function Selo({ rotulo, prefixo }: { rotulo: Rotulo; prefixo: string }) {
  return (
    <span className={`selo selo--${rotulo.nivel}`} title={rotulo.explicacao}>
      <span className="sr-only">{prefixo}: </span>
      {rotulo.texto}
    </span>
  )
}

function Evento({ evento, onVerNoGrafico }: { evento: EventoChuva; onVerNoGrafico?: Props['onVerNoGrafico'] }) {
  const [todas, setTodas] = useState(false)
  const noticias = todas ? evento.noticias : evento.noticias.slice(0, NOTICIAS_VISIVEIS)
  const extras = evento.noticias.length - NOTICIAS_VISIVEIS
  return (
    <li className="evento">
      <div className="evento__head">
        <div>
          <h4 className="evento__data">{formatarPeriodo(evento.inicio, evento.fim)}</h4>
          <p className="evento__resumo">
            {evento.anomalias
              .slice()
              .sort((a, b) => a.dias - b.dias)
              .map((a) => descreverAnomalia(a))
              .join(' · ')}
          </p>
        </div>
      </div>
      <div className="evento__selos">
        <Selo rotulo={evento.avaliacao} prefixo="Para o local" />
        {evento.impacto && <Selo rotulo={evento.impacto} prefixo="Impacto" />}
        <TagEnso fase={evento.faseEnso} oni={evento.oni} />
      </div>
      <div className="evento__noticias">
          <p className="evento__noticias-titulo">
            <IconNews size={16} /> {evento.noticias.length} {evento.noticias.length === 1 ? 'notícia verificada' : 'notícias verificadas'}
          </p>
          <ul>
            {noticias.map((n) => (
              <li key={n.id}>
                <a href={n.url} target="_blank" rel="noopener noreferrer">
                  {n.manchete}
                  <IconExternal size={14} className="evento__externo" />
                  <span className="sr-only"> (abre em nova aba)</span>
                </a>
                <span className="evento__fonte">
                  {n.fonte ?? 'Fonte não identificada'} · {fmtData(n.publicadaEm)}
                  {n.relevancia === 'regional' && ' · cita município vizinho'}
                </span>
              </li>
            ))}
          </ul>
          {extras > 0 && (
            <button type="button" className="link-btn" aria-expanded={todas} onClick={() => setTodas((v) => !v)}>
              {todas ? 'Mostrar menos' : `Ver mais ${extras} ${extras === 1 ? 'notícia' : 'notícias'}`}
            </button>
          )}
        </div>
      {onVerNoGrafico && (
        <button type="button" className="btn btn--ghost evento__ver" onClick={() => onVerNoGrafico(evento)}>
          Ver no gráfico
        </button>
      )}
    </li>
  )
}

export function EventosExtremos({ municipio, eventos, descartadas, carregando, erro, semAnalise, periodo, onVerNoGrafico }: Props) {
  const [metodoAberto, setMetodoAberto] = useState(false)
  const totalNoticias = eventos.reduce((soma, e) => soma + e.noticias.length, 0)

  return (
    <section id="noticias-eventos" className="card eventos" aria-labelledby="eventos-titulo">
      <header className="eventos__head">
        <span className="eventos__icone" aria-hidden="true"><IconAlert size={20} /></span>
        <div>
          <h3 id="eventos-titulo">Eventos de chuva extrema</h3>
          <p>
            Dias e períodos em que choveu muito acima do esperado para {municipio} e que tiveram notícias da época
            confirmadas na página original. Eventos sem notícia verificada não são listados.
          </p>
        </div>
      </header>

      {carregando && <p className="eventos__estado" role="status"><span className="loading-spinner" />Buscando eventos e notícias…</p>}
      {!carregando && erro && <p className="eventos__estado eventos__estado--erro" role="alert">{erro}</p>}
      {!carregando && !erro && semAnalise && (
        <p className="eventos__estado">
          A análise de eventos extremos ainda não foi feita para {municipio}. Por enquanto ela está disponível para os
          municípios já processados pela equipe.
        </p>
      )}
      {!carregando && !erro && !semAnalise && (
        <>
          <p className="eventos__contagem" aria-live="polite">
            {eventos.length === 0
              ? `Nenhum evento de chuva extrema com notícia verificada em ${periodo}.`
              : `${eventos.length} ${eventos.length === 1 ? 'evento' : 'eventos'} com notícias verificadas em ${periodo} (${totalNoticias} ${totalNoticias === 1 ? 'notícia' : 'notícias'}).`}
            {' '}Os eventos aparecem como ▼ no gráfico de precipitação.
          </p>
          {eventos.length > 0 && <ol className="eventos__lista">{eventos.map((e) => <Evento key={e.id} evento={e} onVerNoGrafico={onVerNoGrafico} />)}</ol>}
        </>
      )}

      <div className="eventos__metodo">
        <button type="button" className="link-btn" aria-expanded={metodoAberto} onClick={() => setMetodoAberto((v) => !v)}>
          Como os eventos são identificados
          <IconChevronDown size={16} className={metodoAberto ? 'is-open' : undefined} />
        </button>
        {metodoAberto && (
          <ul>
            <li><b>Chuva fora do padrão em um dia:</b> um modelo estatístico (ARIMA) prevê a chuva de cada dia a partir dos dias anteriores; o dia entra quando a chuva fica muito acima da previsão (escore Z acima de 3).</li>
            <li><b>Vários dias seguidos de chuva:</b> somas de 3 e 5 dias acima de 99% dos períodos iguais dos anos anteriores. Isso captura episódios longos, como a enchente de maio de 2024 no RS, que o modelo diário não destaca.</li>
            <li><b>Revisão:</b> cada caso é avaliado em relação ao clima local e ao potencial de impacto. {descartadas > 0 ? `${descartadas} ${descartadas === 1 ? 'caso foi descartado' : 'casos foram descartados'} neste período por serem chuvas comuns no local.` : 'Nenhum caso foi descartado neste período.'}</li>
            <li><b>Notícias:</b> buscadas de 3 dias antes a 7 dias depois de cada evento e verificadas automaticamente na página original (manchete, fonte, data, tema e município). A verificação é automática e pode errar: confira a matéria antes de citá-la. Dados de reanálise ERA5-Land (~9 km) podem subestimar chuvas muito localizadas.</li>
          </ul>
        )}
      </div>
    </section>
  )
}
