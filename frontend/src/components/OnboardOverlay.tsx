import { useEffect, useState } from 'react'

interface Props {
  onComplete: () => void
}

const BUSINESS_TYPES = [
  'Manufacturer',
  'Trader/Distributor',
  'Retailer',
  'Service Provider',
  'Contractor',
  'Freelancer',
]

const GST_RATES = ['0%', '5%', '12%', '18%', '28%']

// ── Reusable input styles ──────────────────────────────────────────────────────
const inputCls =
  'w-full px-4 py-3 rounded-xl border border-slate-200 focus:outline-none focus:ring-2 focus:ring-orange-500 focus:border-transparent bg-white text-slate-900 placeholder-slate-400 text-sm'

const inputClsLg =
  'w-full px-4 py-4 rounded-xl border border-slate-200 focus:outline-none focus:ring-2 focus:ring-orange-500 focus:border-transparent bg-white text-slate-900 placeholder-slate-400 text-base'

// ── Progress dots ──────────────────────────────────────────────────────────────
function StepDots({ step, total }: { step: number; total: number }) {
  return (
    <div className="flex items-center gap-2">
      {Array.from({ length: total }, (_, i) => {
        const n = i + 1
        const done = n < step
        const active = n === step
        return (
          <div
            key={n}
            className={`rounded-full transition-all duration-300
              ${active ? 'w-6 h-2.5 bg-orange-500' : done ? 'w-2.5 h-2.5 bg-orange-300' : 'w-2.5 h-2.5 bg-slate-200'}
            `}
          />
        )
      })}
    </div>
  )
}

// ── Primary CTA button ─────────────────────────────────────────────────────────
function PrimaryBtn({ onClick, loading, children }: { onClick: () => void; loading?: boolean; children: React.ReactNode }) {
  return (
    <button
      onClick={onClick}
      disabled={loading}
      className="w-full py-3.5 rounded-xl bg-gradient-to-r from-orange-500 to-orange-600 text-white font-semibold text-sm shadow-lg shadow-orange-200 hover:shadow-orange-300 transition-all active:scale-[0.98] disabled:opacity-70"
    >
      {loading ? (
        <span className="flex items-center justify-center gap-2">
          <svg className="animate-spin w-4 h-4" viewBox="0 0 24 24" fill="none">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="white" strokeWidth="4" />
            <path className="opacity-75" fill="white" d="M4 12a8 8 0 018-8v4a4 4 0 00-4 4H4z" />
          </svg>
          Saving…
        </span>
      ) : children}
    </button>
  )
}

// ── Chip selector ──────────────────────────────────────────────────────────────
function Chips({ options, value, onChange, cols }: { options: string[]; value: string; onChange: (v: string) => void; cols: 2 | 3 }) {
  return (
    <div className={`grid gap-2 ${cols === 3 ? 'grid-cols-3' : 'grid-cols-2'}`}>
      {options.map(opt => (
        <button
          key={opt}
          type="button"
          onClick={() => onChange(opt)}
          className={`px-3 py-2 rounded-xl border text-sm font-medium cursor-pointer transition-all text-center
            ${value === opt
              ? 'bg-orange-50 border-orange-500 text-orange-600'
              : 'border-slate-200 text-slate-600 hover:border-orange-300 bg-white'
            }`}
        >
          {opt}
        </button>
      ))}
    </div>
  )
}

// ── Check circle SVG ───────────────────────────────────────────────────────────
function CheckCircle() {
  return (
    <div className="flex items-center justify-center">
      <div className="w-20 h-20 rounded-full bg-orange-50 border-4 border-orange-200 flex items-center justify-center">
        <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="#f97316" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
          <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14" />
          <polyline points="22 4 12 14.01 9 11.01" />
        </svg>
      </div>
    </div>
  )
}

// ── What's unlocked list ───────────────────────────────────────────────────────
const UNLOCKED = [
  '🧾 Invoice & quotation creation',
  '📊 GST reports & tax summaries',
  '💬 WhatsApp AI agent',
  '👥 Customer tracking & history',
]

