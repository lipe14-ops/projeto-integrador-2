import { useEffect, useId, useMemo, useState } from 'react'
import { carregarAnomalias, carregarClima, carregarNoticias, type AnomaliaChuva, type NoticiaVerificada } from '../data/api'
import { agruparEventos, descreverAnomalia, formatarPeriodo, mesDoDia, type EventoChuva } from '../data/eventos'
import {
  ANO_INICIO,
  agregar,
  janelaEmMeses,
  rotuloMunicipio,
  type Granularidade,
  type Janela,
  type Municipio,
  type SerieClima,
} from '../data/climate'
import { DESCRICAO_METODO, type MetodoEstacao } from '../data/seasons'
import { BuscaMunicipio } from './BuscaMunicipio'
import { EventosExtremos } from './EventosExtremos'
import { IconChevronDown, IconCompare } from './Icons'
import { TimeSeriesChart, type Marcador, type SerieGrafico } from './TimeSeriesChart'

interface Props {
  municipio: Municipio
  municipios: Municipio[]
  mesDe: number
  mesAte: number
  serie: SerieClima
  enso: { year: number; month: number; enso_index: number | null }[]
}

type OpcaoEstacao = MetodoEstacao | 'oculto'

const COR_COMPARACAO = '#7a5aa6'
const SYNC_ID = 'clima-municipio'
const OPCOES_ESTACAO: { valor: OpcaoEstacao; rotulo: string }[] = [
  { valor: 'astronomica', rotulo: 'Pelo calendário' },
  { valor: 'meteorologica', rotulo: 'Em trimestres' },
  { valor: 'oculto', rotulo: 'Ocultar' },
]
const slug = (s: string) => s.normalize('NFD').replace(/[̀-ͯ]/g, '').replace(/[^a-z0-9]+/gi, '-').toLowerCase()

interface SerieComparacao {
  chave: string
  serie?: SerieClima
  erro?: string
}

interface DadosEventos {
  ibge: string
  anomalias?: AnomaliaChuva[]
  noticias?: NoticiaVerificada[]
  erro?: string
}

const ID_GRAFICO_CHUVA = 'grafico-precipitacao'
const civil = (iso: string) => ({ ano: +iso.slice(0, 4), mes: +iso.slice(5, 7), dia: +iso.slice(8, 10) })

