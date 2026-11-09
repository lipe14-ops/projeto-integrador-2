// MapaBrasil.tsx
import { useEffect, useMemo, useRef, useState } from "react";
import { CircleMarker, GeoJSON, MapContainer, Pane, Tooltip, useMap } from "react-leaflet";
import L from "leaflet";
import type { Feature, FeatureCollection, Geometry } from "geojson";
import type { Layer, LeafletMouseEvent, PathOptions } from "leaflet";
import "leaflet/dist/leaflet.css";
import "./MapaBrasil.css";
import { AjustarTamanhoMapa } from "../AjustarTamanhoMapa";
import { criarRenderizadorMapa } from "../renderizadorMapa";
import type { MunicipioAnalisado } from "../../data/api";

const IBGE = "https://servicodados.ibge.gov.br/api";
// qualidade "intermediaria": a "minima" é generalizada para escala de país e, com
// zoom no estado, os limites viram segmentos retos que não seguem o território
// (MG: 1,8 MB em vez de 0,5 MB; ~0,6 s).
const malhaPaisUF = `${IBGE}/v3/malhas/paises/BR?formato=application/vnd.geo+json&qualidade=intermediaria&intrarregiao=UF`;
const malhaMunicipios = (uf: string) =>
  `${IBGE}/v3/malhas/estados/${uf}?formato=application/vnd.geo+json&qualidade=intermediaria&intrarregiao=municipio`;

// ---------- Tipos ----------
type Props = { codarea: string };
type Geo = FeatureCollection<Geometry, Props>;
type Feat = Feature<Geometry, Props>;

type EstadoInfo = { sigla: string; nome: string };
type EstadoIBGE = { id: number; sigla: string; nome: string };
type MunicipioIBGE = { id: number; nome: string };

export type MunicipioSelecionado = { codigo: string; nome: string; uf: string };

type MapaBrasilProps = {
  onSelectMunicipio?: (m: MunicipioSelecionado) => void;
  /** Municípios analisados com a contagem de notícias de chuva extrema no período. */
  pontosNoticias?: MunicipioAnalisado[] | null;
  /** Situação da busca dos pontos de notícias (para o aviso de carregamento). */
  statusNoticias?: "carregando" | "erro" | "ok";
};

const textoNoticias = (n: number) => `${n} ${n === 1 ? "notícia verificada" : "notícias verificadas"}`;

// pontos de notícias de desastre: todos do mesmo tamanho
const RAIO_PONTO = 7;
const COR_PONTO = "#c0562b";

async function getJSON<T>(url: string): Promise<T> {
  const r = await fetch(url);
  if (!r.ok) throw new Error(`Erro ${r.status} em ${url}`);
  return r.json() as Promise<T>;
}

// Ajusta o zoom para caber o GeoJSON recebido
function AjustarVisao({ geojson }: { geojson: Geo | null }) {
  const map = useMap();
  useEffect(() => {
    if (!geojson) return;
    map.fitBounds(L.geoJSON(geojson).getBounds(), { padding: [20, 20] });
  }, [geojson, map]);
  return null;
}

// O renderizador SVG padrão desenha só 10% além da área visível e só redesenha
// ao FIM do arraste/zoom: arrastar mais que isso expõe o recorte dos polígonos,
// cujo contorno aparece como linhas retas no mapa (agravado pelo `zoom: 0.9` do
// .app-shell, que faz o Leaflet medir o contêiner ~11% maior). Com padding 1, o
// SVG cobre uma tela inteira em cada direção.
const renderizador = criarRenderizadorMapa();

// ---------- Estilos ----------
const estiloEstado: PathOptions = {
  color: "#5d6d6a", weight: 1.5, fillColor: "#e0ebe5", fillOpacity: 1,
};
const estiloEstadoHover: PathOptions = { color: "#16403f", weight: 3 };

const estiloMunicipio: PathOptions = {
  color: "#9aa8a5", weight: 0.6, fillColor: "#ffffff", fillOpacity: 1,
};
const estiloMunicipioHover: PathOptions = { color: "#16403f", weight: 2 };
const estiloMunicipioSelecionado: PathOptions = {
  color: "#16403f", weight: 2, fillColor: "#247573", fillOpacity: 1,
};

