import { MUNICIPIOS } from './climate.ts'

type P = [number, number] // [lon, lat]

const CONTORNO: P[] = [
  [-50.15, -12.45], [-49.3, -12.6], [-48.4, -12.35], [-47.55, -12.5], [-47.35, -13.2], [-46.5, -13.5],
  [-46.25, -14.3], [-45.95, -14.9], [-46.4, -15.7], [-46.95, -16.2], [-47.2, -17.0], [-47.5, -17.6],
  [-47.55, -18.25], [-48.4, -18.65], [-49.4, -18.5], [-49.9, -18.9], [-50.7, -19.3], [-51.3, -19.0],
  [-51.9, -18.6], [-52.3, -18.0], [-52.9, -17.7], [-53.2, -17.0], [-52.7, -16.4], [-52.0, -16.0],
  [-51.6, -15.2], [-51.2, -14.4], [-50.5, -14.0], [-50.3, -13.1],
]
const DF: [number, number, number, number] = [-48.3, -15.5, -47.45, -16.05] // lon0, lat0, lon1, lat1

export const MAPA_LARGURA = 640
export const MAPA_ALTURA = 640

const lons = CONTORNO.map((p) => p[0])
const lats = CONTORNO.map((p) => p[1])
const [LON0, LON1, LAT0, LAT1] = [Math.min(...lons), Math.max(...lons), Math.max(...lats), Math.min(...lats)]
const KX = Math.cos((((LAT0 + LAT1) / 2) * Math.PI) / 180)
const ESCALA = Math.min((MAPA_LARGURA - 80) / ((LON1 - LON0) * KX), (MAPA_ALTURA - 80) / (LAT0 - LAT1))
const OFFX = (MAPA_LARGURA - (LON1 - LON0) * KX * ESCALA) / 2
const OFFY = (MAPA_ALTURA - (LAT0 - LAT1) * ESCALA) / 2

export const projetar = (lon: number, lat: number): P => [OFFX + (lon - LON0) * KX * ESCALA, OFFY + (LAT0 - lat) * ESCALA]

function mulberry32(a: number) {
  return () => {
    a = (a + 0x6d2b79f5) >>> 0
    let t = a
    t = Math.imul(t ^ (t >>> 15), t | 1)
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61)
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296
  }
}

function dentro(p: P, poly: P[]) {
  let c = false
  for (let i = 0, j = poly.length - 1; i < poly.length; j = i++) {
    const [xi, yi] = poly[i]
    const [xj, yj] = poly[j]
    if (yi > p[1] !== yj > p[1] && p[0] < ((xj - xi) * (p[1] - yi)) / (yj - yi) + xi) c = !c
  }
  return c
}

// recorta o polígono pelo semiplano mais próximo de `a` do que de `b`
function recortar(poly: P[], a: P, b: P): P[] {
  const nx = b[0] - a[0]
  const ny = b[1] - a[1]
  const c = (nx * (a[0] + b[0]) + ny * (a[1] + b[1])) / 2
  const f = (p: P) => c - (nx * p[0] + ny * p[1]) // >= 0 : lado de `a`
  const out: P[] = []
  for (let i = 0; i < poly.length; i++) {
    const p = poly[i]
    const q = poly[(i + 1) % poly.length]
    const fp = f(p)
    const fq = f(q)
    if (fp >= 0) out.push(p)
    if (fp >= 0 !== fq >= 0) {
      const t = fp / (fp - fq)
      out.push([p[0] + (q[0] - p[0]) * t, p[1] + (q[1] - p[1]) * t])
    }
  }
  return out
}

export interface Celula {
  id: string | null // id do município cadastrado (ou null)
  d: string // path SVG
}

const emDF = (p: P) => p[0] > DF[0] && p[0] < DF[2] && p[1] < DF[1] && p[1] > DF[3]

function gerar(): Celula[] {
  const rnd = mulberry32(2026)
  const fixos = MUNICIPIOS.map((m) => ({ id: m.id, p: [m.lon, m.lat] as P }))
  const sementes: { id: string | null; p: P }[] = [...fixos]
  const rioVerde = fixos[0].p
  let tentativas = 0
  while (sementes.length < 246 && tentativas++ < 20000) {
    const cand: P = [LON0 + rnd() * (LON1 - LON0), LAT1 + rnd() * (LAT0 - LAT1)]
    if (!dentro(cand, CONTORNO) || emDF(cand)) continue
    const dRV = Math.hypot((cand[0] - rioVerde[0]) * KX, cand[1] - rioVerde[1])
    if (dRV < 0.75) continue // Rio Verde é um dos maiores municípios do estado
    const dist = Math.min(...sementes.map((s) => Math.hypot((cand[0] - s.p[0]) * KX, cand[1] - s.p[1])))
    if (dist > 0.21 + rnd() * 0.08) sementes.push({ id: null, p: cand })
  }
  return sementes.map((s, i) => {
    let poly = CONTORNO.slice()
    for (let j = 0; j < sementes.length && poly.length > 2; j++) if (j !== i) poly = recortar(poly, s.p, sementes[j].p)
    const d =
      poly.length < 3
        ? ''
        : 'M' + poly.map((p) => projetar(p[0], p[1]).map((v) => v.toFixed(1)).join(',')).join('L') + 'Z'
    return { id: s.id, d }
  })
}

export const CELULAS: Celula[] = gerar().filter((c) => c.d)
export const CONTORNO_PATH = 'M' + CONTORNO.map((p) => projetar(p[0], p[1]).map((v) => v.toFixed(1)).join(',')).join('L') + 'Z'
const [dx0, dy0] = projetar(DF[0], DF[1])
const [dx1, dy1] = projetar(DF[2], DF[3])
export const DF_RECT = { x: dx0, y: dy0, w: dx1 - dx0, h: dy1 - dy0 }
