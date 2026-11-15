import { useEffect, useMemo, useState } from 'react'
import { MapaCoropletico, type DadosMapa, type NomeMunicipio } from '../Analise/MapaCoropletico'
import { classesDe, HACHURA_CSS, NEUTRO, PONTILHADO_CSS } from '../Analise/cores'
import { Estado, Figura } from '../Editorial/Editorial'
import { useRecurso } from '../Editorial/useRecurso'
import { carregarMunicipios } from '../../data/api'
import { carregarCoropletico, carregarGeometrias, type Geometrias, type Variavel } from '../../data/analise'
import {
  carregarMapaClima, fmt, NOME_FASE, NOME_VARIAVEL, RAMPA, type Recorte, type VariavelClima,
} from '../../data/estatisticas'
import { NOMES_ESTACAO } from '../../data/seasons'
import { ROTULO_ANOMALIA, type IdAnomalia } from '../../data/estatisticas'

type Indicador = VariavelClima | 'anomalias'

const escapar = (s: string) => s.replace(/[&<>"']/g, (c) => `&#${c.charCodeAt(0)};`)

export function SecaoMapa({ recorte, variavelAnomalia, numero }: { recorte: Recorte; variavelAnomalia: IdAnomalia; numero: number }) {
  const [indicador, setIndicador] = useState<Indicador>('temperatura')
  const [selecionado, setSelecionado] = useState<string | null>(null)
  const [geometrias, setGeometrias] = useState<Geometrias | null>(null)
  const [erroMalha, setErroMalha] = useState<string | null>(null)
  const [nomes, setNomes] = useState<Map<string, NomeMunicipio>>(new Map())
  useEffect(() => {
    carregarGeometrias().then(setGeometrias).catch((e: unknown) => setErroMalha(e instanceof Error ? e.message : 'erro'))
    carregarMunicipios().then((l) => setNomes(new Map(l.map((m) => [m.ibge, { nome: m.nome, uf: m.uf }])))).catch(() => { /* sem nomes: código IBGE */ })
  }, [])

  const clima = indicador !== 'anomalias'
  const chaveClima = clima ? JSON.stringify([indicador, recorte.inicio, recorte.fim, recorte.estacao, recorte.enso]) : null
  const mapaClima = useRecurso(chaveClima, (s) => carregarMapaClima(indicador as VariavelClima, recorte, s))
  const inicioAnom = Math.max(2017, recorte.inicio)
  const fimAnom = Math.max(2017, recorte.fim)
  const chaveAnom = clima ? null : JSON.stringify([variavelAnomalia, inicioAnom, fimAnom, recorte.estacao, recorte.enso])
  const mapaAnom = useRecurso(chaveAnom, (s) => carregarCoropletico('taxa', {
    variable: variavelAnomalia as Variavel, event_class: 'todas', start_year: inicioAnom, end_year: fimAnom,
    season: recorte.estacao, enso_phase: recorte.enso,
  }, 'el_nino', s))

  const unidade = clima ? (mapaClima.dados?.unidade ?? '') : 'eventos por 1.000 dias válidos'
  const casas = indicador === 'precipitacao' ? 0 : 1

  // adapta a resposta do clima ao formato do mapa coroplético
  const dados: DadosMapa | null = useMemo(() => {
    if (clima) {
      const m = mapaClima.dados
      if (!m) return null
      return {
        scale: 'sequential', breaks: m.quebras, metric: m.variavel,
        values: m.valores.map((v) => ({
          codigo_ibge: v.codigo_ibge, value: v.valor, category: null, n: v.meses, days: 0,
          status: v.valor === null ? 'sem_dados' : 'ok',
        })),
      }
    }
    return mapaAnom.dados ?? null
  }, [clima, mapaClima.dados, mapaAnom.dados])

  const rampa = clima ? RAMPA[indicador as VariavelClima] : undefined
  const classes = dados ? classesDe(dados.scale, dados.breaks, NEUTRO[dados.metric as 'taxa'], rampa) : []
  const tooltip = clima
    ? (v: { value: number | null; n: number } | undefined) => (
      !v || v.value === null
        ? ['Sem dados no recorte']
        : [`${escapar(NOME_VARIAVEL[indicador as VariavelClima])}: <b>${fmt(v.value, casas)} ${escapar(unidade)}</b>`, `${v.n} meses no recorte`]
    )
    : undefined
  const recurso = clima ? mapaClima : mapaAnom
  const valorSel = selecionado ? dados?.values.find((v) => String(v.codigo_ibge) === selecionado) : undefined
  const nomeSel = selecionado ? nomes.get(selecionado) : undefined
  const resumo = clima ? mapaClima.dados?.resumo : mapaAnom.dados?.summary

  const aviso = !geometrias && !erroMalha
    ? 'Carregando a malha dos 5.573 municípios…'
    : recurso.carregando ? (clima ? 'Calculando as médias municipais…' : 'Calculando a frequência de eventos… (a primeira consulta de cada combinação pode levar alguns segundos)') : null
  const recorteTexto = [
    `${clima ? recorte.inicio : inicioAnom}–${clima ? recorte.fim : fimAnom}`,
    recorte.estacao ? NOMES_ESTACAO[recorte.estacao] : 'todas as estações',
    recorte.enso ? NOME_FASE[recorte.enso] : 'todas as fases ENSO',
  ].join(' · ')

  return (
    <div className="ed-grade ed-grade--mapa">
      <Figura
        numero={numero}
        titulo={clima ? `${NOME_VARIAVEL[indicador as VariavelClima]} média por município` : `Frequência de anomalias — ${ROTULO_ANOMALIA[variavelAnomalia]}`}
        unidade={`Unidade: ${unidade} · ${recorteTexto}`}
        controles={(
          <label className="ed-campo">
            <span>Indicador</span>
            <select value={indicador} onChange={(e) => { setIndicador(e.target.value as Indicador) }}>
              <option value="temperatura">Temperatura média</option>
              <option value="precipitacao">Precipitação média mensal</option>
              <option value="umidade">Umidade relativa média</option>
              <option value="anomalias">Frequência de anomalias ({ROTULO_ANOMALIA[variavelAnomalia].toLowerCase()})</option>
            </select>
          </label>
        )}
        legenda={<>Polígonos municipais do IBGE (simplificados a ≈ 1 km). O mapa mostra todo o país; o filtro de região vale para os demais gráficos. {clima ? 'Classes por quantis dos municípios (sete faixas com números parecidos de municípios).' : `Variável da anomalia escolhida na seção anterior; eventos pontuados a partir de 2017.`}</>}
      >
        <div className="est-mapa">
          <MapaCoropletico
            geometrias={geometrias} dados={dados} nomes={nomes} selecionado={selecionado} onSelecionar={setSelecionado}
            aviso={aviso} erro={recurso.erro || erroMalha ? 'Não foi possível atualizar o mapa' : null}
            rampa={rampa} tooltip={tooltip} onVoltar={() => setSelecionado(null)}
          />
        </div>
      </Figura>
      <aside className="est-mapa-lateral" aria-label="Legenda e resumo do mapa">
        <h3 className="ed-figura__titulo">Legenda</h3>
        <p className="ed-figura__unidade">{unidade}</p>
        {dados
          ? (
            <ul className="est-legenda-mapa">
              {classes.filter((c) => clima || c.max === null || c.max > 0).map((c) => <li key={c.rotulo}><i style={{ background: c.cor }} />{c.rotulo}</li>)}
              {!clima && <li><i style={{ background: HACHURA_CSS }} />Dados insuficientes</li>}
              <li><i style={{ background: PONTILHADO_CSS }} />Sem dados (fora da grade do ERA5-Land ou sem dia válido)</li>
            </ul>
          )
          : <Estado tipo="carregando" altura={180} />}
        {resumo && (
          <dl className="est-mapa-resumo">
            {'com_valor' in resumo
              ? <>
                <div><dt>Municípios com valor</dt><dd>{resumo.com_valor.toLocaleString('pt-BR')}</dd></div>
                <div><dt>Mediana</dt><dd>{fmt(resumo.mediana, casas)}</dd></div>
                <div><dt>Mínimo</dt><dd>{fmt(resumo.min, casas)}</dd></div>
                <div><dt>Máximo</dt><dd>{fmt(resumo.max, casas)}</dd></div>
              </>
              : <>
                <div><dt>Municípios com valor</dt><dd>{resumo.municipalities_with_data.toLocaleString('pt-BR')}</dd></div>
                <div><dt>Eventos no recorte</dt><dd>{resumo.total_events.toLocaleString('pt-BR')}</dd></div>
                <div><dt>Mediana</dt><dd>{fmt(resumo.median, 2)}</dd></div>
              </>}
          </dl>
        )}
        <div className="est-mapa-sel" aria-live="polite">
          {selecionado
            ? <>
              <p className="ed-figura__titulo">{nomeSel ? `${nomeSel.nome} — ${nomeSel.uf}` : `Município ${selecionado}`}</p>
              <p>{valorSel && valorSel.value !== null
                ? <><b>{fmt(valorSel.value, clima ? casas : 2)}</b> {unidade}</>
                : 'Sem valor no recorte.'}</p>
              <button type="button" className="ed-link" onClick={() => setSelecionado(null)}>Limpar seleção</button>
            </>
            : <p className="ed-figura__unidade">Clique em um estado para abrir os municípios dele; depois passe o mouse para ver o valor e clique para fixar um município.</p>}
        </div>
        <p className="ed-kpi__criterio">{clima ? mapaClima.dados?.metodo : mapaAnom.dados?.definition}</p>
      </aside>
    </div>
  )
}
