// MapaBrasil.tsx
import { useEffect, useRef, useState } from "react";
import { MapContainer, GeoJSON, useMap } from "react-leaflet";
import L from "leaflet";
import type { Feature, FeatureCollection, Geometry } from "geojson";
import type { Layer, LeafletMouseEvent, PathOptions } from "leaflet";
import "leaflet/dist/leaflet.css";
import "./MapaBrasil.css";

const IBGE = "https://servicodados.ibge.gov.br/api";
const malhaPaisUF = `${IBGE}/v3/malhas/paises/BR?formato=application/vnd.geo+json&qualidade=minima&intrarregiao=UF`;
const malhaMunicipios = (uf: string) =>
  `${IBGE}/v3/malhas/estados/${uf}?formato=application/vnd.geo+json&qualidade=minima&intrarregiao=municipio`;

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
};

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

// ---------- Estilos ----------
const estiloEstado: PathOptions = {
  color: "#5d6d6a", weight: 1.5, fillColor: "#e0ebe5", fillOpacity: 1,
};
const estiloEstadoHover: PathOptions = { fillColor: "#d4ebe6" };

const estiloMunicipio: PathOptions = {
  color: "#9aa8a5", weight: 0.6, fillColor: "#ffffff", fillOpacity: 1,
};
const estiloMunicipioHover: PathOptions = { fillColor: "#d4ebe6", weight: 1 };
const estiloMunicipioSelecionado: PathOptions = {
  color: "#16403f", weight: 2, fillColor: "#247573", fillOpacity: 1,
};

export default function MapaBrasil({ onSelectMunicipio }: MapaBrasilProps) {
  const [estadosGeo, setEstadosGeo] = useState<Geo | null>(null);
  const [estados, setEstados] = useState<Record<string, EstadoInfo>>({});
  const [uf, setUf] = useState<string | null>(null);
  const [munGeo, setMunGeo] = useState<Geo | null>(null);
  const [munNomes, setMunNomes] = useState<Record<string, string>>({});
  const [munSel, setMunSel] = useState<string | null>(null);
  const [carregando, setCarregando] = useState(false);
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
        return;
      }
      setCarregando(false);
    }
    setMunGeo(cache.current[codigo].geo);
    setMunNomes(cache.current[codigo].nomes);
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
    layer.bindTooltip(e ? `${e.nome} — ${e.sigla}` : cod, {
      sticky: true, className: "tooltip-mapa",
    });
    layer.on({
      mouseover: (ev: LeafletMouseEvent) => (ev.target as L.Path).setStyle(estiloEstadoHover),
      mouseout: (ev: LeafletMouseEvent) => (ev.target as L.Path).setStyle(estiloEstado),
      click: () => selecionarEstado(cod),
    });
  };

  const estiloMun = (feature?: Feat): PathOptions =>
    feature?.properties.codarea === munSel
      ? estiloMunicipioSelecionado
      : estiloMunicipio;

  const aoCadaMunicipio = (feature: Feat, layer: Layer) => {
    const cod = feature.properties.codarea;
    const nome = munNomes[cod] ?? cod;
    layer.bindTooltip(`${nome} — ${sigla}`, { sticky: true, className: "tooltip-mapa" });
    layer.on({
      mouseover: (ev: LeafletMouseEvent) => {
        if (cod !== munSel) (ev.target as L.Path).setStyle(estiloMunicipioHover);
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
      {carregando && <div className="mapa-carregando">Carregando municípios…</div>}

      <MapContainer
        center={[-14.2, -51.9]}
        zoom={4}
        zoomSnap={0.25}
        attributionControl={false}
        style={{ height: 600, width: "100%", background: "#dcdcdc" }}
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

        <AjustarVisao geojson={munGeo ?? estadosGeo} />
      </MapContainer>
    </div>
  );
}