import { useSearchParams } from 'react-router-dom'
import { useState } from 'react'

const FROM_PLATFORMS = ['FieldRoutes', 'PestRoutes', 'PestPac', 'Other']
const TO_PLATFORMS = ['GorillaDesk', 'Jobber', 'Housecall Pro', 'ServiceTitan', 'Other']

export default function ThankYou() {
  const [params] = useSearchParams()
  const plan = params.get('plan')
  const isConcierge = plan === 'concierge'

  const [form, setForm] = useState({
    name: '',
    email: '',
    from_platform: 'FieldRoutes',
    to_platform: 'GorillaDesk',
    notes: '',
  })
  const [submitting, setSubmitting] = useState(false)
  const [submitted, setSubmitted] = useState(false)
  const [error, setError] = useState('')

  function handleChange(e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>) {
    setForm(f => ({ ...f, [e.target.name]: e.target.value }))
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setSubmitting(true)
    setError('')

    const apiUrl = import.meta.env.VITE_API_URL
    if (!apiUrl) {
      // No backend — open mailto fallback
      const body = encodeURIComponent(
        `Name: ${form.name}\nEmail: ${form.email}\nFrom: ${form.from_platform}\nTo: ${form.to_platform}\nNotes: ${form.notes}`
      )
      window.open(`mailto:steven@t12n.ai?subject=ExitRoutes+intake&body=${body}`)
      setSubmitted(true)
      setSubmitting(false)
      return
    }

    try {
      const res = await fetch(`${apiUrl}/intake`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ...form, plan: plan ?? 'standard' }),
      })
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      setSubmitted(true)
    } catch {
      setError('Something went wrong — please email steven@t12n.ai directly.')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="thankyou-body">
      <nav>
        <a href="/" className="logo">Exit<span>Routes</span></a>
      </nav>

      <main className="thankyou-main">
        <div className="card">
          <div className="check">✓</div>
          <h1>Payment received.<br />You're in.</h1>
          <p className="card-sub">
            {isConcierge
              ? "Concierge plan — we'll be in touch within 2 hours to schedule your onboarding call."
              : 'Check your email for confirmation.'}
          </p>

          <ol className="card-steps">
            <li>
              <div className="card-step-num">01</div>
              <div className="card-step-text">
                <strong>Fill out the intake form</strong>
                <span>5 questions about your setup — takes 3 minutes.</span>
              </div>
            </li>
            <li>
              <div className="card-step-num">02</div>
              <div className="card-step-text">
                <strong>We send upload instructions</strong>
                <span>Within 2 hours — a secure link and exact steps for pulling your FieldRoutes data.</span>
              </div>
            </li>
            <li>
              <div className="card-step-num">03</div>
              <div className="card-step-text">
                <strong>You get your migration package</strong>
                <span>Within 48 hours of sending us your files. Ready to import, no jargon.</span>
              </div>
            </li>
          </ol>

          {submitted ? (
            <div className="intake-success">
              ✓ Got it — we'll be in touch within 2 hours with your upload link.
            </div>
          ) : (
            <form className="intake-form" onSubmit={handleSubmit}>
              <h3>// intake form</h3>
              <div className="field">
                <label>YOUR NAME</label>
                <input name="name" value={form.name} onChange={handleChange} required placeholder="James Thornton" />
              </div>
              <div className="field">
                <label>YOUR EMAIL</label>
                <input name="email" type="email" value={form.email} onChange={handleChange} required placeholder="james@acmepest.com" />
              </div>
              <div className="field">
                <label>MIGRATING FROM</label>
                <select name="from_platform" value={form.from_platform} onChange={handleChange}>
                  {FROM_PLATFORMS.map(p => <option key={p}>{p}</option>)}
                </select>
              </div>
              <div className="field">
                <label>MIGRATING TO</label>
                <select name="to_platform" value={form.to_platform} onChange={handleChange}>
                  {TO_PLATFORMS.map(p => <option key={p}>{p}</option>)}
                </select>
              </div>
              <div className="field">
                <label>ANYTHING ELSE WE SHOULD KNOW? (OPTIONAL)</label>
                <textarea name="notes" value={form.notes} onChange={handleChange} placeholder="Number of customers, special data you need preserved, timing, etc." />
              </div>
              {error && <div className="error-box">{error}</div>}
              <button type="submit" className="intake-submit" disabled={submitting}>
                {submitting ? 'Sending...' : 'Submit intake form →'}
              </button>
            </form>
          )}

          <p className="card-note">
            Questions? <a href="mailto:steven@t12n.ai">steven@t12n.ai</a>
          </p>
        </div>
      </main>

      <footer>
        <p>ExitRoutes by <a href="https://t12n.ai">t12n.ai</a></p>
      </footer>
    </div>
  )
}
