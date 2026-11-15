// Verifica a navegação estado → município nos mapas nacionais (Estatísticas e Mapa nacional).
//   CHROME=/caminho/chrome node scripts/mapa-estado-municipio-check.mjs [saida]
// O mapa é desenhado em canvas: o script varre uma grade com o mouse e lê o
// tooltip para achar um estado/município, clica e confere o resultado.
import { spawn } from 'node:child_process'
import { mkdirSync, writeFileSync } from 'node:fs'
import { join, resolve } from 'node:path'

const CHROME = process.env.CHROME
const APP = process.env.APP_URL ?? 'http://localhost:5173/'
const OUT = resolve(process.argv[2] ?? '../docs/frontend/capturas/mapa-estado-municipio')
const PORT = 9336
if (!CHROME) throw new Error('Defina CHROME com o caminho do executável do Chromium')
mkdirSync(OUT, { recursive: true })
const profile = resolve('node_modules/.cache/mapa-estado-check-profile')
mkdirSync(profile, { recursive: true })
const chrome = spawn(CHROME, ['--headless=new', `--remote-debugging-port=${PORT}`, `--user-data-dir=${profile}`,
  '--no-first-run', '--hide-scrollbars', 'about:blank'], { stdio: 'ignore' })
const sleep = (ms) => new Promise((r) => setTimeout(r, ms))
let url
for (let i = 0; i < 100 && !url; i++) {
  try { url = (await (await fetch(`http://127.0.0.1:${PORT}/json/list`)).json()).find((t) => t.type === 'page')?.webSocketDebuggerUrl } catch { /* subindo */ }
  await sleep(100)
}
const ws = new WebSocket(url)
await new Promise((r) => ws.addEventListener('open', r, { once: true }))
let seq = 0
const pend = new Map()
const erros = []
ws.addEventListener('message', (e) => {
  const m = JSON.parse(e.data)
  if (m.id && pend.has(m.id)) { pend.get(m.id)(m); pend.delete(m.id) }
  else if (m.method === 'Runtime.exceptionThrown') erros.push(m.params.exceptionDetails.exception?.description ?? m.params.exceptionDetails.text)
  else if (m.method === 'Runtime.consoleAPICalled' && m.params.type === 'error') erros.push(m.params.args.map((a) => a.value ?? a.description).join(' '))
})
const cdp = (method, params = {}) => new Promise((res, rej) => {
  const id = ++seq
  pend.set(id, (m) => (m.error ? rej(new Error(`${method}: ${m.error.message}`)) : res(m.result)))
  ws.send(JSON.stringify({ id, method, params }))
})
const avaliar = async (x) => (await cdp('Runtime.evaluate', { expression: x, returnByValue: true, awaitPromise: true })).result.value
async function esperar(x, ms = 90000) {
  const fim = Date.now() + ms
  while (Date.now() < fim) { if (await avaliar(x).catch(() => false)) return true; await sleep(250) }
  return false
}
const mover = (x, y) => cdp('Input.dispatchMouseEvent', { type: 'mouseMoved', x, y })
async function clicar(x, y) {
  await mover(x, y)
  await cdp('Input.dispatchMouseEvent', { type: 'mousePressed', x, y, button: 'left', clickCount: 1 })
  await cdp('Input.dispatchMouseEvent', { type: 'mouseReleased', x, y, button: 'left', clickCount: 1 })
}
const tooltip = () => avaliar(`[...document.querySelectorAll('.leaflet-tooltip')].map((t) => t.innerText).join(' | ')`)
const tooltipsAbertos = () => avaliar(`document.querySelectorAll('.leaflet-tooltip').length`)
const dica = (sel) => avaliar(`document.querySelector('${sel} .mapa-status')?.innerText ?? ''`)
const temVoltar = (sel) => avaliar(`!!document.querySelector('${sel} .mapa-voltar')`)
/** varre o mapa até o tooltip conter `texto`; devolve o ponto (coordenadas de viewport) */
async function procurar(sel, teste) {
  const r = await avaliar(`(() => { const b = document.querySelector('${sel} .leaflet-container').getBoundingClientRect(); return { x: b.left, y: b.top, w: b.width, h: b.height } })()`)
  for (let passo = 24; passo >= 8; passo /= 2) {
    for (let y = r.y + 30; y < r.y + r.h - 10; y += passo) {
      for (let x = r.x + 50; x < r.x + r.w - 10; x += passo) {
        await mover(x, y)
        const t = await tooltip()
        if (teste(t)) return { x, y, t }
      }
    }
  }
  return null
}
async function captura(nome) {
  const r = await cdp('Page.captureScreenshot', { format: 'png' })
  writeFileSync(join(OUT, `${nome}.png`), Buffer.from(r.data, 'base64'))
}

