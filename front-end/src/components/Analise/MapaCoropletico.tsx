import { useEffect, useMemo, useRef, useState } from 'react'
import { MapContainer, useMap } from 'react-leaflet'
import L from 'leaflet'
import type { Feature, FeatureCollection, Geometry } from 'geojson'
import 'leaflet/dist/leaflet.css'
import '../MapaBrasil/MapaBrasil.css'
import { AjustarTamanhoMapa } from '../AjustarTamanhoMapa'
import type { Coropletico, Escala, Geometrias, Metrica, ValorMunicipio } from '../../data/analise'
import {
  classesDe, corCategoria, corDoValor, hachuraInsuficiente, NEUTRO, pontilhadoSemDados, situacaoDe, type Classe,
} from './cores'
import { descreverValor, ROTULO_STATUS } from './formatos'

export type NomeMunicipio = { nome: string; uf: string }

/** O mínimo que o mapa precisa para colorir: o coroplético de anomalias ou outra métrica municipal. */
export interface DadosMapa {
  scale: Escala
  breaks: number[]
  metric: string
  values: ValorMunicipio[]
}

// Limites estaduais (só contorno, sem interação), da malha do IBGE.
const MALHA_UF = 'https://servicodados.ibge.gov.br/api/v3/malhas/paises/BR?formato=application/vnd.geo+json&qualidade=minima&intrarregiao=UF'
let promessaUf: Promise<FeatureCollection> | null = null
function carregarUfs(): Promise<FeatureCollection> {
  promessaUf ??= fetch(MALHA_UF).then((r) => {
    if (!r.ok) throw new Error(`Erro ${r.status}`)
    return r.json() as Promise<FeatureCollection>
  }).catch((e: unknown) => {
    promessaUf = null
    throw e
  })
  return promessaUf
}

// 5.573 polígonos: o canvas é muito mais leve que o SVG nessa escala.
// Um renderizador POR MAPA: no Leaflet o renderizador pertence a um único mapa.
// Compartilhado entre o Panorama e o Mapa de anomalias, o segundo mapa tomava o
// canvas do primeiro (desenhos sobrepostos ou mapa em branco ao trocar de aba).
const criarRenderizador = () => L.canvas({ padding: 0.5, tolerance: 0 })

const BORDA = { color: '#ffffff', weight: 0.35, opacity: 0.9 }
const BORDA_HOVER = { color: '#0f2f2d', weight: 1.6, opacity: 1 }
const BORDA_SELECIONADO = { color: '#0f2f2d', weight: 2.6, opacity: 1 }

