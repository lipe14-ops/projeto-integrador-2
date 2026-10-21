import { useEffect, useState } from 'react'
import { Button, Card, Col, Row, Select, Tooltip, Typography } from 'antd'
import { HiMiniAdjustmentsHorizontal } from 'react-icons/hi2'
import { IoReload } from 'react-icons/io5'
import { IoIosInformationCircleOutline } from 'react-icons/io'
import type { Municipio } from '../data/climate'

export interface Filtros { municipio: Municipio; de: number; ate: number }
interface Props {
  municipios: Municipio[]; filtros: Filtros; onAplicar: (f: Filtros) => void; carregando?: boolean
}
const { Text } = Typography
const anos = Array.from({ length: 11 }, (_, i) => 2015 + i)

export function SearchFilters({ municipios, filtros, onAplicar, carregando }: Props) {
  const [rascunho, setRascunho] = useState(filtros)
  useEffect(() => setRascunho(filtros), [filtros])
  return (
    <Card className="card">
      <Row gutter={[16, 16]} align="bottom">
        <Col xs={24} sm={12} lg={10}>
          <Text style={{ fontSize: 15 }}>Município</Text>
          <Select
            showSearch allowClear size="large" loading={carregando}
            placeholder="Pesquisar município..." optionFilterProp="label"
            value={rascunho.municipio.ibge}
            options={municipios.map((m) => ({ value: m.ibge, label: `${m.nome} — ${m.uf}` }))}
            onChange={(codigo) => { const municipio = municipios.find((m) => m.ibge === codigo); if (municipio) setRascunho({ ...rascunho, municipio }) }}
            style={{ width: '100%' }}
          />
        </Col>
        <Col xs={24} sm={12} lg={8}>
          <Text style={{ fontSize: 15 }}>Período <Tooltip title="Dados disponíveis de 2015 até 2025"><IoIosInformationCircleOutline size={17} /></Tooltip></Text>
          <Row align="middle">
            <Select size="large" value={rascunho.de} options={anos.map((ano) => ({ value: ano, label: ano }))} onChange={(de) => setRascunho({ ...rascunho, de, ate: Math.max(de, rascunho.ate) })} style={{ width: '43%' }} />
            <Text style={{ margin: '0 10px' }}>até</Text>
            <Select size="large" value={rascunho.ate} options={anos.filter((ano) => ano >= rascunho.de).map((ano) => ({ value: ano, label: ano }))} onChange={(ate) => setRascunho({ ...rascunho, ate })} style={{ width: '43%' }} />
          </Row>
        </Col>
        <Col xs={24} sm={24} lg={6}>
          <Button size="large" style={{ backgroundColor: '#066262', color: 'white' }} onClick={() => onAplicar(rascunho)}><HiMiniAdjustmentsHorizontal /> Aplicar filtros</Button>
          <Button size="large" style={{ marginLeft: 8 }} onClick={() => { const novo = { ...rascunho, de: 2015, ate: 2025 }; setRascunho(novo); onAplicar(novo) }}><IoReload /> Limpar período</Button>
        </Col>
      </Row>
    </Card>
  )
}
