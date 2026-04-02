import JSZip from 'jszip'
import Papa from 'papaparse'
import type { Row, Tables } from './parser'
import type { CleanReport } from './cleaner'

function toCsv(rows: Row[]): string {
  if (rows.length === 0) return ''
  return Papa.unparse(rows)
}

export async function packageMigration(
  mapped: Tables,
  report: CleanReport,
  destination: string,
  original: Tables,
): Promise<Blob> {
  const zip = new JSZip()

  for (const [table, rows] of Object.entries(mapped)) {
    if (rows.length > 0) zip.file(`${table}.csv`, toCsv(rows))
  }

  // Open invoices (customers with balance > 0, from original pre-mapped data)
  const customers = original.customers ?? []
  const openInvoices = customers.filter(r => parseFloat(r['Balance'] ?? '0') > 0)
  if (openInvoices.length > 0) zip.file('open_invoices.csv', toCsv(openInvoices))

  // Warnings
  const warnings: string[] = []
  if (report.missing_email.length)
    warnings.push(`Missing email (${report.missing_email.length}): ${report.missing_email.join(', ')}`)
  if (report.invalid_phone.length)
    warnings.push(`Invalid phone (${report.invalid_phone.length}): ${report.invalid_phone.join(', ')}`)
  if (report.duplicate_flags.length)
    warnings.push(`Potential duplicates (${report.duplicate_flags.length} pairs): ${report.duplicate_flags.map(p => p.join(' + ')).join('; ')}`)

  const reportText = [
    `exitroutes Migration Report`,
    `Destination: ${destination}`,
    `Generated: ${new Date().toISOString()}`,
    '',
    `Total customers:   ${report.total_customers}`,
    `Active customers:  ${report.active_customers}`,
    `Subscriptions:     ${(mapped.subscriptions ?? []).length}`,
    `Service records:   ${(mapped.service_history ?? []).length}`,
    `Open invoices:     ${openInvoices.length}`,
    '',
    warnings.length
      ? `Warnings:\n${warnings.map(w => `  - ${w}`).join('\n')}`
      : 'No warnings.',
  ].join('\n')

  zip.file('migration_report.txt', reportText)

  return zip.generateAsync({ type: 'blob' })
}
