// Mapa das UFs em SVG (malha do IBGE, ~100 KB): leve o bastante para a página
// inicial, que não deve baixar os 5.573 polígonos municipais.
import { useEffect, useMemo, useState } from 'react'
import type { Feature, FeatureCollection, Geometry, Position } from 'geojson'
import { fmt, RAMPA, type LinhaUf, type VariavelClima } from '../../data/estatisticas'

const MALHA_UF = 'https://servicodados.ibge.gov.br/api/v3/malhas/paises/BR?formato=application/vnd.geo+json&qualidade=minima&intrarregiao=UF'

const SIGLA_UF: Record<string, string> = {
  11: 'RO', 12: 'AC', 13: 'AM', 14: 'RR', 15: 'PA', 16: 'AP', 17: 'TO', 21: 'MA', 22: 'PI', 23: 'CE', 24: 'RN',
  25: 'PB', 26: 'PE', 27: 'AL', 28: 'SE', 29: 'BA', 31: 'MG', 32: 'ES', 33: 'RJ', 35: 'SP', 41: 'PR', 42: 'SC',
  43: 'RS', 50: 'MS', 51: 'MT', 52: 'GO', 53: 'DF',
}

let promessa: Promise<FeatureCollection> | null = null
function carregarMalhaUf(): Promise<FeatureCollection> {
  promessa ??= fetch(MALHA_UF).then((r) => {
    if (!r.ok) throw new Error(`Erro ${r.status} na malha do IBGE`)
    return r.json() as Promise<FeatureCollection>
  }).catch((e: unknown) => { promessa = null; throw e })
  return promessa
}

// projeção equiretangular com correção de latitude média do Brasil (≈ −15°)
const KX = Math.cos((15 * Math.PI) / 180)
const LIMITES = { oeste: -74.1, leste: -34.7, norte: 5.4, sul: -33.8 }
const LARGURA = 600
const ESCALA = LARGURA / ((LIMITES.leste - LIMITES.oeste) * KX)
const ALTURA = Math.round((LIMITES.norte - LIMITES.sul) * ESCALA)
const projetar = ([lon, lat]: Position) => `${((lon - LIMITES.oeste) * KX * ESCALA).toFixed(1)},${((LIMITES.norte - lat) * ESCALA).toFixed(1)}`

function caminho(g: Geometry): string {
  const anel = (a: Position[]) => `M${a.map(projetar).join('L')}Z`
  if (g.type === 'Polygon') return g.coordinates.map(anel).join('')
  if (g.type === 'MultiPolygon') return g.coordinates.flatMap((p) => p.map(anel)).join('')
  return ''
}

/** Quebras por quantis entre as UFs (6 classes). */
function quebras(valores: number[], k = 6): number[] {
  const v = [...valores].sort((a, b) => a - b)
  if (v.length < 2) return []
  return Array.from({ length: k - 1 }, (_, i) => v[Math.floor(((i + 1) * v.length) / k)])
}

interface Props {
  ufs: LinhaUf[] | null
  variavel: VariavelClima
  titulo: string
  unidade: string
  compacto?: boolean
}

export function MapaUF({ ufs, variavel, titulo, unidade, compacto }: Props) {
  const [malha, setMalha] = useState<FeatureCollection | null>(null)
  const [erro, setErro] = useState(false)
  const [foco, setFoco] = useState<string | null>(null)
  useEffect(() => {
    let ativo = true
    carregarMalhaUf().then((m) => { if (ativo) setMalha(m) }).catch(() => { if (ativo) setErro(true) })
    return () => { ativo = false }
  }, [])

  const caminhos = useMemo(
    () => (malha?.features ?? []).map((f: Feature) => ({ uf: SIGLA_UF[String(f.properties?.codarea)] ?? '?', d: caminho(f.geometry) })),
    [malha],
  )
  const porUf = useMemo(() => new Map((ufs ?? []).map((u) => [u.uf, u])), [ufs])
  const valores = (ufs ?? []).map((u) => u[variavel]).filter((v): v is number => v !== null)
  const limites = quebras(valores)
  const rampa = RAMPA[variavel].slice(1)
  const cor = (v: number | null | undefined) => {
    if (v === null || v === undefined) return '#ffffff'
    let i = 0
    while (i < limites.length && v >= limites[i]) i++
    return rampa[Math.min(i, rampa.length - 1)]
  }
  const casas = variavel === 'precipitacao' ? 0 : 1
  const linhaFoco = foco ? porUf.get(foco) : null

  if (erro) return <p className="ed-estado">Não foi possível carregar a malha das UFs do IBGE.</p>

  return (
    <div className="ed-mapa-uf">
      <svg viewBox={`0 0 ${LARGURA} ${ALTURA}`} role="img" aria-label={`${titulo}, por unidade federativa`} style={{ width: '100%', height: 'auto', display: 'block' }}>
        {!malha && <rect width={LARGURA} height={ALTURA} fill="#f2f2f2" rx="8" />}
        {caminhos.map(({ uf, d }) => {
          const linha = porUf.get(uf)
          return (
            <path
              key={uf} d={d} fill={cor(linha?.[variavel])} stroke={foco === uf ? '#141414' : '#ffffff'}
              strokeWidth={foco === uf ? 2 : 0.8} strokeLinejoin="round" tabIndex={compacto ? -1 : 0}
              onMouseEnter={() => setFoco(uf)} onMouseLeave={() => setFoco(null)}
              onFocus={() => setFoco(uf)} onBlur={() => setFoco(null)}
              aria-label={`${uf}: ${fmt(linha?.[variavel], casas)} ${unidade}`}
            >
              <title>{`${uf}: ${fmt(linha?.[variavel], casas)} ${unidade}`}</title>
            </path>
          )
        })}
        {foco && caminhos.filter((c) => c.uf === foco).map(({ uf, d }) => (
          <path key={`f-${uf}`} d={d} fill="none" stroke="#141414" strokeWidth={2} pointerEvents="none" />
        ))}
      </svg>
      {!compacto && (
        <div className="ed-mapa-uf__info" aria-live="polite">
          {linhaFoco
            ? <p><b>{linhaFoco.uf}</b> · {linhaFoco.regiao} · {linhaFoco.municipios.toLocaleString('pt-BR')} municípios com dados<br />
              {titulo}: <b>{fmt(linhaFoco[variavel], casas)} {unidade}</b></p>
            : <p>Passe o mouse (ou navegue com Tab) sobre uma UF para ver o valor.</p>}
        </div>
      )}
      {limites.length > 0 && (
        <ul className="ed-legenda ed-mapa-uf__legenda" aria-label={`Legenda: ${titulo} (${unidade})`}>
          {rampa.slice(0, limites.length + 1).map((c, i) => (
            <li key={c}><i style={{ background: c }} />
              {i === 0 ? `< ${fmt(limites[0], casas)}` : i === limites.length ? `≥ ${fmt(limites[i - 1], casas)}` : `${fmt(limites[i - 1], casas)}–${fmt(limites[i], casas)}`}
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
