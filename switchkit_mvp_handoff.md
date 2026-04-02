# SwitchKit — Complete MVP Handoff Document
# Version 1.0 | Created: 2026-04-01

---

## 1. PRODUCT SUMMARY

**What it is:** A $199 flat-rate data migration service for pest control operators leaving
FieldRoutes/PestRoutes. Takes their messy, incomplete export and delivers clean, import-ready
files for GorillaDesk, Jobber, or Housecall Pro within 48 hours.

**The pain it solves:** FieldRoutes charges $500 for an incomplete data export and makes
switching deliberately painful. Operators are publicly angry about this on Capterra, G2, and
pest control Facebook groups. SwitchKit is the exit door.

**Business model:**
- $199 one-time: CSV migration (customer receives output files to import manually)
- $349 one-time: Concierge migration (direct API pull + files + 30-min call)
- $99/mo: Ongoing backup subscription (future — not in MVP)

---

## 2. LANDING PAGE

### Design Direction
Aesthetic: Industrial utility. Think pest control + technology. Dark navy background,
safety-yellow accent, monospace accents for data-feel. NOT startup-friendly, NOT SaaS blue.
It should feel like a tool built by an operator who was burned, not a VC-backed product.

Font pairing: `Syne` (headers, heavy weight) + `IBM Plex Mono` (data/price elements) + 
`Source Serif 4` (body). Available on Google Fonts.

Color palette:
- Background: #0A0F1C (near-black navy)
- Surface: #111827 (card bg)
- Accent: #F5C842 (safety yellow)
- Text primary: #F0EDE4 (warm off-white)
- Text secondary: #8899AA (muted blue-gray)
- Border: #1E2D40 (subtle)
- Success: #2ECC71
- Danger: #E74C3C

### FULL LANDING PAGE HTML

Save as: `index.html`

