// QA visual das páginas Início e Estatísticas gerais (Chrome DevTools Protocol, sem dependências).
// Pré-requisitos: API em 127.0.0.1:8000, Vite em localhost:5173 e um Chromium.
//   CHROME=/caminho/chrome node scripts/estatisticas-check.mjs [saida]
// Gera capturas de página inteira (desktop e celular), testa filtros e
// navegação e grava relatorio.json com erros de console, estouro horizontal
// e o texto dos indicadores.
import { spawn } from 'node:child_process'
import { mkdirSync, writeFileSync } from 'node:fs'
import { join, resolve } from 'node:path'

const CHROME = process.env.CHROME
const APP = process.env.APP_URL ?? 'http://localhost:5173/'
const OUT = resolve(process.argv[2] ?? '../docs/frontend/capturas/estatisticas')
const PORT = 9334
if (!CHROME) throw new Error('Defina CHROME com o caminho do executável do Chromium')
mkdirSync(OUT, { recursive: true })

const profile = resolve('node_modules/.cache/estatisticas-check-profile')
mkdirSync(profile, { recursive: true })
const chrome = spawn(CHROME, [
  '--headless=new', `--remote-debugging-port=${PORT}`, `--user-data-dir=${profile}`,
  '--no-first-run', '--no-default-browser-check', '--hide-scrollbars', 'about:blank',
], { stdio: 'ignore' })
const sleep = (ms) => new Promise((r) => setTimeout(r, ms))

async function alvo() {
  for (let i = 0; i < 100; i++) {
    try {
      const lista = await (await fetch(`http://127.0.0.1:${PORT}/json/list`)).json()
      const pagina = lista.find((t) => t.type === 'page')
      if (pagina) return pagina.webSocketDebuggerUrl
    } catch { /* ainda subindo */ }
    await sleep(100)
  }
  throw new Error('Chromium não respondeu')
}

const ws = new WebSocket(await alvo())
await new Promise((r) => ws.addEventListener('open', r, { once: true }))
let seq = 0
const pendentes = new Map()
const erros = []
let fase = 'inicio'
ws.addEventListener('message', (ev) => {
  const msg = JSON.parse(ev.data)
  if (msg.id && pendentes.has(msg.id)) {
    pendentes.get(msg.id)(msg)
    pendentes.delete(msg.id)
  } else if (msg.method === 'Runtime.exceptionThrown') {
    erros.push(msg.params.exceptionDetails.exception?.description ?? msg.params.exceptionDetails.text)
  } else if (msg.method === 'Runtime.consoleAPICalled' && ['error', 'warning'].includes(msg.params.type)) {
    erros.push(`[${fase}] ${msg.params.type}: ${msg.params.args.map((a) => a.value ?? a.description).join(' ')}`)
  } else if (msg.method === 'Log.entryAdded' && msg.params.entry.level === 'error') {
    erros.push(`log: ${msg.params.entry.text} ${msg.params.entry.url ?? ''}`)
  }
})
function cdp(method, params = {}) {
  const id = ++seq
  ws.send(JSON.stringify({ id, method, params }))
  return new Promise((resolveMsg, reject) => pendentes.set(id, (m) => (m.error ? reject(new Error(`${method}: ${m.error.message}`)) : resolveMsg(m.result))))
}
async function avaliar(expr) {
  const r = await cdp('Runtime.evaluate', { expression: expr, awaitPromise: true, returnByValue: true })
  if (r.exceptionDetails) throw new Error(r.exceptionDetails.exception?.description ?? 'erro no evaluate')
  return r.result.value
}
async function esperar(expr, ms = 60000) {
  const fim = Date.now() + ms
  while (Date.now() < fim) {
    if (await avaliar(expr).catch(() => false)) return true
    await sleep(250)
  }
  return false
}
async function viewport(largura, altura, celular = false) {
  await cdp('Emulation.setDeviceMetricsOverride', { width: largura, height: altura, deviceScaleFactor: 1, mobile: celular })
}
async function captura(nome, inteira = true) {
  // página inteira: aumenta o viewport até a altura do conteúdo e espera os gráficos
  // (ResizeObserver) se ajustarem; captureBeyondViewport redimensiona no meio da captura
  const { cssLayoutViewport: vp } = await cdp('Page.getLayoutMetrics')
  if (inteira) {
    const { cssContentSize } = await cdp('Page.getLayoutMetrics')
    const altura = Math.min(Math.ceil(cssContentSize.height), 16000)
    await cdp('Emulation.setDeviceMetricsOverride', { width: vp.clientWidth, height: altura, deviceScaleFactor: 1, mobile: vp.clientWidth < 600 })
    await sleep(1500)
  }
  const r = await cdp('Page.captureScreenshot', { format: 'png' })
  writeFileSync(join(OUT, `${nome}.png`), Buffer.from(r.data, 'base64'))
  if (inteira) {
    await cdp('Emulation.setDeviceMetricsOverride', { width: vp.clientWidth, height: vp.clientWidth < 600 ? 844 : 900, deviceScaleFactor: 1, mobile: vp.clientWidth < 600 })
    await sleep(500)
  }
}
const estouro = () => avaliar('document.documentElement.scrollWidth - document.documentElement.clientWidth')
const semCarregando = '!document.querySelector(".ed-carregando") && !document.querySelector(".mapa-status")'
const selecionar = (rotulo, valor) => avaliar(`(() => {
  const campo = [...document.querySelectorAll('.ed-filtros label.ed-campo, .ed-filtros .ed-campo')].find((c) => c.textContent.trim().startsWith(${JSON.stringify(rotulo)}))
  const s = campo.querySelector('select')
  const setter = Object.getOwnPropertyDescriptor(HTMLSelectElement.prototype, 'value').set
  setter.call(s, ${JSON.stringify(valor)}); s.dispatchEvent(new Event('change', { bubbles: true })); return s.value
})()`)

