import Papa from 'papaparse'

export type Row = Record<string, string>
export type Tables = Record<string, Row[]>

const SIGNATURES: Record<string, string[]> = {
  customers: ['CustomerID', 'FirstName', 'LastName', 'BillingAddress1'],
  subscriptions: ['SubscriptionID', 'CustomerID', 'ServiceType', 'Frequency'],
  service_history: ['AppointmentID', 'CustomerID', 'ServiceDate', 'TechnicianID'],
}

function detectTable(headers: string[]): string | null {
  const headerSet = new Set(headers)
  for (const [table, sig] of Object.entries(SIGNATURES)) {
    if (sig.every(col => headerSet.has(col))) return table
  }
  return null
}

export function parseFiles(files: File[]): Promise<Tables> {
  return new Promise((resolve) => {
    const tables: Tables = {}
    let pending = files.length
    if (pending === 0) { resolve(tables); return }

    for (const file of files) {
      Papa.parse<Row>(file, {
        header: true,
        skipEmptyLines: true,
        transformHeader: (h: string) => h.trim().replace(/^\uFEFF/, ''),
        complete: (result) => {
          const tableType = detectTable(result.meta.fields ?? [])
          if (tableType) tables[tableType] = result.data
          if (--pending === 0) resolve(tables)
        },
        error: () => {
          if (--pending === 0) resolve(tables)
        },
      })
    }
  })
}
