// Aba Notícias: filtros, paginação, estados e celular (com capturas).
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
const OUT = resolve(process.argv[2] ?? '../docs/frontend/capturas/noticias')
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

const ESTADO = `(() => ({
  resumo: document.querySelector('.news__resumo')?.textContent,
  itens: document.querySelectorAll('.news-item').length,
  primeiro: document.querySelector('.news-item')?.innerText.replace(/\\n/g, ' | ').slice(0, 220),
  paginacao: document.querySelector('.pagination__info')?.textContent ?? null,
  vazio: document.querySelector('.news .eventos__estado')?.textContent ?? null,
  rolagemHorizontal: document.documentElement.scrollWidth > document.documentElement.clientWidth,
}))()`
const pronto = `(!!document.querySelector('.news-list') && !document.querySelector('.news-list.is-loading')) || !!document.querySelector('.news .eventos__estado:not([role=status])')`
async function abaNoticias() {
  await waitFor(`!!document.querySelector('.main-nav__link')`)
  await evaluate(`[...document.querySelectorAll('.main-nav__link')].find((b) => b.textContent === 'Notícias').click()`)
  await waitFor(pronto)
  await waitFor(`document.querySelectorAll('#noticias-municipio option').length > 1`)
  await sleep(400)
}
async function escolher(seletor, valor) {
  await evaluate(`(() => { ${SET_VALUE}; setValue(document.querySelector(${JSON.stringify(seletor)}), ${JSON.stringify(valor)}) })()`)
  await sleep(300)
  await waitFor(pronto)
  await sleep(400)
}

const relatorio = {}
try {
  await send('Page.enable')
  await send('Runtime.enable')
  await send('Emulation.setDeviceMetricsOverride', { width: 1440, height: 1000, deviceScaleFactor: 1, mobile: false })
  await send('Page.navigate', { url: APP })
  await abaNoticias()
  relatorio.todas = await evaluate(ESTADO)
  relatorio.municipios = await evaluate(`[...document.querySelectorAll('#noticias-municipio option')].map((o) => o.textContent)`)
  relatorio.capturas = [await screenshot('01_desktop_noticias_todas.png')]

  await escolher('#noticias-municipio', '5218805')
  relatorio.rio_verde = await evaluate(ESTADO)
  relatorio.capturas.push(await screenshot('02_desktop_noticias_rio-verde.png', '.news', false))

  await escolher('#noticias-municipio', '4314902')
  await escolher('input[type=search]', 'G1')
  await sleep(500)
  await waitFor(pronto)
  relatorio.porto_alegre_g1 = await evaluate(ESTADO)

  await escolher('input[type=search]', '')
  await sleep(500)
  await waitFor(pronto)
  await evaluate(`[...document.querySelectorAll('.pagination .btn')].find((b) => b.textContent.includes('Próxima')).click()`)
  await sleep(300)
  await waitFor(pronto)
  await sleep(600)
  relatorio.porto_alegre_pagina2 = await evaluate(ESTADO)

  await escolher('[aria-label="Ano inicial do evento"]', '2024')
  await escolher('[aria-label="Ano final do evento"]', '2024')
  await escolher('#noticias-ordem', 'publicacao_desc')
  relatorio.porto_alegre_2024_publicacao = await evaluate(ESTADO)
  await evaluate(`scrollTo(0, 0)`)
  relatorio.capturas.push(await screenshot('03_desktop_noticias_porto-alegre_2024.png'))

  await escolher('input[type=search]', 'fonte-inexistente')
  await sleep(500)
  await waitFor(pronto)
  relatorio.vazio = await evaluate(ESTADO)
  relatorio.capturas.push(await screenshot('04_desktop_noticias_sem-resultados.png', '.news', false))

  // celular
  await send('Emulation.setDeviceMetricsOverride', { width: 390, height: 844, deviceScaleFactor: 2, mobile: true })
  await send('Page.navigate', { url: APP })
  await abaNoticias()
  relatorio.celular = await evaluate(ESTADO)
  await send('Page.captureScreenshot', { format: 'png' }).then(({ data }) => writeFileSync(join(OUT, '05_celular_noticias.png'), Buffer.from(data, 'base64')))
} finally {
  writeFileSync(join(OUT, 'relatorio.json'), JSON.stringify(relatorio, null, 2))
  console.log(JSON.stringify(relatorio, null, 2))
  ws.close()
  chrome.kill()
}
