import type { Row, Tables } from './parser'

export interface CleanReport {
  total_customers: number
  active_customers: number
  missing_email: string[]
  invalid_phone: string[]
  duplicate_flags: [string, string][]
  missing_address_fields: string[]
}

function normalizePhone(phone: string | undefined): string | null {
  if (!phone) return null
  const digits = phone.replace(/\D/g, '')
  if (digits.length !== 10) return null
  return `(${digits.slice(0, 3)}) ${digits.slice(3, 6)}-${digits.slice(6)}`
}

function isValidEmail(email: string | undefined): boolean {
  if (!email) return false
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)
}

export function cleanTables(tables: Tables): [Tables, CleanReport] {
  const cleaned: Tables = { ...tables }
  const report: CleanReport = {
    total_customers: 0,
    active_customers: 0,
    missing_email: [],
    invalid_phone: [],
    duplicate_flags: [],
    missing_address_fields: [],
  }

  if (cleaned.customers) {
    const customers: Row[] = cleaned.customers.map(row => ({ ...row }))
    report.total_customers = customers.length

    const emailMap: Record<string, string> = {}

    for (const row of customers) {
      // Phone normalization
      const normalized = normalizePhone(row['Phone1'])
      if (normalized) {
        row['Phone1'] = normalized
      } else {
        row['Phone1'] = ''
        if (row['CustomerID']) report.invalid_phone.push(row['CustomerID'])
      }

      // Email validation
      if (!isValidEmail(row['Email'])) {
        if (row['CustomerID']) report.missing_email.push(row['CustomerID'])
      } else {
        // Duplicate detection
        const emailKey = row['Email']!.toLowerCase()
        const existing = emailMap[emailKey]
        if (existing) {
          report.duplicate_flags.push([existing, row['CustomerID']])
        } else {
          emailMap[emailKey] = row['CustomerID']
        }
      }

      // Service address fallback from billing
      if (!row['ServiceAddress1']) {
        row['ServiceAddress1'] = row['BillingAddress1'] ?? ''
        row['ServiceCity'] = row['BillingCity'] ?? ''
        row['ServiceState'] = row['BillingState'] ?? ''
        row['ServiceZip'] = row['BillingZip'] ?? ''
      }

      // address_is_same flag
      row['address_is_same'] = (
        row['ServiceAddress1'] === row['BillingAddress1'] &&
        row['ServiceCity'] === row['BillingCity']
      ) ? '1' : '0'

      // Active count
      if (row['IsActive'] === '1') report.active_customers++
    }

    cleaned.customers = customers
  }

  return [cleaned, report]
}
