// Mapa: reproduz linhas ao arrastar/dar zoom (recorte do Leaflet).
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
const OUT = resolve(process.argv[2] ?? '../docs/frontend/capturas/mapa')
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

const relatorio = {}
const centroMapa = `(() => { const r = document.querySelector('.leaflet-container').getBoundingClientRect(); return { x: r.left + r.width / 2, y: r.top + r.height / 2, w: r.width, h: r.height } })()`
const DIAG = `(() => {
  const c = document.querySelector('.leaflet-container')
  const svg = c.querySelector('svg.leaflet-zoom-animated')
  const r = c.getBoundingClientRect(), s = svg?.getBoundingClientRect()
  return { container: [Math.round(r.width), Math.round(r.height)], clientSize: [c.clientWidth, c.clientHeight],
    svg: s ? [Math.round(s.left - r.left), Math.round(s.top - r.top), Math.round(s.width), Math.round(s.height)] : null,
    zoomCss: getComputedStyle(document.querySelector('.app-shell')).zoom }
})()`
async function arrastar(dx, dy) {
  const c = await evaluate(centroMapa)
  await send('Input.dispatchMouseEvent', { type: 'mousePressed', x: c.x, y: c.y, button: 'left', clickCount: 1 })
  for (let i = 1; i <= 10; i++) await send('Input.dispatchMouseEvent', { type: 'mouseMoved', x: c.x + dx * i / 10, y: c.y + dy * i / 10, button: 'left', buttons: 1 })
  await sleep(150)
  return c
}


const P = process.env.PREFIX ?? 'estado'
async function clicarNoMapa(fx, fy) {
  const r = await evaluate(`(() => { const r = document.querySelector('.leaflet-container').getBoundingClientRect(); return { x: r.left, y: r.top, w: r.width, h: r.height } })()`)
  const x = r.x + r.w * fx, y = r.y + r.h * fy
  await send('Input.dispatchMouseEvent', { type: 'mouseMoved', x, y })
  await send('Input.dispatchMouseEvent', { type: 'mousePressed', x, y, button: 'left', clickCount: 1 })
  await send('Input.dispatchMouseEvent', { type: 'mouseReleased', x, y, button: 'left', clickCount: 1 })
}
async function mais(n) {
  for (let i = 0; i < n; i++) { await evaluate(`document.querySelector('.leaflet-control-zoom-in').click()`); await sleep(700) }
}
try {
  await send('Page.enable')
  await send('Runtime.enable')
  await send('Emulation.setDeviceMetricsOverride', { width: 1440, height: 1000, deviceScaleFactor: 1, mobile: false })
  await send('Page.navigate', { url: APP })
  await waitFor(`document.querySelectorAll('.leaflet-interactive').length > 20`)
  await sleep(800)
  await evaluate(`document.querySelector('.leaflet-container').scrollIntoView({ block: 'center' })`)
  await sleep(300)
  // Minas Gerais (centro-leste do mapa inicial)
  await clicarNoMapa(0.66, 0.57)
  await waitFor(`document.querySelectorAll('.leaflet-interactive').length > 200`, 60_000)
  await sleep(1200)
  relatorio.poligonos = await evaluate(`document.querySelectorAll('.leaflet-interactive').length`)
  await screenshot(`${P}_1_estado.png`, '.leaflet-container', false)
  await evaluate(`document.querySelector('.leaflet-control-zoom-in').click()`)
  await sleep(90)
  await screenshot(`${P}_1b_durante_animacao_zoom.png`, '.leaflet-container', false)
  await sleep(700)
  await mais(1)
  await screenshot(`${P}_2_zoom2.png`, '.leaflet-container', false)
  await mais(2)
  await screenshot(`${P}_3_zoom4.png`, '.leaflet-container', false)
  const p = await arrastar(-300, -150)
  relatorio.foco = await evaluate(`(() => { const a = document.activeElement; const r = a.getBoundingClientRect(); return { tag: a.tagName, classe: a.getAttribute('class'), tabindex: a.getAttribute('tabindex'), outline: getComputedStyle(a).outlineStyle + ' ' + getComputedStyle(a).outlineWidth + ' ' + getComputedStyle(a).outlineColor, caixa: [Math.round(r.left), Math.round(r.top), Math.round(r.width), Math.round(r.height)] } })()`)
  await screenshot(`${P}_4_arrastando.png`, '.leaflet-container', false)
  await send('Input.dispatchMouseEvent', { type: 'mouseReleased', x: p.x - 300, y: p.y - 150, button: 'left', clickCount: 1 })
  await sleep(700)
  await screenshot(`${P}_5_solto.png`, '.leaflet-container', false)
} finally {
  console.log(JSON.stringify(relatorio))
  ws.close()
  chrome.kill()
}