export function AnalysisSection({ municipio, municipios, mesDe, mesAte, serie, enso }: Props) {
  const [gran] = useState<Granularidade>('mensal')
  const [janela] = useState<Janela>('custom')
  const [comparando, setComparando] = useState(false)
  const [outro, setOutro] = useState<Municipio | undefined>(undefined)
  const [dadosEventos, setDadosEventos] = useState<DadosEventos>({ ibge: '' })
  const [destaque, setDestaque] = useState<string | null>(null)
  const [opcaoEstacao, setOpcaoEstacao] = useState<OpcaoEstacao>('astronomica')
  const [comparacao, setComparacao] = useState<SerieComparacao>({ chave: '' })
  const [graficoAtivo, setGraficoAtivo] = useState<string | null>(null)
  const idNotaEstacao = useId()

  const anoDe = ANO_INICIO + Math.floor(mesDe / 12)
  const anoAte = ANO_INICIO + Math.floor((mesAte - 1) / 12)
  // comparação com qualquer município do país (dados reais da API)
  const candidatos = useMemo(
    () => municipios.filter((m) => m.ibge !== municipio.ibge).sort((a, b) => a.nome.localeCompare(b.nome, 'pt-BR')),
    [municipios, municipio.ibge],
  )
  const outroAtivo = comparando ? outro : undefined
  const chaveComparacao = outroAtivo?.ibge ?? ''

  useEffect(() => {
    if (!outroAtivo) return
    const controller = new AbortController()
    const chave = outroAtivo.ibge
    carregarClima(chave, controller.signal)
      .then(({ serie: dados }) => setComparacao({ chave, serie: dados }))
      .catch((e: unknown) => {
        if (controller.signal.aborted) return
        setComparacao({ chave, erro: e instanceof Error ? e.message : 'Não foi possível carregar o município de comparação.' })
      })
    return () => controller.abort()
  }, [outroAtivo])

  // anomalias de chuva e notícias verificadas do município (uma vez por município)
  useEffect(() => {
    const controller = new AbortController()
    const ibge = municipio.ibge
    Promise.all([carregarAnomalias(ibge, controller.signal), carregarNoticias(ibge, controller.signal)])
      .then(([anomalias, noticias]) => setDadosEventos({ ibge, anomalias, noticias }))
      .catch((e: unknown) => {
        if (controller.signal.aborted) return
        setDadosEventos({ ibge, erro: e instanceof Error ? e.message : 'Não foi possível carregar os eventos de chuva.' })
      })
    return () => controller.abort()
  }, [municipio.ibge])

  const serieOutro = comparacao.chave === chaveComparacao ? comparacao.serie : undefined
  const erroOutro = comparacao.chave === chaveComparacao ? comparacao.erro : undefined
  const carregandoOutro = Boolean(outroAtivo) && !serieOutro && !erroOutro
  const outroComDados = serieOutro ? outroAtivo : undefined

  const eventosAtuais = dadosEventos.ibge === municipio.ibge ? dadosEventos : null
  const carregandoEventos = !eventosAtuais
  const { eventos, descartadas } = useMemo(() => {
    const anomalias = eventosAtuais?.anomalias ?? []
    const noPeriodo = anomalias.filter((a) => {
      const m = mesDoDia(a.data, ANO_INICIO)
      return m >= mesDe && m < mesAte
    })
    const validas = noPeriodo.filter((a) => a.status !== 'rejected')
    return {
      // mais recente primeiro: o usuário costuma procurar eventos que lembra
      // só eventos com notícia verificada (lista e marcadores do gráfico)
      eventos: agruparEventos(validas, eventosAtuais?.noticias ?? []).filter((e) => e.noticias.length > 0).reverse(),
      descartadas: noPeriodo.length - validas.length,
    }
  }, [eventosAtuais, mesDe, mesAte])
  const semAnalise = Boolean(eventosAtuais?.anomalias) && eventosAtuais!.anomalias!.length === 0
  const marcadores = useMemo<Marcador[]>(() => eventos.map((e: EventoChuva) => ({
    id: e.id,
    grupo: e.id,
    data: civil(e.principal.data),
    texto: `${formatarPeriodo(e.inicio, e.fim)}: ${descreverAnomalia(e.principal)}${e.noticias.length ? ` · ${e.noticias.length} notícia(s)` : ''}`,
  })), [eventos])

  function verNoGrafico(evento: EventoChuva) {
    setDestaque(evento.id)
    document.getElementById(ID_GRAFICO_CHUVA)?.scrollIntoView({ behavior: 'smooth', block: 'center' })
  }

  const [ini, fim] = janelaEmMeses(janela, mesDe, mesAte)
  const episodios = useMemo(() => {
    const resultado: { tipo: 'el-nino' | 'la-nina'; inicio: number; fim: number }[] = []
    for (const item of enso) {
      const tipo = (item.enso_index ?? 0) >= 0.5 ? 'el-nino' : (item.enso_index ?? 0) <= -0.5 ? 'la-nina' : null
      if (!tipo) continue
      const mes = (item.year - ANO_INICIO) * 12 + item.month - 1
      const anterior = resultado[resultado.length - 1]
      if (anterior?.tipo === tipo && anterior.fim === mes) anterior.fim++
      else resultado.push({ tipo, inicio: mes, fim: mes + 1 })
    }
    return resultado
  }, [enso])

  const graficos = useMemo(() => {
    const monta = (campo: keyof SerieClima, cor: string, modo: 'media' | 'soma'): SerieGrafico[] => {
      const lista: [Municipio, string, SerieClima][] = [[municipio, cor, serie]]
      if (outroComDados && serieOutro) lista.push([outroComDados, COR_COMPARACAO, serieOutro])
      return lista.map(([m, c, s]) => ({
        nome: rotuloMunicipio(m),
        cor: c,
        pontos: agregar(s[campo], ini, fim, gran, modo),
      }))
    }
    return {
      temp: monta('temp', '#c0562b', 'media'),
      chuva: monta('chuva', '#1769a8', 'soma'),
      umid: monta('umid', '#2f7d5b', 'media'),
    }
  }, [municipio, outroComDados, serieOutro, ini, fim, gran, serie])

  const metodoEstacao = opcaoEstacao === 'oculto' ? null : opcaoEstacao
  const chave = `${municipio.ibge}-${outroComDados?.ibge ?? 'x'}-${gran}-${ini}-${fim}`
  const arq = (nome: string) => `${nome}_${slug(municipio.nome)}-${slug(municipio.uf)}${outroComDados ? `_vs_${slug(outroComDados.nome)}` : ''}`
  const comum = { episodios, metodoEstacao, syncId: SYNC_ID }
  const foco = (id: string) => ({
    tooltipVisivel: graficoAtivo === null || graficoAtivo === id,
    onAtivar: (ativo: boolean) => setGraficoAtivo((atual) => (ativo ? id : atual === id ? null : atual)),
  })

  return (
    <section className="analysis" aria-labelledby="analise-titulo">
      <div className="analysis__head">
        <div>
          <p className="mono-label">{rotuloMunicipio(municipio)} · {anoDe}–{anoAte}</p>
          <h2 id="analise-titulo" className="section-title">
            Análise climática
          </h2>
        </div>
      </div>

      <div className={comparando ? 'compare is-open' : 'compare'}>
        <button type="button" className="compare__toggle" aria-expanded={comparando} onClick={() => setComparando((v) => !v)}>
          <IconCompare size={20} />
          Comparar municípios
          <IconChevronDown size={18} className="compare__chev" />
        </button>
        {comparando && (
          <div className="compare__body">
            <label htmlFor="comparar-com">Comparar {municipio.nome} com outro município (de qualquer estado)</label>
            <BuscaMunicipio id="comparar-com" municipios={candidatos} selecionado={outro} onSelecionar={setOutro} />
            {outro && (
              <button type="button" className="btn btn--ghost" onClick={() => setOutro(undefined)}>
                Remover comparação
              </button>
            )}
            {carregandoOutro && <p className="compare__status" role="status"><span className="loading-spinner" />Buscando dados de {outroAtivo?.nome}…</p>}
            {erroOutro && <p className="compare__status compare__status--erro" role="alert">{erroOutro}</p>}
          </div>
        )}
      </div>

      <div className="season-bar">
        <div className="season-bar__control">
          <span className="season-bar__label" id={`${idNotaEstacao}-rotulo`}>Estações do ano na faixa superior dos gráficos</span>
          <div className="segmented" role="radiogroup" aria-labelledby={`${idNotaEstacao}-rotulo`} aria-describedby={idNotaEstacao}>
            {OPCOES_ESTACAO.map((opcao) => (
              <button
                key={opcao.valor}
                type="button"
                role="radio"
                aria-checked={opcaoEstacao === opcao.valor}
                className={opcaoEstacao === opcao.valor ? 'is-active' : undefined}
                onClick={() => setOpcaoEstacao(opcao.valor)}
              >
                {opcao.rotulo}
              </button>
            ))}
          </div>
        </div>
        <p className="season-bar__note" id={idNotaEstacao}>
          {metodoEstacao
            ? `${DESCRICAO_METODO[metodoEstacao]} Não são o mesmo que a época de chuva ou de seca da região.`
            : 'Estações ocultas.'}
          {' '}Passe o cursor ou toque em um mês para ver a estação. Arraste a barra inferior de qualquer gráfico para ampliar os três.
        </p>
      </div>

      <div className="charts">
        <TimeSeriesChart
          key={`t-${chave}`}
          titulo="Temperatura média"
          subtitulo="Média mensal da temperatura do ar a 2 m · °C"
          unidade="°C"
          tipo="linha"
          series={graficos.temp}
          decimais={1}
          passoY={1}
          arquivo={arq('temperatura-media')}
          {...comum}
          {...foco('temp')}
        />
        <div id={ID_GRAFICO_CHUVA} className="charts__item">
        <TimeSeriesChart
          key={`p-${chave}`}
          titulo="Precipitação acumulada"
          subtitulo="Chuva total de cada mês · mm"
          unidade="mm"
          tipo="barra"
          series={graficos.chuva}
          decimais={0}
          passoY={5}
          dominioZero
          arquivo={arq('precipitacao-acumulada')}
          marcadores={marcadores}
          destaque={destaque}
          rotuloMarcadores="Evento de chuva extrema"
          {...comum}
          {...foco('chuva')}
        />
        </div>
        <TimeSeriesChart
          key={`u-${chave}`}
          titulo="Umidade relativa média"
          subtitulo="Média mensal, derivada da temperatura do ponto de orvalho · %"
          unidade="%"
          tipo="linha"
          series={graficos.umid}
          decimais={0}
          passoY={5}
          arquivo={arq('umidade-relativa-media')}
          {...comum}
          {...foco('umid')}
        />
      </div>

      <EventosExtremos
        municipio={municipio.nome}
        eventos={eventos}
        descartadas={descartadas}
        carregando={carregandoEventos}
        erro={eventosAtuais?.erro ?? ''}
        semAnalise={semAnalise}
        periodo={anoDe === anoAte ? String(anoDe) : `${anoDe}–${anoAte}`}
        onVerNoGrafico={verNoGrafico}
      />
    </section>
  )
}