await cdp('Page.enable')
await cdp('Runtime.enable')
await cdp('Log.enable')
const relatorio = {}

// ---------- Início (desktop) ----------
await viewport(1440, 900)
await cdp('Page.navigate', { url: APP })
relatorio.inicio_carregou = await esperar(`document.querySelector('.inicio h1')?.textContent === 'Clima Brasil' && ${semCarregando}`)
await sleep(800)
relatorio.inicio_kpis = await avaliar(`[...document.querySelectorAll('.inicio-abrangencia .ed-kpi')].map((k) => k.innerText.replace(/\\n+/g, ' | '))`)
relatorio.inicio_capacidades = await avaliar(`document.querySelectorAll('.inicio-capacidade svg.recharts-surface').length`)
relatorio.inicio_ufs_coloridas = await avaliar(`[...document.querySelectorAll('.ed-mapa-uf svg path')].filter((p) => p.getAttribute('fill') && p.getAttribute('fill') !== '#ffffff' && p.getAttribute('fill') !== 'none').length`)
relatorio.inicio_estouro_desktop = await estouro()
await captura('01_inicio_desktop')

// ---------- Início (celular) ----------
await viewport(390, 844, true)
await sleep(800)
relatorio.inicio_estouro_celular = await estouro()
await captura('02_inicio_celular')

fase = 'estatisticas'
// ---------- Navegação: botão "Explorar estatísticas" ----------
await viewport(1440, 900)
await avaliar(`[...document.querySelectorAll('button')].find((b) => b.textContent.trim() === 'Explorar estatísticas').click()`)
relatorio.hash_apos_botao = await avaliar('location.hash')
relatorio.estatisticas_carregou = await esperar(`document.querySelector('.estatisticas h1')?.offsetParent !== null && ${semCarregando}`, 90000)
await sleep(1500)
relatorio.estatisticas_kpis = await avaliar(`[...document.querySelectorAll('.estatisticas .ed-kpis')[0].querySelectorAll('.ed-kpi')].map((k) => k.querySelector('.ed-kpi__rotulo').innerText + ': ' + k.querySelector('.ed-kpi__valor').innerText)`)
relatorio.estatisticas_graficos = await avaliar(`document.querySelectorAll('.estatisticas svg.recharts-surface').length`)
relatorio.mapa_poligonos = await avaliar(`document.querySelectorAll('.estatisticas .leaflet-container canvas').length`)
relatorio.estatisticas_estouro_desktop = await estouro()
await captura('03_estatisticas_desktop')