```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>SwitchKit — Get Your Data Out of FieldRoutes</title>
  <meta name="description" content="Stop letting FieldRoutes hold your customer data hostage. $199 flat. Clean migration to GorillaDesk or Jobber in 48 hours." />
  <link rel="preconnect" href="https://fonts.googleapis.com" />
  <link href="https://fonts.googleapis.com/css2?family=Syne:wght@700;800&family=IBM+Plex+Mono:wght@400;500&family=Source+Serif+4:wght@400;600&display=swap" rel="stylesheet" />
  <style>
    *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
    :root {
      --bg: #0A0F1C;
      --surface: #111827;
      --surface2: #162030;
      --accent: #F5C842;
      --accent-dim: rgba(245,200,66,0.12);
      --text: #F0EDE4;
      --muted: #8899AA;
      --border: #1E2D40;
      --success: #2ECC71;
      --danger: #E74C3C;
      --font-head: 'Syne', sans-serif;
      --font-mono: 'IBM Plex Mono', monospace;
      --font-body: 'Source Serif 4', serif;
    }
    html { scroll-behavior: smooth; }
    body {
      background: var(--bg);
      color: var(--text);
      font-family: var(--font-body);
      font-size: 18px;
      line-height: 1.7;
      min-height: 100vh;
    }

    /* NAV */
    nav {
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 1.25rem 2rem;
      border-bottom: 1px solid var(--border);
      position: sticky;
      top: 0;
      background: rgba(10,15,28,0.95);
      backdrop-filter: blur(8px);
      z-index: 100;
    }
    .logo {
      font-family: var(--font-mono);
      font-weight: 500;
      font-size: 1rem;
      color: var(--accent);
      letter-spacing: 0.02em;
    }
    .logo span { color: var(--muted); }
    nav a {
      font-family: var(--font-mono);
      font-size: 0.8rem;
      color: var(--muted);
      text-decoration: none;
      letter-spacing: 0.05em;
      transition: color 0.2s;
    }
    nav a:hover { color: var(--text); }

    /* HERO */
    .hero {
      max-width: 900px;
      margin: 0 auto;
      padding: 5rem 2rem 4rem;
      text-align: center;
    }
    .eyebrow {
      font-family: var(--font-mono);
      font-size: 0.75rem;
      color: var(--accent);
      letter-spacing: 0.15em;
      text-transform: uppercase;
      margin-bottom: 1.5rem;
      display: inline-flex;
      align-items: center;
      gap: 8px;
    }
    .eyebrow::before, .eyebrow::after {
      content: '';
      display: block;
      width: 32px;
      height: 1px;
      background: var(--accent);
      opacity: 0.5;
    }
    h1 {
      font-family: var(--font-head);
      font-size: clamp(2.8rem, 7vw, 5rem);
      font-weight: 800;
      line-height: 1.05;
      letter-spacing: -0.02em;
      color: var(--text);
      margin-bottom: 1.5rem;
    }
    h1 em {
      font-style: normal;
      color: var(--accent);
    }
    .hero-sub {
      font-size: 1.2rem;
      color: var(--muted);
      max-width: 600px;
      margin: 0 auto 2.5rem;
      line-height: 1.6;
      font-family: var(--font-body);
    }
    .hero-cta {
      display: inline-flex;
      flex-direction: column;
      align-items: center;
      gap: 0.5rem;
    }
    .btn-primary {
      display: inline-block;
      background: var(--accent);
      color: #0A0F1C;
      font-family: var(--font-mono);
      font-weight: 500;
      font-size: 0.95rem;
      letter-spacing: 0.05em;
      padding: 1rem 2.5rem;
      border-radius: 4px;
      text-decoration: none;
      transition: opacity 0.15s, transform 0.15s;
    }
    .btn-primary:hover { opacity: 0.9; transform: translateY(-1px); }
    .btn-primary:active { transform: translateY(0); }
    .price-note {
      font-family: var(--font-mono);
      font-size: 0.78rem;
      color: var(--muted);
      letter-spacing: 0.04em;
    }

    /* PROOF STRIP */
    .proof-strip {
      border-top: 1px solid var(--border);
      border-bottom: 1px solid var(--border);
      background: var(--surface);
      padding: 1.25rem 2rem;
      text-align: center;
    }
    .proof-strip p {
      font-family: var(--font-mono);
      font-size: 0.78rem;
      color: var(--muted);
      letter-spacing: 0.05em;
    }
    .proof-strip strong { color: var(--text); }

    /* QUOTE SECTION */
    .quote-section {
      max-width: 860px;
      margin: 0 auto;
      padding: 5rem 2rem;
    }
    .section-head {
      font-family: var(--font-mono);
      font-size: 0.72rem;
      color: var(--accent);
      letter-spacing: 0.15em;
      text-transform: uppercase;
      margin-bottom: 2.5rem;
    }
    .quotes-grid {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 1.25rem;
    }
    @media (max-width: 640px) { .quotes-grid { grid-template-columns: 1fr; } }
    .quote-card {
      background: var(--surface);
      border: 1px solid var(--border);
      border-left: 3px solid var(--accent);
      border-radius: 0 6px 6px 0;
      padding: 1.25rem 1.5rem;
    }
    .quote-text {
      font-family: var(--font-body);
      font-size: 0.95rem;
      color: var(--text);
      line-height: 1.65;
      margin-bottom: 0.75rem;
      font-style: italic;
    }
    .quote-source {
      font-family: var(--font-mono);
      font-size: 0.72rem;
      color: var(--accent);
      letter-spacing: 0.05em;
    }

    /* HOW IT WORKS */
    .how-section {
      background: var(--surface);
      border-top: 1px solid var(--border);
      border-bottom: 1px solid var(--border);
      padding: 5rem 2rem;
    }
    .how-inner { max-width: 860px; margin: 0 auto; }
    .how-section h2 {
      font-family: var(--font-head);
      font-size: 2.2rem;
      font-weight: 800;
      margin-bottom: 3rem;
      letter-spacing: -0.02em;
    }
    .steps-list {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 2rem;
    }
    @media (max-width: 640px) { .steps-list { grid-template-columns: 1fr; } }
    .step-item { display: flex; gap: 1rem; align-items: flex-start; }
    .step-num {
      font-family: var(--font-mono);
      font-size: 0.75rem;
      color: var(--accent);
      background: var(--accent-dim);
      border: 1px solid rgba(245,200,66,0.25);
      width: 32px;
      height: 32px;
      border-radius: 4px;
      display: flex;
      align-items: center;
      justify-content: center;
      flex-shrink: 0;
      margin-top: 3px;
    }
    .step-content h3 {
      font-family: var(--font-head);
      font-size: 1.05rem;
      font-weight: 700;
      margin-bottom: 0.35rem;
    }
    .step-content p {
      font-size: 0.9rem;
      color: var(--muted);
      line-height: 1.6;
      font-family: var(--font-body);
    }

    /* WHAT YOU GET */
    .delivers-section {
      max-width: 860px;
      margin: 0 auto;
      padding: 5rem 2rem;
    }
    .delivers-section h2 {
      font-family: var(--font-head);
      font-size: 2.2rem;
      font-weight: 800;
      margin-bottom: 0.5rem;
      letter-spacing: -0.02em;
    }
    .delivers-section .sub {
      color: var(--muted);
      font-size: 1rem;
      margin-bottom: 2.5rem;
      font-family: var(--font-body);
    }
    .file-list {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 1rem;
      margin-bottom: 2rem;
    }
    @media (max-width: 640px) { .file-list { grid-template-columns: 1fr; } }
    .file-item {
      background: var(--surface);
      border: 1px solid var(--border);
      border-radius: 6px;
      padding: 1rem 1.25rem;
      display: flex;
      align-items: flex-start;
      gap: 0.75rem;
    }
    .file-icon {
      font-family: var(--font-mono);
      font-size: 0.7rem;
      color: var(--success);
      background: rgba(46,204,113,0.1);
      border: 1px solid rgba(46,204,113,0.2);
      padding: 3px 7px;
      border-radius: 3px;
      flex-shrink: 0;
      margin-top: 2px;
    }
    .file-name {
      font-family: var(--font-mono);
      font-size: 0.82rem;
      color: var(--text);
      margin-bottom: 3px;
    }
    .file-desc {
      font-size: 0.82rem;
      color: var(--muted);
      font-family: var(--font-body);
    }
    .guarantee-box {
      background: var(--accent-dim);
      border: 1px solid rgba(245,200,66,0.25);
      border-radius: 6px;
      padding: 1.25rem 1.5rem;
      display: flex;
      gap: 1rem;
      align-items: flex-start;
    }
    .guarantee-icon {
      font-size: 1.5rem;
      flex-shrink: 0;
      margin-top: 2px;
    }
    .guarantee-box h4 {
      font-family: var(--font-head);
      font-size: 1rem;
      font-weight: 700;
      color: var(--accent);
      margin-bottom: 0.25rem;
    }
    .guarantee-box p {
      font-size: 0.88rem;
      color: var(--muted);
      font-family: var(--font-body);
    }

    /* PRICING */
    .pricing-section {
      background: var(--surface);
      border-top: 1px solid var(--border);
      border-bottom: 1px solid var(--border);
      padding: 5rem 2rem;
    }
    .pricing-inner {
      max-width: 860px;
      margin: 0 auto;
    }
    .pricing-inner h2 {
      font-family: var(--font-head);
      font-size: 2.2rem;
      font-weight: 800;
      margin-bottom: 2.5rem;
      letter-spacing: -0.02em;
    }
    .plans-grid {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 1.25rem;
    }
    @media (max-width: 640px) { .plans-grid { grid-template-columns: 1fr; } }
    .plan-card {
      background: var(--bg);
      border: 1px solid var(--border);
      border-radius: 8px;
      padding: 1.75rem;
    }
    .plan-card.featured {
      border-color: var(--accent);
      position: relative;
    }
    .plan-badge {
      position: absolute;
      top: -12px;
      left: 1.5rem;
      background: var(--accent);
      color: #0A0F1C;
      font-family: var(--font-mono);
      font-size: 0.7rem;
      font-weight: 500;
      letter-spacing: 0.08em;
      padding: 3px 10px;
      border-radius: 3px;
    }
    .plan-name {
      font-family: var(--font-mono);
      font-size: 0.8rem;
      color: var(--muted);
      letter-spacing: 0.08em;
      text-transform: uppercase;
      margin-bottom: 0.75rem;
    }
    .plan-price {
      font-family: var(--font-mono);
      font-size: 2.5rem;
      font-weight: 500;
      color: var(--text);
      line-height: 1;
      margin-bottom: 0.25rem;
    }
    .plan-period {
      font-family: var(--font-mono);
      font-size: 0.75rem;
      color: var(--muted);
      margin-bottom: 1.5rem;
    }
    .plan-features {
      list-style: none;
      margin-bottom: 1.75rem;
    }
    .plan-features li {
      font-size: 0.9rem;
      color: var(--text);
      padding: 0.4rem 0;
      border-bottom: 1px solid var(--border);
      font-family: var(--font-body);
      display: flex;
      gap: 0.5rem;
      align-items: baseline;
    }
    .plan-features li:last-child { border-bottom: none; }
    .plan-features li::before {
      content: '→';
      color: var(--accent);
      font-family: var(--font-mono);
      font-size: 0.75rem;
      flex-shrink: 0;
    }
    .btn-plan {
      display: block;
      text-align: center;
      padding: 0.85rem;
      border-radius: 4px;
      font-family: var(--font-mono);
      font-size: 0.85rem;
      font-weight: 500;
      letter-spacing: 0.04em;
      text-decoration: none;
      transition: all 0.15s;
    }
    .btn-plan-primary {
      background: var(--accent);
      color: #0A0F1C;
    }
    .btn-plan-primary:hover { opacity: 0.9; }
    .btn-plan-secondary {
      background: transparent;
      color: var(--text);
      border: 1px solid var(--border);
    }
    .btn-plan-secondary:hover { border-color: var(--muted); }

    /* FAQ */
    .faq-section {
      max-width: 700px;
      margin: 0 auto;
      padding: 5rem 2rem;
    }
    .faq-section h2 {
      font-family: var(--font-head);
      font-size: 2rem;
      font-weight: 800;
      margin-bottom: 2rem;
      letter-spacing: -0.02em;
    }
    .faq-item {
      border-bottom: 1px solid var(--border);
      padding: 1.25rem 0;
    }
    .faq-q {
      font-family: var(--font-head);
      font-size: 1rem;
      font-weight: 700;
      margin-bottom: 0.5rem;
    }
    .faq-a {
      font-size: 0.92rem;
      color: var(--muted);
      font-family: var(--font-body);
      line-height: 1.65;
    }
    .faq-a a { color: var(--accent); text-decoration: none; }
    .faq-a a:hover { text-decoration: underline; }

    /* FINAL CTA */
    .final-cta {
      background: var(--surface);
      border-top: 1px solid var(--border);
      padding: 5rem 2rem;
      text-align: center;
    }
    .final-cta h2 {
      font-family: var(--font-head);
      font-size: clamp(2rem, 5vw, 3.5rem);
      font-weight: 800;
      letter-spacing: -0.02em;
      max-width: 640px;
      margin: 0 auto 1rem;
      line-height: 1.1;
    }
    .final-cta h2 em { font-style: normal; color: var(--accent); }
    .final-cta p {
      color: var(--muted);
      margin-bottom: 2rem;
      font-size: 1rem;
    }

    /* FOOTER */
    footer {
      padding: 2rem;
      text-align: center;
      border-top: 1px solid var(--border);
    }
    footer p {
      font-family: var(--font-mono);
      font-size: 0.75rem;
      color: var(--muted);
      letter-spacing: 0.04em;
    }
    footer a { color: var(--muted); text-decoration: none; }
    footer a:hover { color: var(--text); }

    /* ANIMATIONS */
    @keyframes fadeUp {
      from { opacity: 0; transform: translateY(20px); }
      to { opacity: 1; transform: translateY(0); }
    }
    .hero > * {
      animation: fadeUp 0.6s ease forwards;
      opacity: 0;
    }
    .hero > *:nth-child(1) { animation-delay: 0.1s; }
    .hero > *:nth-child(2) { animation-delay: 0.2s; }
    .hero > *:nth-child(3) { animation-delay: 0.3s; }
    .hero > *:nth-child(4) { animation-delay: 0.4s; }
  </style>
</head>
<body>

<!-- NAV -->
<nav>
  <div class="logo">Switch<span>Kit</span></div>
  <a href="#pricing">Get started →</a>
</nav>

<!-- HERO -->
<section class="hero">
  <div class="eyebrow">For pest control operators</div>
  <h1>Your data is yours.<br>Take it <em>back.</em></h1>
  <p class="hero-sub">
    FieldRoutes is charging $500 for an incomplete export and making it nearly impossible to leave.
    SwitchKit gets you out — customer list, service history, recurring schedules — 
    clean and ready to import in 48 hours.
  </p>
  <div class="hero-cta">
    <a href="#pricing" class="btn-primary">Get your data migrated — $199</a>
    <span class="price-note">flat fee · no subscription · 48-hour turnaround</span>
  </div>
</section>

<!-- PROOF STRIP -->
<div class="proof-strip">
  <p>
    Works with <strong>GorillaDesk</strong> · <strong>Jobber</strong> · <strong>Housecall Pro</strong>
    &nbsp;·&nbsp; Migrates from <strong>FieldRoutes</strong> · <strong>PestRoutes</strong> · <strong>PestPac</strong>
  </p>
</div>

<!-- QUOTES -->
<section class="quote-section">
  <p class="section-head">// what operators are saying about FieldRoutes</p>
  <div class="quotes-grid">
    <div class="quote-card">
      <p class="quote-text">"PestRoutes has made it impossible to leave by holding our data hostage. We've been trying for almost a year to switch."</p>
      <p class="quote-source">— Capterra review, Environmental Services</p>
    </div>
    <div class="quote-card">
      <p class="quote-text">"I still can't believe they want $500 to give us an INCOMPLETE data backup. It's only 6 fields of data."</p>
      <p class="quote-source">— Capterra review, Pest Control Operator</p>
    </div>
    <div class="quote-card">
      <p class="quote-text">"We've been trying for a year to switch software. FieldRoutes made it impossible. I had to forfeit the rest of my subscription."</p>
      <p class="quote-source">— SoftwareAdvice review, Lawn & Pest</p>
    </div>
    <div class="quote-card">
      <p class="quote-text">"No support when needed. Not two or three days later. No one ever answers the phone."</p>
      <p class="quote-source">— Capterra review, November 2024</p>
    </div>
  </div>
</section>

<!-- HOW IT WORKS -->
<section class="how-section">
  <div class="how-inner">
    <p class="section-head">// how it works</p>
    <h2>Four steps. 48 hours.<br>You're out.</h2>
    <div class="steps-list">
      <div class="step-item">
        <div class="step-num">01</div>
        <div class="step-content">
          <h3>Pay & fill out the intake form</h3>
          <p>$199 via Stripe. Then answer 5 quick questions about your current setup, your destination platform, and what data matters most.</p>
        </div>
      </div>
      <div class="step-item">
        <div class="step-num">02</div>
        <div class="step-content">
          <h3>Send us your data export</h3>
          <p>We'll email you exact instructions for pulling your FieldRoutes data — including the reports most operators don't know about. You upload the files to a secure link.</p>
        </div>
      </div>
      <div class="step-item">
        <div class="step-num">03</div>
        <div class="step-content">
          <h3>We clean and map everything</h3>
          <p>Our tool parses your data, deduplicates records, normalizes phone numbers and addresses, and maps every field to your destination platform's format.</p>
        </div>
      </div>
      <div class="step-item">
        <div class="step-num">04</div>
        <div class="step-content">
          <h3>You get a clean migration package</h3>
          <p>Three ready-to-import CSV files plus a plain-English import guide. Follow the steps and your new software has everything from day one.</p>
        </div>
      </div>
    </div>
  </div>
</section>

<!-- WHAT YOU GET -->
<section class="delivers-section">
  <p class="section-head">// what's in the migration package</p>
  <h2>Everything, actually.</h2>
  <p class="sub">Not the 6 fields FieldRoutes gives you. The full picture.</p>
  <div class="file-list">
    <div class="file-item">
      <span class="file-icon">CSV</span>
      <div>
        <div class="file-name">customers.csv</div>
        <div class="file-desc">Full customer list — names, addresses, phones, emails, account numbers, billing vs service address</div>
      </div>
    </div>
    <div class="file-item">
      <span class="file-icon">CSV</span>
      <div>
        <div class="file-name">subscriptions.csv</div>
        <div class="file-desc">Active recurring plans — service type, frequency, price, next due date, autopay status</div>
      </div>
    </div>
    <div class="file-item">
      <span class="file-icon">CSV</span>
      <div>
        <div class="file-name">service_history.csv</div>
        <div class="file-desc">Last 24 months of completed jobs — dates, technician, chemicals used, notes, results</div>
      </div>
    </div>
    <div class="file-item">
      <span class="file-icon">CSV</span>
      <div>
        <div class="file-name">open_invoices.csv</div>
        <div class="file-desc">Outstanding balances by customer — amount, age, linked service records</div>
      </div>
    </div>
    <div class="file-item">
      <span class="file-icon">PDF</span>
      <div>
        <div class="file-name">import_guide.pdf</div>
        <div class="file-desc">Step-by-step instructions for importing each file into your destination platform. Plain English, no jargon.</div>
      </div>
    </div>
    <div class="file-item">
      <span class="file-icon">TXT</span>
      <div>
        <div class="file-name">migration_report.txt</div>
        <div class="file-desc">Record counts, any flagged issues (missing emails, duplicate addresses), and what to watch for during import</div>
      </div>
    </div>
  </div>
  <div class="guarantee-box">
    <div class="guarantee-icon">⚡</div>
    <div>
      <h4>48-hour turnaround, guaranteed</h4>
      <p>You'll have your migration package within 48 hours of sending us your data files. If we miss that window for any reason, you get a full refund — no questions asked.</p>
    </div>
  </div>
</section>

<!-- PRICING -->
<section class="pricing-section" id="pricing">
  <div class="pricing-inner">
    <p class="section-head">// pricing</p>
    <h2>One flat fee.<br>No surprises.</h2>
    <div class="plans-grid">

      <div class="plan-card featured">
        <div class="plan-badge">MOST POPULAR</div>
        <div class="plan-name">Standard Migration</div>
        <div class="plan-price">$199</div>
        <div class="plan-period">one-time · no subscription</div>
        <ul class="plan-features">
          <li>Full customer list extraction</li>
          <li>Active subscription mapping</li>
          <li>24-month service history</li>
          <li>Open invoices export</li>
          <li>GorillaDesk, Jobber, or Housecall Pro output</li>
          <li>Plain-English import guide</li>
          <li>Migration validation report</li>
          <li>48-hour turnaround guaranteed</li>
        </ul>
        <!-- REPLACE WITH YOUR STRIPE PAYMENT LINK -->
        <a href="https://buy.stripe.com/REPLACE_WITH_STANDARD_LINK" class="btn-plan btn-plan-primary">
          Get started — $199 →
        </a>
      </div>

      <div class="plan-card">
        <div class="plan-name">Concierge Migration</div>
        <div class="plan-price">$349</div>
        <div class="plan-period">one-time · includes support call</div>
        <ul class="plan-features">
          <li>Everything in Standard</li>
          <li>API-direct data pull (we handle extraction)</li>
          <li>Chemical log PDF archive (state compliance)</li>
          <li>Technician & route mapping</li>
          <li>30-min onboarding call post-delivery</li>
          <li>We answer any import questions for 7 days</li>
          <li>Priority 24-hour turnaround</li>
          <li>PestPac also supported</li>
        </ul>
        <!-- REPLACE WITH YOUR STRIPE PAYMENT LINK -->
        <a href="https://buy.stripe.com/REPLACE_WITH_CONCIERGE_LINK" class="btn-plan btn-plan-secondary">
          Get Concierge — $349 →
        </a>
      </div>

    </div>
  </div>
</section>

<!-- FAQ -->
<section class="faq-section">
  <p class="section-head">// questions</p>
  <h2>Things operators ask.</h2>

  <div class="faq-item">
    <div class="faq-q">Will FieldRoutes block you from getting my data?</div>
    <div class="faq-a">No. We work entirely with data you already have legitimate access to — the exports FieldRoutes provides, plus the built-in report exports most operators don't know about. If you're still an active customer, you also have API access, which we can use with your permission. We don't do anything outside the bounds of your existing contract.</div>
  </div>

  <div class="faq-item">
    <div class="faq-q">What if my FieldRoutes export is incomplete?</div>
    <div class="faq-a">It will be — that's the whole problem. We'll email you instructions for pulling every available report from within FieldRoutes, including sections most operators never export. What we can't get, we flag clearly in the migration report so you know what to re-enter manually.</div>
  </div>

  <div class="faq-item">
    <div class="faq-q">How do you keep my customer data secure?</div>
    <div class="faq-a">Your files are uploaded to an encrypted, temporary link. We process your data and delete the source files within 72 hours of delivering your migration package. We don't store customer data long-term and we never share it with anyone.</div>
  </div>

  <div class="faq-item">
    <div class="faq-q">What if the migration doesn't work?</div>
    <div class="faq-a">We'll fix it. If any of the output files don't import cleanly into your destination platform, email us and we'll troubleshoot until it works. If we can't get it working within 5 business days, full refund.</div>
  </div>

  <div class="faq-item">
    <div class="faq-q">Do you support platforms other than GorillaDesk and Jobber?</div>
    <div class="faq-a">Currently: GorillaDesk, Jobber, and Housecall Pro. PestPac and ServiceTitan are available on the Concierge plan. If your destination platform isn't listed, email us before purchasing — we may still be able to help.</div>
  </div>

  <div class="faq-item">
    <div class="faq-q">Can you help migrate from PestPac too?</div>
    <div class="faq-a">Yes — on the Concierge plan. PestPac's export format is different but more complete than FieldRoutes. We support it for operators migrating from either platform.</div>
  </div>
</section>

<!-- FINAL CTA -->
<section class="final-cta">
  <h2>Stop letting them<br><em>hold you hostage.</em></h2>
  <p>$199 flat. 48 hours. Your data, in your hands.</p>
  <a href="#pricing" class="btn-primary">Get started →</a>
</section>

<!-- FOOTER -->
<footer>
  <p>
    SwitchKit by <a href="https://t12n.ai">t12n.ai</a> &nbsp;·&nbsp;
    <a href="mailto:steven@t12n.ai">steven@t12n.ai</a> &nbsp;·&nbsp;
    Questions? <a href="mailto:steven@t12n.ai">Email us before purchasing</a>
  </p>
</footer>

</body>
</html>
```

