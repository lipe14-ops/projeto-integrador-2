import { useEffect } from 'react'
import { useMap } from 'react-leaflet'

/**
 * Remede o mapa sempre que o contêiner muda de tamanho.
 *
 * As abas ficam montadas e só são escondidas (`hidden`). Se a janela muda de
 * tamanho com a aba escondida, o Leaflet mede o contêiner como 0×0 e recorta
 * todos os polígonos nessa área vazia: ao voltar, o mapa aparece em branco e,
 * ao arrastar, o recorte surge como segmentos de reta sem sentido. Observar o
 * contêiner faz o Leaflet medir de novo assim que ele volta a ficar visível.
 */
export function AjustarTamanhoMapa() {
  const map = useMap()
  useEffect(() => {
    const el = map.getContainer()
    const obs = new ResizeObserver(() => {
      if (el.clientWidth > 0 && el.clientHeight > 0) map.invalidateSize()
    })
    obs.observe(el)
    return () => obs.disconnect()
  }, [map])
  return null
}