export default function MapaBrasil({ onSelectMunicipio, pontosNoticias, statusNoticias = "ok" }: MapaBrasilProps) {
  const [estadosGeo, setEstadosGeo] = useState<Geo | null>(null);
  const [estados, setEstados] = useState<Record<string, EstadoInfo>>({});
  const [uf, setUf] = useState<string | null>(null);
  const [munGeo, setMunGeo] = useState<Geo | null>(null);
  const [munNomes, setMunNomes] = useState<Record<string, string>>({});
  const [munSel, setMunSel] = useState<string | null>(null);
  const [carregando, setCarregando] = useState(false);
  // clique na legenda liga/desliga os pontos de notícias de desastre
  const [mostrarPontos, setMostrarPontos] = useState(true);
  const cache = useRef<Record<string, { geo: Geo; nomes: Record<string, string> }>>({});

  // Estados: carrega uma vez
  useEffect(() => {
    Promise.all([
      getJSON<Geo>(malhaPaisUF),
      getJSON<EstadoIBGE[]>(`${IBGE}/v1/localidades/estados`),
    ])
      .then(([geo, lista]) => {
        setEstadosGeo(geo);
        setEstados(
          Object.fromEntries(
            lista.map((e) => [String(e.id), { sigla: e.sigla, nome: e.nome }])
          )
        );
      })
      .catch(console.error);
  }, []);

  // Municípios: carrega ao selecionar um estado (com cache)
  const selecionarEstado = async (codigo: string) => {
    setUf(codigo);
    setMunSel(null);
    setMunGeo(null);

    if (!cache.current[codigo]) {
      setCarregando(true);
      try {
        const [geo, lista] = await Promise.all([
          getJSON<Geo>(malhaMunicipios(codigo)),
          getJSON<MunicipioIBGE[]>(`${IBGE}/v1/localidades/estados/${codigo}/municipios`),
        ]);
        cache.current[codigo] = {
          geo,
          nomes: Object.fromEntries(lista.map((m) => [String(m.id), m.nome])),
        };
      } catch (e) {
        console.error(e);
        setUf(null);
        setCarregando(false);
        return false;
      }
      setCarregando(false);
    }
    setMunGeo(cache.current[codigo].geo);
    setMunNomes(cache.current[codigo].nomes);
    return true;
  };

  // municípios com notícia verificada (no estado aberto, só os dele)
  const pontos = useMemo(
    () => (pontosNoticias ?? [])
      .filter((p) => p.noticias > 0 && p.latitude !== null && p.longitude !== null && (!uf || p.codigoIbge.startsWith(uf))),
    [pontosNoticias, uf],
  );

  // clique num ponto: abre o estado (se preciso) e seleciona o município
  const selecionarPonto = async (p: MunicipioAnalisado) => {
    const codUf = p.codigoIbge.slice(0, 2);
    if (uf !== codUf && !(await selecionarEstado(codUf))) return;
    setMunSel(p.codigoIbge);
    onSelectMunicipio?.({ codigo: p.codigoIbge, nome: p.nome, uf: p.uf ?? estados[codUf]?.sigla ?? "" });
  };


  const voltar = () => {
    setUf(null);
    setMunGeo(null);
    setMunSel(null);
  };

  const sigla = uf ? estados[uf]?.sigla ?? "" : "";

  const aoCadaEstado = (feature: Feat, layer: Layer) => {
    const cod = feature.properties.codarea;
    const e = estados[cod];
    layer.bindTooltip(e ? `${e.nome} — ${e.sigla}` : cod, { sticky: true, className: "tooltip-mapa" });
    layer.on({
      mouseover: (ev: LeafletMouseEvent) => {
        (ev.target as L.Path).setStyle(estiloEstadoHover);
        (ev.target as L.Path).bringToFront();
      },
      mouseout: (ev: LeafletMouseEvent) => (ev.target as L.Path).setStyle(estiloEstado),
      click: () => selecionarEstado(cod),
    });
  };

  const estiloMun = (feature?: Feat): PathOptions =>
    feature?.properties.codarea === munSel ? estiloMunicipioSelecionado : estiloMunicipio;

  const aoCadaMunicipio = (feature: Feat, layer: Layer) => {
    const cod = feature.properties.codarea;
    const nome = munNomes[cod] ?? cod;
    layer.bindTooltip(`${nome} — ${sigla}`, { sticky: true, className: "tooltip-mapa" });
    layer.on({
      mouseover: (ev: LeafletMouseEvent) => {
        if (cod === munSel) return;
        (ev.target as L.Path).setStyle(estiloMunicipioHover);
        (ev.target as L.Path).bringToFront();
      },
      mouseout: (ev: LeafletMouseEvent) => {
        if (cod !== munSel) (ev.target as L.Path).setStyle(estiloMunicipio);
      },
      click: () => {
        setMunSel(cod);
        onSelectMunicipio?.({ codigo: cod, nome, uf: sigla });
      },
    });
  };

  return (
    <div className="mapa-wrapper">
      {uf && (
        <button className="mapa-voltar" onClick={voltar}>
          ← Brasil
        </button>
      )}
      {/* avisos de carregamento (um de cada vez, do mais básico ao complementar) */}
      {(() => {
        const aviso = !estadosGeo
          ? "Carregando mapa…"
          : carregando
            ? "Carregando municípios…"
            : statusNoticias === "carregando"
              ? "Carregando notícias de desastre…"
              : null;
        if (aviso) {
          return (
            <div className="mapa-status" role="status" aria-live="polite">
              <span className="loading-spinner" aria-hidden="true" />
              {aviso}
            </div>
          );
        }
        if (statusNoticias === "erro") {
          return <div className="mapa-status mapa-status--erro" role="status">Não foi possível carregar as notícias</div>;
        }
        return null;
      })()}
      {pontos.length > 0 && (
        <button
          type="button"
          className={mostrarPontos ? "mapa-legenda" : "mapa-legenda is-oculto"}
          aria-pressed={mostrarPontos}
          title={mostrarPontos ? "Clique para ocultar os pontos" : "Clique para mostrar os pontos"}
          onClick={() => setMostrarPontos((v) => !v)}
        >
          <span className="mapa-legenda__ponto"><i style={{ background: COR_PONTO }} />Município com notícias de desastre</span>
          <span className="mapa-legenda__dica">{mostrarPontos ? "clique para ocultar" : "oculto · clique para mostrar"}</span>
        </button>
      )}

      <MapContainer
        center={[-14.2, -51.9]}
        zoom={4}
        zoomSnap={0.25}
        renderer={renderizador}
        attributionControl={false}
        style={{ height: 600, width: "100%", background: "#dcdcdc", borderRadius: "13px" }}
      >
        {estadosGeo && (
          <GeoJSON
            key={`uf-${uf}-${Object.keys(estados).length}`}
            data={estadosGeo}
            filter={(f) => (f as Feat).properties.codarea !== uf}
            style={estiloEstado}
            onEachFeature={(f, l) => aoCadaEstado(f as Feat, l)}
          />
        )}

        {munGeo && (
          <GeoJSON
            key={`mun-${uf}-${munSel}`}
            data={munGeo}
            style={(f) => estiloMun(f as Feat | undefined)}
            onEachFeature={(f, l) => aoCadaMunicipio(f as Feat, l)}
          />
        )}

        {/* pontos acima dos polígonos (chegam depois e não podem ficar cobertos) */}
        <Pane name="noticias" style={{ zIndex: 450 }}>
          {mostrarPontos && pontos.map((p) => {
            const ativo = p.codigoIbge === munSel;
            return (
              <CircleMarker
                key={p.codigoIbge}
                center={[p.latitude!, p.longitude!]}
                radius={RAIO_PONTO}
                pathOptions={{
                  color: ativo ? "#16403f" : "#ffffff",
                  weight: ativo ? 3 : 2,
                  fillColor: COR_PONTO,
                  fillOpacity: 0.9,
                }}
                eventHandlers={{ click: () => void selecionarPonto(p) }}
              >
                <Tooltip direction="top" offset={[0, -RAIO_PONTO]} className="tooltip-mapa">
                  <b>{p.nome}{p.uf ? ` — ${p.uf}` : ""}</b>
                  <br />
                  {textoNoticias(p.noticias)} de desastre por chuva
                  <br />
                  Clique para ver o município
                </Tooltip>
              </CircleMarker>
            );
          })}
        </Pane>

        <AjustarVisao geojson={munGeo ?? estadosGeo} />
        <AjustarTamanhoMapa />
      </MapContainer>
    </div>
  );
}