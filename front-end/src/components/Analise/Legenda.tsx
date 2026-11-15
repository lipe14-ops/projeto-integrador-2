import type { Coropletico, Definicoes, FaseComparacao, FiltrosAnalise } from '../../data/analise'
import { NOMES_ESTACAO, ORDEM_ESTACOES } from '../../data/seasons'
import {
  classesDe, COR_ESTACAO, COR_SEM_PREDOMINIO, HACHURA_CSS, NEUTRO, PONTILHADO_CSS, ROTULO_PADRAO,
} from './cores'
import { formatarMetrica } from './formatos'

interface Props {
  dados: Coropletico
  definicoes: Definicoes | null
  filtros: FiltrosAnalise
  comparar: FaseComparacao
  desatualizado: boolean
}

export function Legenda({ dados, definicoes, filtros, comparar, desatualizado }: Props) {
  const classes = classesDe(dados.scale, dados.breaks, NEUTRO[dados.metric])
  const minEventos = definicoes?.min_events ?? 20
  const s = dados.summary
  const estacao = filtros.season ? definicoes?.seasons[filtros.season] ?? NOMES_ESTACAO[filtros.season] : 'Todas as estações'
  const enso = dados.metric === 'razao_enso'
    ? `${definicoes?.enso_phases[comparar] ?? comparar} ÷ neutro`
    : filtros.enso_phase ? definicoes?.enso_phases[filtros.enso_phase] ?? filtros.enso_phase : 'Todas as fases'
  const classe = definicoes?.class_filters[filtros.event_class] ?? filtros.event_class
  const neutro = NEUTRO[dados.metric]

  return (
    <section className={desatualizado ? 'card legenda-analise is-desatualizada' : 'card legenda-analise'} aria-label="Legenda do mapa">
      <div className="legenda-analise__topo">
        <div>
          <p className="mono-label">Legenda</p>
          <h3>{dados.label}</h3>
          <p className="legenda-analise__unidade">Unidade: <b>{dados.unit}</b></p>
        </div>
        {desatualizado && <span className="legenda-analise__selo">atualizando…</span>}
      </div>

      <ul className="legenda-analise__classes">
        {dados.scale === 'categorical'
          ? <>
            {ORDEM_ESTACOES.map((e) => (
              <li key={e}><i style={{ background: COR_ESTACAO[e] }} />{ROTULO_PADRAO[`predominio_${e}`]}</li>
            ))}
            <li><i style={{ background: COR_SEM_PREDOMINIO }} />{ROTULO_PADRAO.sem_predominio} (q ≥ 0,05)</li>
          </>
          : classes.map((c) => <li key={c.rotulo}><i style={{ background: c.cor }} />{c.rotulo}</li>)}
        <li><i style={{ background: HACHURA_CSS }} />Dados insuficientes (&lt; {dados.metric === 'razao_enso' ? 10 : minEventos} eventos)</li>
        <li><i style={{ background: PONTILHADO_CSS }} />Sem detecção / sem dados</li>
      </ul>
      {neutro !== undefined && (
        <p className="legenda-analise__nota">
          Escala divergente centrada em <b>{formatarMetrica(neutro, dados.metric)}</b> (sem diferença):
          vermelho abaixo, azul acima.
        </p>
      )}
      {dados.scale === 'sequential' && dados.breaks.length > 0 && (
        <p className="legenda-analise__nota">Classes por quintis dos municípios com dados; mais escuro = maior valor.</p>
      )}

      <p className="legenda-analise__definicao">{dados.definition}</p>

      <dl className="legenda-analise__lista">
        <div><dt>Variável</dt><dd>{dados.variable_label}</dd></div>
        <div><dt>Classe</dt><dd>{classe}</dd></div>
        <div><dt>Período</dt><dd>{dados.period.start_year}–{dados.period.end_year}</dd></div>
        <div><dt>Estação</dt><dd>{estacao}</dd></div>
        <div><dt>Fase ENSO</dt><dd>{enso}</dd></div>
      </dl>

      <dl className="legenda-analise__resumo">
        <div><dt>Municípios com valor</dt><dd>{s.municipalities_with_data.toLocaleString('pt-BR')}</dd></div>
        <div><dt>Dados insuficientes</dt><dd>{s.insufficient.toLocaleString('pt-BR')}</dd></div>
        <div><dt>Sem detecção/dados</dt><dd>{s.without_detection.toLocaleString('pt-BR')}</dd></div>
        <div><dt>Eventos no filtro</dt><dd>{s.total_events.toLocaleString('pt-BR')}</dd></div>
        {s.median !== null && <div><dt>Mediana</dt><dd>{formatarMetrica(s.median, dados.metric)}</dd></div>}
      </dl>
    </section>
  )
}
