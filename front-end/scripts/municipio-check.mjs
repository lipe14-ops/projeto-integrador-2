// Tarefas do agente Usuário nas melhorias de UX (eventos extremos, comparação, desempenho).
// Pré-requisitos: API em 127.0.0.1:8000, Vite em 127.0.0.1:5173 e um Chromium.
//   CHROME=/caminho/chrome node scripts/visual-check.mjs [saida]
// Simula as tarefas do agente Usuário: escolher estado/município/período,
// localizar o mês mais chuvoso, ler a estação no tooltip (mouse e toque) e
// mede as dimensões dos três gráficos em desktop e celular.
import { spawn } from 'node:child_process'
import { mkdirSync, writeFileSync } from 'node:fs'
import { join, resolve } from 'node:path'

const CHROME = process.env.CHROME
const APP = process.env.APP_URL ?? 'http://127.0.0.1:5173/'
const OUT = resolve(process.argv[2] ?? '../docs/frontend/capturas/municipio')
const PORT = 9333
mkdirSync(OUT, { recursive: true })
if (!CHROME) throw new Error('Defina CHROME com o caminho do executável do Chromium')

const profile = resolve('node_modules/.cache/visual-check-profile')
mkdirSync(profile, { recursive: true })
const chrome = spawn(CHROME, [
  '--headless=new', `--remote-debugging-port=${PORT}`, `--user-data-dir=${profile}`,
  '--no-first-run', '--no-default-browser-check', '--disable-gpu', 'about:blank',
], { stdio: 'ignore' })

const sleep = (ms) => new Promise((r) => setTimeout(r, ms))
async function json(path, method = 'GET') {
  let ultimo
  for (let i = 0; i < 150; i++) {
    try {
      const resposta = await fetch(`http://127.0.0.1:${PORT}${path}`, { method })
      const texto = await resposta.text()
      try { return JSON.parse(texto) } catch { ultimo = new Error(`resposta inesperada: ${texto.slice(0, 200)}`) }
    } catch (erro) { ultimo = erro }
    await sleep(200)
  }
  throw new Error(`Chromium não respondeu: ${ultimo?.message}`)
}

const target = await json(`/json/new?${encodeURIComponent('about:blank')}`, 'PUT')
const ws = new WebSocket(target.webSocketDebuggerUrl)
await new Promise((r) => ws.addEventListener('open', r, { once: true }))
let seq = 0
const pending = new Map()
ws.addEventListener('message', (ev) => {
  const msg = JSON.parse(ev.data)
  if (msg.id && pending.has(msg.id)) {
    const { resolve: ok, reject } = pending.get(msg.id)
    pending.delete(msg.id)
    if (msg.error) reject(new Error(JSON.stringify(msg.error)))
    else ok(msg.result)
  }
})
const send = (method, params = {}) => new Promise((ok, reject) => {
  const id = ++seq
  pending.set(id, { resolve: ok, reject })
  ws.send(JSON.stringify({ id, method, params }))
})
async function evaluate(expression) {
  const r = await send('Runtime.evaluate', { expression, awaitPromise: true, returnByValue: true })
  if (r.exceptionDetails) throw new Error(r.exceptionDetails.exception?.description ?? r.exceptionDetails.text)
  return r.result.value
}
async function waitFor(expression, timeout = 180_000) {
  const t0 = Date.now()
  while (Date.now() - t0 < timeout) {
    if (await evaluate(expression)) return
    await sleep(500)
  }
  throw new Error(`timeout esperando: ${expression}`)
}
async function screenshot(name, selector, beyond = true, ate = null) {
  // ate: seletor do último elemento incluído no recorte (recorte de vários elementos)
  const clip = selector
    ? await evaluate(`(() => { const r = document.querySelector(${JSON.stringify(selector)}).getBoundingClientRect();
        const f = ${JSON.stringify(ate)} ? document.querySelector(${JSON.stringify(ate)}).getBoundingClientRect() : r;
        return { x: r.left + scrollX, y: r.top + scrollY, width: r.width, height: f.bottom - r.top, scale: 1 } })()`)
    : undefined
  // recorte maior que a viewport sai em branco sem captureBeyondViewport
  if (clip && !beyond) beyond = clip.height > (await evaluate('innerHeight'))
  const { data } = await send('Page.captureScreenshot', { format: 'png', captureBeyondViewport: beyond, ...(clip ? { clip } : {}) })
  writeFileSync(join(OUT, name), Buffer.from(data, 'base64'))
  return join(OUT, name)
}