await cdp('Page.enable')
await cdp('Runtime.enable')
await cdp('Emulation.setDeviceMetricsOverride', { width: 1440, height: 1000, deviceScaleFactor: 1, mobile: false })
const relatorio = {}

async function testar(nome, rota, sel) {
  const r = {}
  await cdp("Page.navigate", { url: "about:blank" })
  await sleep(300)
  await cdp("Page.navigate", { url: `${APP}?t=${Date.now()}#${rota}` })
  await esperar(`!!document.querySelector('${sel} .leaflet-container canvas')`)
  await avaliar(`document.querySelector('${sel} .leaflet-container').scrollIntoView({ block: 'center' })`)
  // espera a malha, o mapa e os nomes das UFs
  r.carregou = await esperar(`(document.querySelector('${sel} .mapa-status')?.innerText ?? '').startsWith('Clique em um estado')`)
  await sleep(1500)
  r.dica_brasil = await dica(sel)
  r.voltar_no_brasil = await temVoltar(sel)

  // 1) no Brasil, o mouse sobre um município mostra o ESTADO
  const goias = await procurar(sel, (t) => t.includes('Goiás'))
  r.tooltip_brasil = goias?.t
  r.tooltips_abertos_brasil = await tooltipsAbertos()
  await captura(`${nome}_1_brasil_hover_estado`)
  // 2) clique abre o estado
  await clicar(goias.x, goias.y)
  await sleep(1500)
  r.dica_estado = await dica(sel)
  r.voltar_no_estado = await temVoltar(sel)
  await captura(`${nome}_2_estado_aberto`)
  // 3) dentro do estado, o tooltip é do município (com "— GO") e o clique seleciona
  const mun = await procurar(sel, (t) => / — GO/.test(t) && !t.includes('Goiás'))
  r.tooltip_municipio = mun?.t?.split('\n')[0]
  await clicar(mun.x, mun.y)
  await sleep(1500)
  r.selecionado = await avaliar(`(document.querySelector('.est-mapa-sel .ed-figura__titulo') ?? document.querySelector('.analise-mapa__lateral h2'))?.innerText`)
  await captura(`${nome}_3_municipio_selecionado`)
  // 4) clicar num estado esmaecido troca de estado
  const outro = await procurar(sel, (t) => t.includes('Clique para ver os municípios') && !t.includes('Goiás'))
  r.estado_vizinho = outro?.t?.split('\n')[0]
  await clicar(outro.x, outro.y)
  await sleep(1500)
  r.dica_apos_trocar = await dica(sel)
  // 5) voltar ao Brasil limpa a seleção
  await avaliar(`document.querySelector('${sel} .mapa-voltar').click()`)
  await sleep(1500)
  r.dica_apos_voltar = await dica(sel)
  r.voltar_apos_voltar = await temVoltar(sel)
  r.selecao_apos_voltar = await avaliar(`(document.querySelector('.est-mapa-sel .ed-figura__titulo') ?? document.querySelector('.analise-mapa__lateral h2'))?.innerText ?? null`)
  return r
}

relatorio.estatisticas = await testar('estatisticas', 'estatisticas', '#mapa')
relatorio.mapa_nacional = await testar('mapa_nacional', 'analise', '.analise-mapa')
// atalho de Porto Alegre: deve abrir o RS sozinho
await avaliar(`[...document.querySelectorAll('button')].find((b) => /Porto Alegre/.test(b.textContent))?.click()`)
await sleep(2500)
relatorio.mapa_nacional.atalho_porto_alegre_dica = await dica('.analise-mapa')
await captura('mapa_nacional_4_atalho_porto_alegre')
relatorio.erros_console = erros
writeFileSync(join(OUT, 'relatorio.json'), JSON.stringify(relatorio, null, 2))
console.log(JSON.stringify(relatorio, null, 2))
ws.close()
chrome.kill()
