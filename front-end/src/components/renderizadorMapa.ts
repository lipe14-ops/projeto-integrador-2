import L from 'leaflet'

type Anel = L.Point[]
type PoligonoInterno = { _parts: Anel[] }
type RenderizadorInterno = L.SVG & { _setPath(layer: PoligonoInterno, path: string): void }

/** Anel com ao menos 3 pontos distintos (área possível) depois da projeção. */
function anelValido(anel: Anel): boolean {
  const distintos = new Set(anel.map((p) => `${Math.round(p.x)},${Math.round(p.y)}`))
  return distintos.size >= 3
}

/**
 * Renderizador SVG para os mapas de polígonos.
 *
 * - padding 1: o SVG cobre uma tela inteira em cada direção, para o recorte dos
 *   polígonos não aparecer como linhas ao arrastar.
 * - Ilhas pequenas (Fernando de Noronha, ilhas do litoral do PA/MA/PR…), depois
 *   de projetadas e simplificadas, viram anéis degenerados como "M463 90L463 90z".
 *   O Chrome não desenha nada, mas o Firefox desenha esses subcaminhos de
 *   comprimento zero como segmentos de reta longos e sem sentido. Descartamos
 *   os anéis sem área antes de montar o caminho SVG.
 */
const SvgSemAneisDegenerados = L.SVG.extend({
  _updatePoly(this: RenderizadorInterno, layer: PoligonoInterno, closed: boolean) {
    const partes = closed ? layer._parts.filter(anelValido) : layer._parts
    this._setPath(layer, L.SVG.pointsToPath(partes as unknown as L.PointExpression[], closed))
  },
}) as unknown as new (options?: L.RendererOptions) => L.SVG

export function criarRenderizadorMapa(): L.SVG {
  return new SvgSemAneisDegenerados({ padding: 1 })
}