const SET_VALUE = `
  function setValue(el, value) {
    const proto = el.tagName === 'SELECT' ? HTMLSelectElement.prototype : HTMLInputElement.prototype
    Object.getOwnPropertyDescriptor(proto, 'value').set.call(el, value)
    el.dispatchEvent(new Event(el.tagName === 'SELECT' ? 'change' : 'input', { bubbles: true }))
  }`

async function selecionar(uf, municipio, de, ate) {
  await waitFor(`document.querySelector('#estado')?.options.length > 5`)
  await evaluate(`(() => { ${SET_VALUE}; setValue(document.querySelector('#estado'), ${JSON.stringify(uf)}) })()`)
  await sleep(200)
  await evaluate(`(() => { ${SET_VALUE}
    setValue(document.querySelector('#municipio'), ${JSON.stringify(municipio)})
    setValue(document.querySelector('[aria-label="Ano inicial"]'), ${JSON.stringify(String(de))})
    setValue(document.querySelector('[aria-label="Ano final"]'), ${JSON.stringify(String(ate))}) })()`)
  await sleep(200)
  await evaluate(`document.querySelector('form').requestSubmit()`)
  await waitFor(`document.querySelectorAll('.chart-card .recharts-cartesian-grid').length === 3`)
  await sleep(800)
}

const MEDIDAS = `(() => {
  const cards = [...document.querySelectorAll('.chart-card')]
  return {
    graficos: cards.map((c) => {
      const titulo = c.querySelector('h3').textContent
      const wrap = c.querySelector('.chart-wrap').getBoundingClientRect()
      const grid = c.querySelector('.recharts-cartesian-grid').getBoundingClientRect()
      return {
        titulo,
        card: [Math.round(c.getBoundingClientRect().left), Math.round(c.getBoundingClientRect().width)],
        area: [Math.round(wrap.width), Math.round(wrap.height)],
        plot: [Math.round(grid.left), Math.round(grid.width), Math.round(grid.height)],
        faixas: c.querySelectorAll('.recharts-reference-area').length,
      }
    }),
    rolagemHorizontal: document.documentElement.scrollWidth > document.documentElement.clientWidth,
    legendaEstacoes: [...document.querySelectorAll('.legend__seasons')].map((u) => u.textContent),
  }
})()`

async function tooltipNoMeio(chartIndex, touch = false) {
  const p = await evaluate(`(() => { const g = document.querySelectorAll('.chart-card .recharts-cartesian-grid')[${chartIndex}];
    g.scrollIntoView({ block: 'center' }); const r = g.getBoundingClientRect();
    return { x: r.left + r.width * 0.55, y: r.top + r.height * 0.5 } })()`)
  await sleep(300)
  if (touch) {
    await send('Input.dispatchTouchEvent', { type: 'touchStart', touchPoints: [{ x: p.x, y: p.y }] })
    await sleep(80)
    await send('Input.dispatchTouchEvent', { type: 'touchEnd', touchPoints: [] })
  } else {
    await send('Input.dispatchMouseEvent', { type: 'mouseMoved', x: p.x, y: p.y })
  }
  await sleep(500)
  return evaluate(`[...document.querySelectorAll('.chart-tooltip')].map((t) => t.innerText.replace(/\\n/g, ' | '))`)
}

try {
  await send('Page.enable')
  await send('Runtime.enable')
  await send('Emulation.setDeviceMetricsOverride', { width: 1440, height: 1000, deviceScaleFactor: 1, mobile: false })
  await send('Page.navigate', { url: APP })
  await selecionar('GO', 'Rio Verde — GO', 2015, 2025)
  await evaluate(`document.querySelector('.municipio-card').scrollIntoView({ block: 'start' })`)
  await sleep(300)
  await screenshot('01_cartao_fechado.png', '.municipio-card', false)
  await evaluate(`document.querySelector('.municipio-mais summary').click()`)
  await sleep(400)
  console.log(await evaluate(`document.querySelector('.municipio-mais').innerText`))
  await screenshot('02_cartao_aberto.png', '.municipio-card', true)
} finally {
  ws.close()
  chrome.kill()
}