// ── Main component ─────────────────────────────────────────────────────────────
export default function OnboardOverlay({ onComplete }: Props) {
  const [step, setStep] = useState<1 | 2 | 3>(1)
  const [businessName, setBusinessName] = useState('')
  const [businessType, setBusinessType] = useState('')
  const [phone, setPhone] = useState('')
  const [catalogItem, setCatalogItem] = useState({ name: '', price: '', gst: '18%' })
  const [saving, setSaving] = useState(false)
  const [isMobile, setIsMobile] = useState(window.innerWidth < 768)

  useEffect(() => {
    const onResize = () => setIsMobile(window.innerWidth < 768)
    window.addEventListener('resize', onResize)
    return () => window.removeEventListener('resize', onResize)
  }, [])

  // ── Step advancement ───────────────────────────────────────────────────────
  function advance() {
    if (step === 1) setStep(2)
    else if (step === 2) {
      setSaving(true)
      setTimeout(() => {
        setSaving(false)
        setStep(3)
      }, 700)
    } else {
      // Step 3 → complete
      localStorage.setItem('m1m_biz_name', businessName || 'Your Business')
      onComplete()
    }
  }

  const stepLabels = ['Your Business', 'First Catalog Item', "You're all set!"]
  const currentLabel = stepLabels[step - 1]

  // ── Step content ───────────────────────────────────────────────────────────
  function renderStepContent(large: boolean) {
    const inpCls = large ? inputClsLg : inputCls

    if (step === 1) {
      return (
        <div className="space-y-4">
          <div>
            <label className="block text-xs font-semibold text-slate-500 uppercase tracking-wide mb-1.5">
              Business name *
            </label>
            <input
              className={inpCls}
              placeholder="e.g. Sharma Traders"
              value={businessName}
              onChange={e => setBusinessName(e.target.value)}
              autoFocus
            />
          </div>
          <div>
            <label className="block text-xs font-semibold text-slate-500 uppercase tracking-wide mb-1.5">
              Business type
            </label>
            <Chips
              options={BUSINESS_TYPES}
              value={businessType}
              onChange={setBusinessType}
              cols={large ? 2 : 3}
            />
          </div>
          <div>
            <label className="block text-xs font-semibold text-slate-500 uppercase tracking-wide mb-1.5">
              Phone number
            </label>
            <input
              className={inpCls}
              placeholder="+91 98765 43210"
              value={phone}
              onChange={e => setPhone(e.target.value)}
              type="tel"
            />
          </div>
        </div>
      )
    }

    if (step === 2) {
      return (
        <div className="space-y-4">
          <div>
            <label className="block text-xs font-semibold text-slate-500 uppercase tracking-wide mb-1.5">
              Product / Service name
            </label>
            <input
              className={inpCls}
              placeholder="e.g. Web Design Package"
              value={catalogItem.name}
              onChange={e => setCatalogItem(c => ({ ...c, name: e.target.value }))}
              autoFocus
            />
          </div>
          <div className="flex gap-3">
            <div className="flex-1">
              <label className="block text-xs font-semibold text-slate-500 uppercase tracking-wide mb-1.5">
                Price (₹)
              </label>
              <div className="relative">
                <span className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400 font-medium">₹</span>
                <input
                  className={`${inpCls} pl-8`}
                  placeholder="5000"
                  value={catalogItem.price}
                  onChange={e => setCatalogItem(c => ({ ...c, price: e.target.value }))}
                  type="number"
                />
              </div>
            </div>
            <div className="w-28">
              <label className="block text-xs font-semibold text-slate-500 uppercase tracking-wide mb-1.5">
                GST rate
              </label>
              <select
                className={inpCls}
                value={catalogItem.gst}
                onChange={e => setCatalogItem(c => ({ ...c, gst: e.target.value }))}
              >
                {GST_RATES.map(r => <option key={r} value={r}>{r}</option>)}
              </select>
            </div>
          </div>
          <p className="text-xs text-slate-400">You can add more items later from the app.</p>
        </div>
      )
    }

    // Step 3
    return (
      <div className="space-y-5 text-center">
        <CheckCircle />
        <div>
          <h3 className="text-xl font-bold text-slate-900">
            You're all set, <span className="text-orange-500">{businessName || 'there'}</span>!
          </h3>
          <p className="text-slate-500 text-sm mt-1">Here's what you've unlocked:</p>
        </div>
        <ul className="text-left space-y-2 bg-orange-50 rounded-xl p-4">
          {UNLOCKED.map(item => (
            <li key={item} className="text-sm text-slate-700 flex items-center gap-2">
              {item}
            </li>
          ))}
        </ul>
      </div>
    )
  }

  // ── Mobile layout ──────────────────────────────────────────────────────────
  if (isMobile) {
    const progressPct = ((step - 1) / 2) * 100

    return (
      <div className="fixed inset-0 z-50 bg-white flex flex-col">
        {/* Header */}
        <div className="bg-gradient-to-r from-orange-500 to-orange-600 px-5 pt-12 pb-5 flex-shrink-0">
          <div className="flex items-center gap-2 mb-4">
            <div className="w-8 h-8 rounded-full bg-white/20 flex items-center justify-center">
              <span className="text-white font-extrabold text-sm">M</span>
            </div>
            <span className="text-white font-bold text-base">Munim.ai</span>
          </div>
          <p className="text-white/70 text-xs font-medium uppercase tracking-wider mb-1">
            Step {step} of 3
          </p>
          <h2 className="text-white font-bold text-xl mb-4">{currentLabel}</h2>
          {/* Progress bar */}
          <div className="h-1.5 rounded-full bg-white/30 overflow-hidden">
            <div
              className="h-full bg-white rounded-full transition-all duration-500"
              style={{ width: step === 3 ? '100%' : `${progressPct + 33}%` }}
            />
          </div>
        </div>

        {/* Scrollable content */}
        <div className="flex-1 overflow-auto px-5 pt-6 pb-32">
          {renderStepContent(false)}
        </div>

        {/* Fixed bottom CTA */}
        <div className="fixed bottom-0 left-0 right-0 bg-white border-t border-slate-100 px-5 py-4">
          <PrimaryBtn onClick={advance} loading={saving}>
            {step === 3 ? 'Open Munim.ai →' : step === 2 ? 'Next →' : 'Continue →'}
          </PrimaryBtn>
          <button
            onClick={() => { localStorage.setItem('m1m_biz_name', businessName || 'Your Business'); onComplete() }}
            className="w-full text-center text-xs text-slate-400 mt-2 py-1"
          >
            Skip setup
          </button>
        </div>
      </div>
    )
  }

  // ── Desktop layout ─────────────────────────────────────────────────────────
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm">
      <div className="bg-white rounded-3xl shadow-2xl w-full max-w-xl mx-4 overflow-hidden">
        {/* Orange gradient header */}
        <div className="bg-gradient-to-r from-orange-500 to-orange-600 px-8 py-6">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2.5">
              <div className="w-9 h-9 rounded-full bg-white/20 flex items-center justify-center">
                <span className="text-white font-extrabold text-base">M</span>
              </div>
              <span className="text-white font-bold text-lg">Set up Munim.ai</span>
            </div>
            <span className="text-white/80 text-sm font-medium">{step} of 3</span>
          </div>
          {/* Step progress dots */}
          <div className="flex items-center gap-2 mt-4">
            <StepDots step={step} total={3} />
            <span className="text-white/70 text-xs ml-1">{currentLabel}</span>
          </div>
        </div>

        {/* Form area */}
        <div className="px-8 py-6 space-y-5">
          {renderStepContent(false)}

          <PrimaryBtn onClick={advance} loading={saving}>
            {step === 3 ? 'Open Munim.ai →' : step === 2 ? 'Save & Continue →' : 'Continue →'}
          </PrimaryBtn>

          <div className="text-center">
            <button
              onClick={() => { localStorage.setItem('m1m_biz_name', businessName || 'Your Business'); onComplete() }}
              className="text-xs text-slate-400 hover:text-slate-600 transition-colors"
            >
              Skip setup
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
