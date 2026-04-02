export default function Landing() {
  return (
    <>
      <nav>
        <a href="/" className="logo">Exit<span>Routes</span></a>
        <a href="#pricing">Get started →</a>
      </nav>

      <section className="hero">
        <div className="eyebrow">For pest control operators</div>
        <h1>Your data is yours.<br />Take it <em>back.</em></h1>
        <p className="hero-sub">
          FieldRoutes is charging $500 for an incomplete export and making it nearly impossible to leave.
          ExitRoutes gets you out — customer list, service history, recurring schedules —
          clean and ready to import in 48 hours.
        </p>
        <div className="hero-cta">
          <a href="#pricing" className="btn-primary">Get your data migrated — $199</a>
          <span className="price-note">flat fee · no subscription · 48-hour turnaround</span>
        </div>
      </section>

      <div className="proof-strip">
        <p>
          Works with <strong>GorillaDesk</strong> · <strong>Jobber</strong> · <strong>Housecall Pro</strong>
          &nbsp;·&nbsp; Migrates from <strong>FieldRoutes</strong> · <strong>PestRoutes</strong> · <strong>PestPac</strong>
        </p>
      </div>

      <section className="quote-section">
        <p className="section-head">// what operators are saying about FieldRoutes</p>
        <div className="quotes-grid">
          <div className="quote-card">
            <p className="quote-text">"PestRoutes has made it impossible to leave by holding our data hostage. We've been trying for almost a year to switch."</p>
            <p className="quote-source">— Capterra review, Environmental Services</p>
          </div>
          <div className="quote-card">
            <p className="quote-text">"I still can't believe they want $500 to give us an INCOMPLETE data backup. It's only 6 fields of data."</p>
            <p className="quote-source">— Capterra review, Pest Control Operator</p>
          </div>
          <div className="quote-card">
            <p className="quote-text">"We've been trying for a year to switch software. FieldRoutes made it impossible. I had to forfeit the rest of my subscription."</p>
            <p className="quote-source">— SoftwareAdvice review, Lawn &amp; Pest</p>
          </div>
          <div className="quote-card">
            <p className="quote-text">"No support when needed. Not two or three days later. No one ever answers the phone."</p>
            <p className="quote-source">— Capterra review, November 2024</p>
          </div>
        </div>
      </section>

      <section className="how-section">
        <div className="how-inner">
          <p className="section-head">// how it works</p>
          <h2>Four steps. 48 hours.<br />You're out.</h2>
          <div className="steps-list">
            <div className="step-item">
              <div className="step-num">01</div>
              <div className="step-content">
                <h3>Pay &amp; fill out the intake form</h3>
                <p>$199 via Stripe. Then answer 5 quick questions about your current setup, your destination platform, and what data matters most.</p>
              </div>
            </div>
            <div className="step-item">
              <div className="step-num">02</div>
              <div className="step-content">
                <h3>Send us your data export</h3>
                <p>We'll email you exact instructions for pulling your FieldRoutes data — including the reports most operators don't know about. You upload the files to a secure link.</p>
              </div>
            </div>
            <div className="step-item">
              <div className="step-num">03</div>
              <div className="step-content">
                <h3>We clean and map everything</h3>
                <p>Our tool parses your data, deduplicates records, normalizes phone numbers and addresses, and maps every field to your destination platform's format.</p>
              </div>
            </div>
            <div className="step-item">
              <div className="step-num">04</div>
              <div className="step-content">
                <h3>You get a clean migration package</h3>
                <p>Three ready-to-import CSV files plus a plain-English import guide. Follow the steps and your new software has everything from day one.</p>
              </div>
            </div>
          </div>
        </div>
      </section>

      <section className="delivers-section">
        <p className="section-head">// what's in the migration package</p>
        <h2>Everything, actually.</h2>
        <p className="sub">Not the 6 fields FieldRoutes gives you. The full picture.</p>
        <div className="file-list">
          <div className="file-item">
            <span className="file-icon">CSV</span>
            <div>
              <div className="file-name">customers.csv</div>
              <div className="file-desc">Full customer list — names, addresses, phones, emails, account numbers, billing vs service address</div>
            </div>
          </div>
          <div className="file-item">
            <span className="file-icon">CSV</span>
            <div>
              <div className="file-name">subscriptions.csv</div>
              <div className="file-desc">Active recurring plans — service type, frequency, price, next due date, autopay status</div>
            </div>
          </div>
          <div className="file-item">
            <span className="file-icon">CSV</span>
            <div>
              <div className="file-name">service_history.csv</div>
              <div className="file-desc">Last 24 months of completed jobs — dates, technician, chemicals used, notes, results</div>
            </div>
          </div>
          <div className="file-item">
            <span className="file-icon">CSV</span>
            <div>
              <div className="file-name">open_invoices.csv</div>
              <div className="file-desc">Outstanding balances by customer — amount, age, linked service records</div>
            </div>
          </div>
          <div className="file-item">
            <span className="file-icon">PDF</span>
            <div>
              <div className="file-name">import_guide.pdf</div>
              <div className="file-desc">Step-by-step instructions for importing each file into your destination platform. Plain English, no jargon.</div>
            </div>
          </div>
          <div className="file-item">
            <span className="file-icon">TXT</span>
            <div>
              <div className="file-name">migration_report.txt</div>
              <div className="file-desc">Record counts, any flagged issues (missing emails, duplicate addresses), and what to watch for during import</div>
            </div>
          </div>
        </div>
        <div className="guarantee-box">
          <div className="guarantee-icon">⚡</div>
          <div>
            <h4>48-hour turnaround, guaranteed</h4>
            <p>You'll have your migration package within 48 hours of sending us your data files. If we miss that window for any reason, you get a full refund — no questions asked.</p>
          </div>
        </div>
      </section>

      <section className="pricing-section" id="pricing">
        <div className="pricing-inner">
          <p className="section-head">// pricing</p>
          <h2>One flat fee.<br />No surprises.</h2>
          <div className="plans-grid">
            <div className="plan-card featured">
              <div className="plan-badge">MOST POPULAR</div>
              <div className="plan-name">Standard Migration</div>
              <div className="plan-price">$199</div>
              <div className="plan-period">one-time · no subscription</div>
              <ul className="plan-features">
                <li>Full customer list extraction</li>
                <li>Active subscription mapping</li>
                <li>24-month service history</li>
                <li>Open invoices export</li>
                <li>GorillaDesk, Jobber, or Housecall Pro output</li>
                <li>Plain-English import guide</li>
                <li>Migration validation report</li>
                <li>48-hour turnaround guaranteed</li>
              </ul>
              <a href="https://buy.stripe.com/test_cNicN63ee9TjeZn5n9eAg00" className="btn-plan btn-plan-primary">
                Get started — $199 →
              </a>
            </div>
            <div className="plan-card">
              <div className="plan-name">Concierge Migration</div>
              <div className="plan-price">$349</div>
              <div className="plan-period">one-time · includes support call</div>
              <ul className="plan-features">
                <li>Everything in Standard</li>
                <li>API-direct data pull (we handle extraction)</li>
                <li>Chemical log PDF archive (state compliance)</li>
                <li>Technician &amp; route mapping</li>
                <li>30-min onboarding call post-delivery</li>
                <li>We answer any import questions for 7 days</li>
                <li>Priority 24-hour turnaround</li>
                <li>PestPac also supported</li>
              </ul>
              <a href="https://buy.stripe.com/test_8x2dRadSSaXncRf7vheAg01" className="btn-plan btn-plan-secondary">
                Get Concierge — $349 →
              </a>
            </div>
          </div>
        </div>
      </section>

      <section className="faq-section">
        <p className="section-head">// questions</p>
        <h2>Things operators ask.</h2>
        <div className="faq-item">
          <div className="faq-q">Will FieldRoutes block you from getting my data?</div>
          <div className="faq-a">No. We work entirely with data you already have legitimate access to — the exports FieldRoutes provides, plus the built-in report exports most operators don't know about. If you're still an active customer, you also have API access, which we can use with your permission.</div>
        </div>
        <div className="faq-item">
          <div className="faq-q">What if my FieldRoutes export is incomplete?</div>
          <div className="faq-a">It will be — that's the whole problem. We'll email you instructions for pulling every available report from within FieldRoutes, including sections most operators never export. What we can't get, we flag clearly in the migration report so you know what to re-enter manually.</div>
        </div>
        <div className="faq-item">
          <div className="faq-q">How do you keep my customer data secure?</div>
          <div className="faq-a">Your files are uploaded to an encrypted, temporary link. We process your data and delete the source files within 72 hours of delivering your migration package. We don't store customer data long-term and we never share it with anyone.</div>
        </div>
        <div className="faq-item">
          <div className="faq-q">What if the migration doesn't work?</div>
          <div className="faq-a">We'll fix it. If any of the output files don't import cleanly into your destination platform, email us and we'll troubleshoot until it works. If we can't get it working within 5 business days, full refund.</div>
        </div>
        <div className="faq-item">
          <div className="faq-q">Do you support platforms other than GorillaDesk and Jobber?</div>
          <div className="faq-a">Currently: GorillaDesk, Jobber, and Housecall Pro. PestPac and ServiceTitan are available on the Concierge plan. If your destination platform isn't listed, email us before purchasing — we may still be able to help.</div>
        </div>
        <div className="faq-item">
          <div className="faq-q">Can you help migrate from PestPac too?</div>
          <div className="faq-a">Yes — on the Concierge plan. PestPac's export format is different but more complete than FieldRoutes. We support it for operators migrating from either platform.</div>
        </div>
      </section>

      <section className="final-cta">
        <h2>Stop letting them<br /><em>hold you hostage.</em></h2>
        <p>$199 flat. 48 hours. Your data, in your hands.</p>
        <a href="#pricing" className="btn-primary">Get started →</a>
      </section>

      <footer>
        <p>
          ExitRoutes by <a href="https://t12n.ai">t12n.ai</a> &nbsp;·&nbsp;
          <a href="mailto:steven@t12n.ai">steven@t12n.ai</a> &nbsp;·&nbsp;
          Questions? <a href="mailto:steven@t12n.ai">Email us before purchasing</a>
        </p>
      </footer>
    </>
  )
}