---

## 3. STRIPE SETUP INSTRUCTIONS

### Step 1: Create two Payment Links in your Stripe dashboard

**Product 1: SwitchKit Standard**
- Name: `SwitchKit Standard Migration`
- Price: `$199.00 USD`
- Payment type: One-time
- Success URL: `https://switchkit.io/thank-you?plan=standard`
- After-purchase: Redirect to Typeform intake form (see Section 4)

**Product 2: SwitchKit Concierge**
- Name: `SwitchKit Concierge Migration`
- Price: `$349.00 USD`
- Payment type: One-time
- Success URL: `https://switchkit.io/thank-you?plan=concierge`
- After-purchase: Redirect to Typeform intake form

### Step 2: Replace placeholder links in the HTML

Find these lines in index.html and replace with your actual Stripe URLs:
```
https://buy.stripe.com/REPLACE_WITH_STANDARD_LINK
https://buy.stripe.com/REPLACE_WITH_CONCIERGE_LINK
```

### Step 3: Set up Stripe webhook (optional for MVP)

For MVP, just check Stripe dashboard manually.
When ready to automate: webhook event `checkout.session.completed`
→ sends confirmation email with Typeform link.

### Step 4: Confirmation email text (send manually for first 10 customers)

Subject: Your SwitchKit order — next steps

