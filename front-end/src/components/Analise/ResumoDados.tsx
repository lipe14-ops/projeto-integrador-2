import { useEffect, useState } from 'react'
import { carregarVisaoGeral, type VisaoGeral } from '../../data/analise'

const num = (v: number) => v.toLocaleString('pt-BR')

/** Volume de dados reunido pela plataforma (API /analysis/visao-geral). */
export function ResumoDados() {
  const [dados, setDados] = useState<VisaoGeral | null>(null)

  useEffect(() => {
    let ativo = true
    carregarVisaoGeral().then((d) => { if (ativo) setDados(d) }).catch(() => { /* faixa opcional */ })
    return () => { ativo = false }
  }, [])

  if (!dados) return null
  const itens = [
    dados.climate_records ? { valor: `${(dados.climate_records / 1e6).toLocaleString('pt-BR', { maximumFractionDigits: 1 })} mi`, rotulo: 'registros climáticos' } : null,
    { valor: num(dados.municipalities_with_data ?? dados.municipalities), rotulo: 'municípios com dados' },
    { valor: `${dados.period.start}–${dados.period.end}`, rotulo: 'período' },
    { valor: num(dados.rain_events), rotulo: 'eventos de chuva detectados' },
  ].filter((i): i is { valor: string; rotulo: string } => i !== null)

  return (
    <ul className="resumo-dados" aria-label="Dados reunidos pela plataforma">
      {itens.map((i) => (
        <li key={i.rotulo} className="resumo-dados__item">
          <strong>{i.valor}</strong>
          <span>{i.rotulo}</span>
        </li>
      ))}
    </ul>
  )
}