const escapar = (s: string) => s.replace(/[&<>"']/g, (c) => `&#${c.charCodeAt(0)};`)

interface Props {
  geometrias: Geometrias | null
  dados: DadosMapa | null
  nomes: Map<string, NomeMunicipio>
  selecionado: string | null
  onSelecionar: (codigo: string) => void
  aviso: string | null
  erro: string | null
  /** rampa sequencial própria (claro → escuro); padrão: azul do mapa de anomalias */
  rampa?: string[]
  /** linhas do tooltip (HTML já escapado) depois do nome; padrão: valor, eventos e situação */
  tooltip?: (valor: ValorMunicipio | undefined) => string[]
  /** chamado ao voltar para o Brasil (o município selecionado deve ser limpo) */
  onVoltar?: () => void
}

export function MapaCoropletico({ geometrias, dados, nomes, selecionado, onSelecionar, aviso, erro, rampa, tooltip, onVoltar }: Props) {
  // Navegação em dois passos, como no Explorar: primeiro o estado, depois o município.
  // uf = código IBGE de 2 dígitos do estado aberto (prefixo do código do município).
  const [uf, setUf] = useState<string | null>(selecionado ? selecionado.slice(0, 2) : null)
  // seleção vinda de fora (busca, atalho "Porto Alegre"): abre o estado do município
  const [selAnterior, setSelAnterior] = useState(selecionado)
  if (selecionado !== selAnterior) {
    setSelAnterior(selecionado)
    if (selecionado && selecionado.slice(0, 2) !== uf) setUf(selecionado.slice(0, 2))
  }
  const [renderizador] = useState(criarRenderizador)
  const [nomesUf, setNomesUf] = useState<Map<string, string>>(new Map())
  useEffect(() => {
    let ativo = true
    carregarNomesUf().then((m) => { if (ativo) setNomesUf(m) }).catch(() => { /* tooltip mostra o código */ })
    return () => { ativo = false }
  }, [])

  function voltar() {
    setUf(null)
    onVoltar?.()
  }

  return (
    <div className="mapa-wrapper">
      {uf && (
        <button type="button" className="mapa-voltar" onClick={voltar}>
          ← Brasil
        </button>
      )}
      {aviso && (
        <div className="mapa-status" role="status" aria-live="polite">
          <span className="loading-spinner" aria-hidden="true" />
          {aviso}
        </div>
      )}
      {!aviso && erro && <div className="mapa-status mapa-status--erro" role="alert">{erro}</div>}
      {!aviso && !erro && (
        <div className="mapa-status mapa-status--dica" role="status">
          {uf
            ? `${nomesUf.get(uf) ?? 'Estado'}: clique em um município`
            : 'Clique em um estado para ver os municípios'}
        </div>
      )}
      <MapContainer
        center={[-14.2, -51.9]}
        zoom={4}
        zoomSnap={0.25}
        preferCanvas
        renderer={renderizador}
        attributionControl={false}
        className="coropletico__mapa"
      >
        {geometrias && (
          <CamadaMunicipios
            geometrias={geometrias} dados={dados} nomes={nomes} uf={uf} renderizador={renderizador}
            selecionado={selecionado} onSelecionar={onSelecionar} rampa={rampa} tooltip={tooltip}
          />
        )}
        <CamadaEstados uf={uf} nomesUf={nomesUf} onAbrir={setUf} renderizador={renderizador} />
        <AjustarTamanhoMapa />
      </MapContainer>
    </div>
  )
}

const NOMES_UF = 'https://servicodados.ibge.gov.br/api/v1/localidades/estados'
let promessaNomesUf: Promise<Map<string, string>> | null = null
function carregarNomesUf(): Promise<Map<string, string>> {
  promessaNomesUf ??= fetch(NOMES_UF).then((r) => {
    if (!r.ok) throw new Error(`Erro ${r.status}`)
    return r.json() as Promise<{ id: number; sigla: string; nome: string }[]>
  }).then((lista) => new Map(lista.map((e) => [String(e.id), `${e.nome} — ${e.sigla}`]))).catch((e: unknown) => {
    promessaNomesUf = null
    throw e
  })
  return promessaNomesUf
}

const ESTADO = { color: '#334845', weight: 0.9, opacity: 0.75, fill: true, fillColor: '#000', fillOpacity: 0 }
const ESTADO_HOVER = { color: '#0f2f2d', weight: 2.6, opacity: 1 }
const ESTADO_ABERTO = { color: '#0f2f2d', weight: 2.2, opacity: 1, fill: false }

/**
 * Contornos estaduais. Fora do estado aberto eles ficam por cima dos municípios
 * (preenchimento transparente) e recebem o mouse: passar mostra o estado e clicar
 * abre os municípios dele. O estado aberto só tem contorno, sem interação, para
 * que os cliques cheguem aos municípios.
 */
function CamadaEstados({ uf, nomesUf, onAbrir, renderizador }: {
  uf: string | null; nomesUf: Map<string, string>; onAbrir: (uf: string) => void; renderizador: L.Canvas
}) {
  const map = useMap()
  const [geo, setGeo] = useState<FeatureCollection | null>(null)
  useEffect(() => {
    let ativo = true
    carregarUfs().then((g) => { if (ativo) setGeo(g) }).catch(() => { /* sem contorno, sem navegação por estado */ })
    return () => { ativo = false }
  }, [])

  const abrir = useRef(onAbrir)
  const nomes = useRef(nomesUf)
  useEffect(() => {
    abrir.current = onAbrir
    nomes.current = nomesUf
  })

  // recria a camada a cada estado aberto (27 polígonos: barato)
  useEffect(() => {
    if (!geo) return
    const codigo = (f?: Feature) => String((f?.properties as { codarea?: string } | null)?.codarea ?? '')
    const outros = L.geoJSON(geo, {
      filter: (f: Feature) => codigo(f) !== uf,
      style: ESTADO,
      renderer: renderizador,
      onEachFeature: (f: Feature, layer: L.Layer) => {
        const cod = codigo(f)
        const caminho = layer as L.Path
        caminho.bindTooltip(
          () => `<b>${escapar(nomes.current.get(cod) ?? `Estado ${cod}`)}</b><br/><span style="opacity:.75">Clique para ver os municípios</span>`,
          { sticky: true, className: 'tooltip-mapa' },
        )
        caminho.on({
          mouseover: () => caminho.setStyle(ESTADO_HOVER),
          mouseout: () => caminho.setStyle(ESTADO),
          click: () => abrir.current(cod),
        })
      },
    } as L.GeoJSONOptions).addTo(map)
    const aberto = uf
      ? L.geoJSON(geo, { filter: (f: Feature) => codigo(f) === uf, style: ESTADO_ABERTO, interactive: false, renderer: renderizador } as L.GeoJSONOptions).addTo(map)
      : null
    // Os estados precisam ficar ACIMA dos municípios no canvas (o clique vai para a camada
    // de cima). A malha municipal pode chegar depois e se desenhar por cima: sempre que algo
    // é adicionado ao mapa, os estados voltam para a frente (uma vez por quadro).
    let quadro = 0
    const trazerParaFrente = () => {
      if (quadro) return
      quadro = requestAnimationFrame(() => {
        quadro = 0
        outros.bringToFront()
        aberto?.bringToFront()
      })
    }
    trazerParaFrente()
    map.on('layeradd', trazerParaFrente)
    return () => {
      map.off('layeradd', trazerParaFrente)
      if (quadro) cancelAnimationFrame(quadro)
      outros.remove()
      aberto?.remove()
    }
  }, [geo, uf, map, renderizador])

  // enquadra o estado aberto ou o Brasil inteiro (não na primeira carga: os municípios já enquadram)
  const ufAnterior = useRef<string | null | undefined>(undefined)
  useEffect(() => {
    if (!geo) return
    const primeira = ufAnterior.current === undefined
    ufAnterior.current = uf
    if (primeira && !uf) return
    const alvo = uf
      ? L.geoJSON(geo, { filter: (f: Feature) => String((f.properties as { codarea?: string }).codarea) === uf } as L.GeoJSONOptions)
      : L.geoJSON(geo)
    const limites = alvo.getBounds()
    if (limites.isValid()) map.flyToBounds(limites, { padding: [16, 16], duration: 0.6 })
  }, [geo, uf, map])

  return null
}

type Camadas = Map<string, L.Path>

function CamadaMunicipios({ geometrias, dados, nomes, selecionado, onSelecionar, rampa, tooltip, uf, renderizador }: Omit<Props, 'aviso' | 'erro' | 'onVoltar'> & { uf: string | null; renderizador: L.Canvas }) {
  const map = useMap()
  const camadas = useRef<Camadas>(new Map())
  const [versao, setVersao] = useState(0)

  const indice = useMemo(() => new Map((dados?.values ?? []).map((v) => [String(v.codigo_ibge), v])), [dados])
  const classes = useMemo<Classe[]>(
    () => (dados ? classesDe(dados.scale, dados.breaks, NEUTRO[dados.metric as Metrica], rampa) : []),
    [dados, rampa],
  )

  // estado atual lido pelos eventos do Leaflet (criados uma única vez)
  const atual = useRef({ indice, dados, nomes, selecionado, onSelecionar, tooltip, uf })
  useEffect(() => {
    atual.current = { indice, dados, nomes, selecionado, onSelecionar, tooltip, uf }
  })
  const noEstado = (codigo: string) => atual.current.uf !== null && codigo.startsWith(atual.current.uf)

  // cria os polígonos uma vez por malha
  useEffect(() => {
    const mapaCamadas: Camadas = new Map()
    const grupo = L.geoJSON(geometrias, {
      renderer: renderizador,
      style: () => ({ ...BORDA, fillColor: '#eef3f0', fillOpacity: 1 }),
      onEachFeature: (feature: Feature<Geometry, { codigo_ibge: number }>, layer) => {
        const codigo = String(feature.properties.codigo_ibge)
        const caminho = layer as L.Path
        mapaCamadas.set(codigo, caminho)
        caminho.bindTooltip(() => conteudoTooltip(codigo), { sticky: true, className: 'tooltip-mapa' })
        // tooltip do município só dentro do estado aberto (fora dele, o estado responde)
        caminho.on('tooltipopen', () => { if (!noEstado(codigo)) caminho.closeTooltip() })
        caminho.on({
          mouseover: () => {
            if (!noEstado(codigo)) return
            if (codigo !== atual.current.selecionado) caminho.setStyle(BORDA_HOVER)
            caminho.bringToFront()
          },
          mouseout: () => {
            if (noEstado(codigo) && codigo !== atual.current.selecionado) caminho.setStyle(BORDA)
          },
          click: () => {
            if (noEstado(codigo)) atual.current.onSelecionar(codigo)
          },
        })
      },
    } as L.GeoJSONOptions).addTo(map)
    camadas.current = mapaCamadas
    map.fitBounds(grupo.getBounds(), { padding: [10, 10] })
    // eslint-disable-next-line react-hooks/set-state-in-effect -- avisa o efeito de cores que as camadas existem
    setVersao((v) => v + 1)

    function conteudoTooltip(codigo: string): string {
      const { indice: idx, dados: dd, nomes: n, tooltip: tt } = atual.current
      const nome = n.get(codigo)
      const titulo = nome ? `${escapar(nome.nome)} — ${escapar(nome.uf)}` : `Município ${codigo}`
      const v: ValorMunicipio | undefined = idx.get(codigo)
      if (!dd) return `<b>${titulo}</b>`
      if (tt) return [`<b>${titulo}</b>`, ...tt(v)].join('<br/>')
      const d = dd as Coropletico
      if (!v) return `<b>${titulo}</b><br/>Sem detecção / sem dados no período`
      const linhas = [
        `<b>${titulo}</b>`,
        `${escapar(d.label)}: <b>${escapar(descreverValor(v, d))}</b>`,
        `${v.n.toLocaleString('pt-BR')} eventos · ${v.days.toLocaleString('pt-BR')} dias válidos`,
        `Situação: ${ROTULO_STATUS[v.status]}`,
        '<span style="opacity:.75">Clique para ver a distribuição sazonal</span>',
      ]
      return linhas.join('<br/>')
    }

    return () => {
      grupo.remove()
      camadas.current = new Map()
    }
  }, [geometrias, map, renderizador])

  // recolore quando chegam novos dados (sem recriar as camadas)
  useEffect(() => {
    const hachura = hachuraInsuficiente()
    const pontilhado = pontilhadoSemDados()
    camadas.current.forEach((caminho, codigo) => {
      let preenchimento: string | CanvasPattern = '#eef3f0'
      if (dados) {
        const v = indice.get(codigo)
        const situacao = situacaoDe(v, dados)
        if (situacao === 'insuficiente') preenchimento = hachura
        else if (situacao === 'sem_dados') preenchimento = pontilhado
        else if (dados.scale === 'categorical') preenchimento = corCategoria(v!.category)
        else preenchimento = corDoValor(v!.value!, classes)
      }
      const borda = codigo === selecionado ? BORDA_SELECIONADO : BORDA
      // com um estado aberto, o resto do país fica esmaecido (continua como contexto)
      const opacidade = uf && !codigo.startsWith(uf) ? 0.35 : 1
      // o renderizador canvas aceita CanvasPattern em fillStyle
      caminho.setStyle({ ...borda, fillColor: preenchimento as unknown as string, fillOpacity: opacidade })
    })
    if (selecionado) camadas.current.get(selecionado)?.bringToFront()
  }, [dados, indice, classes, selecionado, versao, uf])

  return null
}