fase = 'filtros'
// ---------- Filtros: Sul, inverno, La Niña, 2020–2024 ----------
const antes = relatorio.estatisticas_kpis
await selecionar('Região', 'Sul')
await selecionar('Estação', 'inverno')
await selecionar('Fase ENSO', 'la_nina')
await avaliar(`(() => { const s = document.querySelector('[aria-label="Ano inicial"]'); Object.getOwnPropertyDescriptor(HTMLSelectElement.prototype, 'value').set.call(s, '2020'); s.dispatchEvent(new Event('change', { bubbles: true })) })()`)
await avaliar(`(() => { const s = document.querySelector('[aria-label="Ano final"]'); Object.getOwnPropertyDescriptor(HTMLSelectElement.prototype, 'value').set.call(s, '2024'); s.dispatchEvent(new Event('change', { bubbles: true })) })()`)
await esperar(`!document.querySelector('.ed-atualizando') && ${semCarregando}`, 90000)
await sleep(1500)
relatorio.filtro_resumo = await avaliar(`document.querySelector('.ed-filtros__resumo').innerText`)
relatorio.filtro_kpis = await avaliar(`[...document.querySelectorAll('.estatisticas .ed-kpis')[0].querySelectorAll('.ed-kpi')].map((k) => k.innerText.replace(/\\n+/g, ' | '))`)
relatorio.filtro_mudou_kpis = JSON.stringify(antes) !== JSON.stringify(relatorio.filtro_kpis)
await captura('04_estatisticas_filtro_sul_inverno_lanina')

// ---------- Mapa: precipitação e anomalias ----------
await avaliar(`(() => { const s = [...document.querySelectorAll('#mapa select')][0]; Object.getOwnPropertyDescriptor(HTMLSelectElement.prototype, 'value').set.call(s, 'anomalias'); s.dispatchEvent(new Event('change', { bubbles: true })) })()`)
await esperar(`!document.querySelector('#mapa .mapa-status')`, 90000)
await sleep(1000)
relatorio.mapa_anomalias_legenda = await avaliar(`document.querySelector('.est-legenda-mapa')?.innerText`)
await avaliar(`document.getElementById('mapa').scrollIntoView()`)
await sleep(500)
await captura('05_mapa_anomalias_viewport', false)

fase = 'celular'
// ---------- Celular ----------
await avaliar(`document.querySelector('.ed-link') && [...document.querySelectorAll('.ed-filtros .ed-link')].find((b) => b.textContent.includes('Limpar'))?.click()`)
await esperar(`!document.querySelector('.ed-atualizando') && ${semCarregando}`, 90000)
await viewport(390, 844, true)
await avaliar('window.scrollTo(0, 0)')
await sleep(1500)
relatorio.estatisticas_estouro_celular = await estouro()
relatorio.elementos_largos_celular = await avaliar(`[...document.querySelectorAll('.estatisticas *')].filter((e) => e.getBoundingClientRect().right > document.documentElement.clientWidth + 1 && !e.closest('.ed-tabela-wrap') && !e.closest('.leaflet-container')).slice(0, 8).map((e) => e.className || e.tagName)`)
await captura('06_estatisticas_celular')

fase = 'rotas'
// ---------- Rotas existentes preservadas ----------
await viewport(1440, 900)
for (const rota of ['explorar', 'analise', 'sobre']) {
  await cdp('Page.navigate', { url: `${APP}#${rota}` })
  await sleep(2500)
  relatorio[`rota_${rota}`] = await avaliar(`document.querySelector('main')?.innerText.slice(0, 80)`)
}

relatorio.erros_console = erros
writeFileSync(join(OUT, 'relatorio.json'), JSON.stringify(relatorio, null, 2))
console.log(JSON.stringify(relatorio, null, 2))
ws.close()
chrome.kill()