---
Hi [Name],

Payment received — you're in.

Here's what happens next:

1. Fill out this short intake form so we know exactly what you need:
   [TYPEFORM LINK]

2. We'll reply within 2 hours with a secure upload link for your FieldRoutes export files,
   plus instructions for pulling everything you need.

3. Within 48 hours of receiving your files, you'll have your complete migration package.

Any questions, just reply to this email.

— Steven
steven@t12n.ai | SwitchKit
---

---

## 4. TYPEFORM INTAKE FORM SPEC

### Form title: SwitchKit — Migration Intake

Create at: typeform.com (free plan supports this)
Set to auto-send to: steven@t12n.ai on every submission

### Questions (in order):

**Q1 — Welcome screen**
Headline: "Let's get your data back."
Description: "5 quick questions — takes about 3 minutes. We'll be in touch within 2 hours."

**Q2 — Short text**
Question: "What's your company name?"
Required: Yes

**Q3 — Short text**
Question: "What's the best email to reach you?"
Format: Email
Required: Yes

**Q4 — Short text**
Question: "What's a good phone number? (Optional — for the Concierge plan call)"
Required: No

**Q5 — Multiple choice**
Question: "Which software are you migrating FROM?"
Options:
- FieldRoutes (formerly PestRoutes)
- PestPac (WorkWave)
- ServiceTitan
- Other

