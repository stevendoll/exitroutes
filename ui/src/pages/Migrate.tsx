import { useState, useRef } from 'react'
import { parseFiles } from '../lib/parser'
import { cleanTables } from '../lib/cleaner'
import { mapTables, DESTINATIONS } from '../lib/mapper'
import { packageMigration } from '../lib/packager'
import type { Tables } from '../lib/parser'
import type { CleanReport } from '../lib/cleaner'

type Stage = 'upload' | 'processing' | 'done' | 'error'

interface Result {
  blob: Blob
  report: CleanReport
  mapped: Tables
  destination: string
}

export default function Migrate() {
  const [files, setFiles] = useState<File[]>([])
  const [destination, setDestination] = useState(DESTINATIONS[0])
  const [stage, setStage] = useState<Stage>('upload')
  const [progress, setProgress] = useState(0)
  const [progressLabel, setProgressLabel] = useState('')
  const [result, setResult] = useState<Result | null>(null)
  const [errorMsg, setErrorMsg] = useState('')
  const [dragOver, setDragOver] = useState(false)
  const inputRef = useRef<HTMLInputElement>(null)

  function addFiles(incoming: FileList | null) {
    if (!incoming) return
    const csvs = Array.from(incoming).filter(f => f.name.endsWith('.csv'))
    setFiles(prev => {
      const existing = new Set(prev.map(f => f.name))
      return [...prev, ...csvs.filter(f => !existing.has(f.name))]
    })
  }

  async function process() {
    if (files.length === 0) return
    setStage('processing')
    setProgress(0)

    try {
      setProgressLabel('01 — Parsing files...')
      setProgress(15)
      const tables = await parseFiles(files)
      if (Object.keys(tables).length === 0) {
        throw new Error('No recognizable FieldRoutes CSV files found. Check that you uploaded the right files.')
      }

      setProgressLabel('02 — Cleaning data...')
      setProgress(40)
      const [cleaned, report] = cleanTables(tables)

      setProgressLabel('03 — Mapping to destination format...')
      setProgress(65)
      const mapped = mapTables(cleaned, destination)

      setProgressLabel('04 — Generating migration package...')
      setProgress(85)
      const blob = await packageMigration(mapped, report, destination, cleaned)

      setProgress(100)
      setProgressLabel('Done.')
      setResult({ blob, report, mapped, destination })
      setStage('done')
    } catch (e) {
      setErrorMsg(e instanceof Error ? e.message : 'Unexpected error')
      setStage('error')
    }
  }

  function reset() {
    setFiles([])
    setStage('upload')
    setProgress(0)
    setProgressLabel('')
    setResult(null)
    setErrorMsg('')
  }

  function downloadUrl() {
    if (!result) return '#'
    return URL.createObjectURL(result.blob)
  }

  const warningCount = result
    ? result.report.missing_email.length +
      result.report.invalid_phone.length +
      result.report.duplicate_flags.length +
      result.report.missing_address_fields.length
    : 0

  return (
    <div className="migrate-page">
      <nav>
        <a href="/" className="logo">exit<span>routes</span></a>
      </nav>

      <main className="migrate-main">
        <p className="section-head">// migration tool</p>
        <h1>FieldRoutes Migration</h1>
        <p className="migrate-sub">Upload your export CSVs → select destination → download ready-to-import package</p>

        {(stage === 'upload' || stage === 'error') && (
          <>
            <div
              className={`upload-zone${dragOver ? ' drag-over' : ''}`}
              onDragOver={e => { e.preventDefault(); setDragOver(true) }}
              onDragLeave={() => setDragOver(false)}
              onDrop={e => { e.preventDefault(); setDragOver(false); addFiles(e.dataTransfer.files) }}
              onClick={() => inputRef.current?.click()}
            >
              <input
                ref={inputRef}
                type="file"
                accept=".csv"
                multiple
                onChange={e => addFiles(e.target.files)}
                style={{ display: 'none' }}
              />
              <div className="upload-icon">📂</div>
              <p className="upload-label">
                <strong>Click to choose</strong> or drag CSV files here
              </p>
              <p className="upload-label" style={{ marginTop: '0.35rem', fontSize: '0.72rem' }}>
                customers.csv · subscriptions.csv · service_history.csv
              </p>
            </div>

            {files.length > 0 && (
              <div className="files-list">
                {files.map(f => (
                  <span key={f.name} className="file-tag">{f.name}</span>
                ))}
              </div>
            )}

            <div className="dest-row">
              <label>MIGRATING TO</label>
              <select value={destination} onChange={e => setDestination(e.target.value)}>
                {DESTINATIONS.map(d => <option key={d}>{d}</option>)}
              </select>
            </div>

            {stage === 'error' && <div className="error-box">{errorMsg}</div>}

            <button
              className="process-btn"
              disabled={files.length === 0}
              onClick={process}
            >
              Process migration →
            </button>
          </>
        )}

        {stage === 'processing' && (
          <>
            <div className="progress-bar-wrap">
              <div className="progress-bar-fill" style={{ width: `${progress}%` }} />
            </div>
            <p className="progress-label">{progressLabel}</p>
          </>
        )}

        {stage === 'done' && result && (
          <>
            <div className="metrics-grid">
              <div className="metric-card">
                <div className="metric-value">{result.report.total_customers}</div>
                <div className="metric-label">Customers</div>
              </div>
              <div className="metric-card">
                <div className="metric-value">{(result.mapped.subscriptions ?? []).length}</div>
                <div className="metric-label">Subscriptions</div>
              </div>
              <div className="metric-card">
                <div className="metric-value">{(result.mapped.service_history ?? []).length}</div>
                <div className="metric-label">Service records</div>
              </div>
              <div className="metric-card">
                <div className="metric-value">{warningCount}</div>
                <div className="metric-label">Warnings</div>
              </div>
            </div>

            {warningCount > 0 && (
              <div className="warnings-box">
                <h4>⚠ WARNINGS — review before importing</h4>
                {result.report.missing_email.map(id => (
                  <div key={id} className="warn-item">Missing email — CustomerID {id}</div>
                ))}
                {result.report.invalid_phone.map(id => (
                  <div key={id} className="warn-item">Invalid phone — CustomerID {id}</div>
                ))}
                {result.report.duplicate_flags.map(([a, b]) => (
                  <div key={`${a}-${b}`} className="warn-item">Possible duplicate — {a} and {b}</div>
                ))}
              </div>
            )}

            <a
              href={downloadUrl()}
              download="exitroutes_migration.zip"
              className="download-btn"
            >
              ⬇ Download migration package (.zip)
            </a>
            <button className="reset-btn" onClick={reset}>← Start over</button>
          </>
        )}
      </main>

      <footer>
        <p>
          exitroutes by <a href="https://t12n.ai">t12n.ai</a> &nbsp;·&nbsp;
          Questions? <a href="mailto:steven@t12n.ai">steven@t12n.ai</a>
        </p>
      </footer>
    </div>
  )
}
