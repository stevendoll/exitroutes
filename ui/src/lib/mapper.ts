import type { Row, Tables } from './parser'
import gorilladesk from '../config/gorilladesk.json'
import jobber from '../config/jobber.json'
import housecallpro from '../config/housecallpro.json'

interface TableConfig {
  column_map: Record<string, string>
  drop: string[]
}

interface DestConfig {
  destination: string
  customers?: TableConfig
  subscriptions?: TableConfig
  service_history?: TableConfig
}

const CONFIGS: Record<string, DestConfig> = {
  'GorillaDesk': gorilladesk,
  'Jobber': jobber,
  'Housecall Pro': housecallpro,
}

export const DESTINATIONS = Object.keys(CONFIGS)

function mapTable(rows: Row[], config: TableConfig): Row[] {
  return rows.map(row => {
    const mapped: Row = {}
    for (const [from, to] of Object.entries(config.column_map)) {
      if (from in row) mapped[to] = row[from]
    }
    return mapped
  })
}

export function mapTables(tables: Tables, destination: string): Tables {
  const cfg = CONFIGS[destination]
  if (!cfg) throw new Error(`Unknown destination: ${destination}`)

  const mapped: Tables = {}
  for (const [table, rows] of Object.entries(tables)) {
    const tableCfg = (cfg as unknown as Record<string, unknown>)[table] as TableConfig | undefined
    mapped[table] = tableCfg ? mapTable(rows, tableCfg) : rows
  }
  return mapped
}