**Q6 — Multiple choice**
Question: "Which software are you migrating TO?"
Options:
- GorillaDesk
- Jobber
- Housecall Pro
- Other (I'll tell you in the notes)

**Q7 — Multiple choice (allow multiple)**
Question: "Which data is most important to you? (Select all that apply)"
Options:
- Customer list (names, addresses, contacts)
- Active service subscriptions / recurring plans
- Service history (past jobs, chemicals used)
- Open invoices and outstanding balances
- Technician assignments and routes
- Chemical logs (EPA/state compliance records)
- Customer notes and access instructions

**Q8 — Long text**
Question: "Anything else we should know? Any unusual data situations, multi-location setups, or things that have already gone wrong with the export?"
Required: No
Placeholder: "e.g. We have 3 service locations. FieldRoutes already told us our backup is incomplete. We have lawn care and pest control services on the same accounts."

**Q9 — Thank you screen**
Headline: "Got it. We'll be in touch within 2 hours."
Description: "Check your email for your secure file upload link and export instructions. If you don't see it, check spam or email steven@t12n.ai directly."

---

## 5. CLAUDE CODE BUILD PROMPT

Copy and paste this prompt to start a new Claude Code session in your repo.
The session should begin with the repo already initialized (git init, README.md present).

---

```
You are helping me build SwitchKit — a $199 data migration tool for pest control operators 
leaving FieldRoutes/PestRoutes. The business context is in the handoff doc (see below).

The repo should be structured as follows:

switchkit/
├── index.html              # Landing page (already written — see handoff doc)
├── app/
│   ├── main.py             # Streamlit UI for the migration tool
│   ├── parser.py           # FieldRoutes CSV parsing logic
│   ├── mapper.py           # Field mapping engine (FR → GorillaDesk/Jobber/HCP)
│   ├── cleaner.py          # Data cleaning and validation
│   ├── packager.py         # Output ZIP generation
│   └── config/
│       ├── gorilladesk.json    # Field mapping: FR → GorillaDesk
│       ├── jobber.json         # Field mapping: FR → Jobber
│       └── housecallpro.json   # Field mapping: FR → Housecall Pro
├── sample_data/
│   ├── fr_customers_sample.csv        # Sample FieldRoutes customer export
│   ├── fr_subscriptions_sample.csv    # Sample subscriptions export
│   └── fr_service_history_sample.csv  # Sample service history
├── requirements.txt
└── README.md

---

## What to build first (in order):

### 1. Sample data files (start here)

Create realistic sample CSV files that mimic what FieldRoutes actually exports.
Base them on these known FieldRoutes export fields:

customers export fields:
CustomerID, FirstName, LastName, CompanyName, BillingAddress1, BillingAddress2, 
BillingCity, BillingState, BillingZip, ServiceAddress1, ServiceAddress2, ServiceCity, 
ServiceState, ServiceZip, Phone1, Phone2, Email, Balance, Notes, IsActive, CreatedDate

subscriptions export fields:
SubscriptionID, CustomerID, ServiceType, Frequency, Price, NextServiceDate, 
TechnicianID, Status, AutoPay, ContractStartDate, ContractEndDate

service_history export fields:
AppointmentID, CustomerID, SubscriptionID, ServiceDate, TechnicianID, Status, 
ChemicalsUsed, AmountApplied, Notes, InvoiceAmount, AmountPaid

Create 25 realistic sample customers with messy data: 
- Some missing emails
- Phone numbers in various formats (555-1234, (555) 123-4567, 5551234567)
- Some customers with service address = billing address, some different
- A few duplicate records
- Mix of active and inactive subscriptions
- Service history going back 24 months

---

### 2. parser.py

A Python class `FieldRoutesParser` that:
- Accepts a dict of {filename: file_path} for the uploaded CSVs
- Detects which export type each file is (customers / subscriptions / service_history)
  based on column headers
- Reads each file with pandas, handling:
  - BOM characters (some FR exports have UTF-8-BOM)
  - Mixed encodings (try UTF-8, fall back to latin-1)
  - Extra whitespace in headers and values
  - Empty rows
- Returns a dict of {table_name: DataFrame}
- Logs a warning for any unexpected columns or missing required columns

---

### 3. cleaner.py

A class `DataCleaner` that takes the parsed DataFrames and:

**Phone normalization:**
- Accept any common US format
- Output: (555) 555-5555 standard format
- Flag invalid/missing phone numbers

**Address standardization:**
- Strip extra whitespace
- Title-case street names
- Validate that city/state/zip are all present; flag if not

**Email validation:**
- Basic regex check
- Flag missing emails (critical — many platforms need email for import)

**Deduplication:**
- Identify duplicate CustomerIDs
- Identify potential duplicates by (FirstName + LastName + ServiceAddress) or (Email)
- Flag but don't auto-delete — report them for human review

**Service address vs billing address:**
- If ServiceAddress fields are empty, copy from BillingAddress fields
- Add a flag column: `address_is_same` (True/False)

**Active filtering:**
- Separate active vs inactive customers
- Include both in output but label clearly

Returns cleaned DataFrames + a validation report dict:
{
  "total_customers": int,
  "active_customers": int,
  "missing_email": [list of CustomerIDs],
  "invalid_phone": [list of CustomerIDs],
  "duplicate_flags": [list of CustomerID pairs],
  "missing_address_fields": [list of CustomerIDs]
}

---

### 4. config/gorilladesk.json

A field mapping configuration for the GorillaDesk import format.
GorillaDesk customer import expects these columns:
first_name, last_name, company, email, phone, mobile, 
billing_address, billing_city, billing_state, billing_zip,
service_address, service_city, service_state, service_zip,
notes, balance

Map from FieldRoutes customer fields to GorillaDesk fields.
Fields that don't map directly should have a "transform" key 
explaining what processing is needed.

Also create gorilladesk subscription mapping for their recurring service import format.

---

### 5. mapper.py

A class `FieldMapper` that:
- Loads a mapping config JSON for the selected destination
- Applies column renaming from FR field names → destination field names
- Applies any transform rules defined in the config
- Returns DataFrames ready for export with destination-native column names
- Drops any columns that have no mapping (log them as "unmapped")

---

### 6. packager.py

A class `MigrationPackager` that:
- Takes the mapped DataFrames + validation report
- Generates a ZIP file containing:
  - customers.csv (destination-formatted)
  - subscriptions.csv (destination-formatted)
  - service_history.csv (destination-formatted)
  - open_invoices.csv (balance > 0 subset of customers)
  - migration_report.txt (human-readable summary of what was migrated 
    and what was flagged)
  - README.txt (import instructions for the destination platform, 
    one section per file)
- Returns the path to the ZIP file

The migration_report.txt should look like:

```
SWITCHKIT MIGRATION REPORT
Generated: [datetime]
Destination: GorillaDesk

SUMMARY
-------
Total customers processed: 247
Active customers: 231
Inactive customers: 16
Subscriptions migrated: 189
Service records migrated: 1,843
Open invoices: 23 (total balance: $4,210.00)

WARNINGS (review before importing)
-----------------------------------
Missing email address (12 customers):
  - #1042 Johnson Exterminators — no email on file
  - #1187 Garcia Residence — no email on file
  [...]

Potential duplicates flagged (2 pairs):
  - #1023 and #1089 may be the same customer (same address, different name spellings)
  - #0445 and #1332 may be the same customer (same email address)

Invalid phone numbers (3 customers):
  - #0221 Smith Property Mgmt — phone "555-PEST" could not be formatted
  [...]

UNMAPPED FIELDS (not included in output)
-----------------------------------------
FieldRoutes field "CustomField1" has no GorillaDesk equivalent
FieldRoutes field "SalesRepID" has no GorillaDesk equivalent

NEXT STEPS
----------
1. Import customers.csv first using GorillaDesk Settings → Import → Customers
2. Then import subscriptions.csv
3. Then service_history.csv
4. Review the 12 customers with missing emails and add manually
5. Review the 2 potential duplicate pairs and merge if needed
```

---

### 7. app/main.py — Streamlit UI

A clean, functional Streamlit app with:

**Page 1: Upload**
- Title: "SwitchKit — FieldRoutes Migration"
- Subtitle: "Upload your FieldRoutes export files to get started"
- File uploader (accepts multiple CSVs): "Upload your FieldRoutes export files"
- Dropdown: "I'm migrating to:" [GorillaDesk, Jobber, Housecall Pro]
- Button: "Process migration"

**Page 2: Processing**
- Progress bar showing steps:
  1. Parsing files...
  2. Cleaning data...
  3. Validating records...
  4. Generating output...
- Show completion checkmarks as each step finishes

**Page 3: Results**
- Summary metrics in cards:
  - Customers migrated
  - Subscriptions
  - Service records
  - Warnings found
- Expandable "Warnings" section showing the validation issues
- Large button: "Download migration package (.zip)"
- Small text: "Questions? Email steven@t12n.ai"

**Styling:**
- Dark theme: st.set_page_config(layout="wide")
- Use st.markdown with custom CSS to match the landing page feel:
  - Dark background #0A0F1C
  - Accent color #F5C842
  - IBM Plex Mono for code/numbers
- Keep it clean and functional — this is a tool, not a marketing page

---

### 8. requirements.txt

pandas>=2.0
streamlit>=1.30
openpyxl>=3.1    # for Excel exports if needed
python-dotenv>=1.0

---

### 9. README.md

Write a complete developer README with:
- Project overview (1 paragraph)
- Local setup instructions
- How to run locally: `streamlit run app/main.py`
- How to deploy to Streamlit Cloud (free, takes 5 min)
- File structure explanation
- How to add a new destination platform (add a config JSON + register in mapper.py)
- Known limitations of FieldRoutes exports
- Environment variables needed (none for MVP, placeholder for future Stripe webhook)

---

## Priority order:
1. sample_data/ files first — everything else tests against these
2. parser.py + cleaner.py — core processing logic
3. config/gorilladesk.json + mapper.py — first destination
4. packager.py — output generation
5. app/main.py — UI (can use sample data to build and test this)
6. config/jobber.json + config/housecallpro.json — additional destinations
7. README.md last

## Testing approach:
After each module, test with the sample data files.
The final integration test: run the Streamlit app, upload all three sample CSVs,
select GorillaDesk, process, download the ZIP, and verify the contents look correct.

## What NOT to build in this session:
- Authentication / user accounts
- Stripe webhook integration
- Email sending
- Database / persistent storage
- FieldRoutes API connector (Phase 3 — future session)

Any questions about the business context or data structures, ask before coding.
```

---

## 6. QUICK-START CHECKLIST

Week 1 — before writing code:
- [ ] Register switchkit.io (or .co)
- [ ] Deploy index.html to Vercel (drag-and-drop, free)
- [ ] Create Stripe account + two Payment Links
- [ ] Create Typeform intake form
- [ ] Update Stripe links in index.html and redeploy
- [ ] Run Claude Code session with the prompt above
- [ ] Send first 10 outreach emails using scripts from outreach guide

Week 2 — after first paying customers:
- [ ] Deploy Streamlit app to Streamlit Cloud
- [ ] Do first migrations manually using sample data as a template
- [ ] Use real customer data to test and fix the parser
- [ ] Add GorillaDesk field mapping based on what you learn from real data

---

## 7. DOMAIN + HOSTING

**Domain:** switchkit.io (~$12/yr on Namecheap or Google Domains)
**Landing page:** Vercel (free, deploy by dropping index.html into a repo)
**Streamlit app:** Streamlit Cloud (free for one public app)
**File uploads:** WeTransfer or Filestack free tier for MVP (operator emails files)
**Email:** Use your existing steven@t12n.ai

Total monthly cost at MVP stage: $0 (domain is annual)

---

END OF HANDOFF DOCUMENT
