import { useEffect, useState } from 'react'
import { ehAbort } from '../../data/estatisticas'

export type Recurso<T> = { dados: T | null; carregando: boolean; erro: string | null }

/**
 * Busca com chave: aborta a anterior quando a chave muda e mantém o último
 * dado válido na tela enquanto o novo chega (gráfico não "pisca").
 */
export function useRecurso<T>(chave: string | null, buscar: (signal: AbortSignal) => Promise<T>): Recurso<T> {
  const [estado, setEstado] = useState<{ chave: string | null; dados: T | null; erro: string | null }>({ chave: null, dados: null, erro: null })
  useEffect(() => {
    if (chave === null) return
    const controller = new AbortController()
    buscar(controller.signal)
      .then((dados) => setEstado({ chave, dados, erro: null }))
      .catch((e: unknown) => {
        if (controller.signal.aborted || ehAbort(e)) return
        setEstado((s) => ({ chave, dados: s.dados, erro: e instanceof Error ? e.message : 'Erro ao carregar os dados.' }))
      })
    return () => controller.abort()
    // a chave identifica a consulta; `buscar` é recriada a cada render
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [chave])
  const atual = estado.chave === chave
  return { dados: estado.dados, carregando: chave !== null && !atual, erro: atual ? estado.erro : null }
}
