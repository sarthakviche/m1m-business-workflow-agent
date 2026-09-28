import { useState, useEffect, useRef } from 'react'






interface BusinessProfile {

  businessName: string

  gstin: string

  state: string

  address: string

  businessType: string

  phone: string

  email: string

}



interface CatalogItem {

  id: string

  name: string

  unit: string

  price: string

  gstRate: string

  hsn: string

  stock: string

}






const INDIAN_STATES = [

  'Andhra Pradesh','Arunachal Pradesh','Assam','Bihar','Chhattisgarh',

  'Goa','Gujarat','Haryana','Himachal Pradesh','Jharkhand','Karnataka',

  'Kerala','Madhya Pradesh','Maharashtra','Manipur','Meghalaya','Mizoram',

  'Nagaland','Odisha','Punjab','Rajasthan','Sikkim','Tamil Nadu','Telangana',

  'Tripura','Uttar Pradesh','Uttarakhand','West Bengal',

  'Delhi','Jammu & Kashmir','Ladakh',

]



const BUSINESS_TYPES = [

  { value: 'manufacturer', label: 'Manufacturer', icon: '🏭' },

  { value: 'trader',       label: 'Trader / Distributor', icon: '📦' },

  { value: 'retailer',     label: 'Retailer', icon: '🏪' },

  { value: 'services',     label: 'Service Provider', icon: '🛠️' },

  { value: 'contractor',   label: 'Contractor', icon: '🏗️' },

  { value: 'freelancer',   label: 'Freelancer', icon: '💼' },

]



const GST_RATES = ['0','5','12','18','28']



const UNITS = ['pcs','kg','mtr','ltr','box','bundle','set','dozen','ton','sqft']



const FEATURE_BULLETS = [

  { icon: '💬', text: 'Create invoices & quotations via natural language chat' },

  { icon: '🧾', text: 'GST-compliant PDFs with CGST / SGST / IGST auto-split' },

  { icon: '📦', text: 'Real-time inventory tracking on every sale' },

  { icon: '📊', text: 'Live dashboard with sales, dues & stock alerts' },

]






const STEPS = [

  { id: 1, label: 'Business' },

  { id: 2, label: 'Catalog' },

  { id: 3, label: 'Review' },

]






function uid() {

  return Math.random().toString(36).slice(2, 10)

}






function InputField({

  label, name, value, onChange, placeholder = '', type = 'text', optional = false,

  hint, error,

}: {

  label: string; name: string; value: string; onChange: (v: string) => void;

  placeholder?: string; type?: string; optional?: boolean; hint?: string; error?: string;

}) {

  return (

    <div className="flex flex-col gap-1.5">

      <label className="text-sm font-medium text-slate-600 flex items-center gap-1.5" htmlFor={name}>

        {label}

        {optional && <span className="text-xs font-normal text-white/30">Optional</span>}

      </label>

      <input

        id={name}

        type={type}

        value={value}

        onChange={e => onChange(e.target.value)}

        placeholder={placeholder}

        className={`

          w-full rounded-xl px-4 py-3 text-sm font-sans text-white placeholder-white/25

          bg-white/50 backdrop-blur-3xl border transition-all duration-200 outline-none

          ${error

            ? 'border-red-400/60 focus:border-red-400 focus:ring-1 focus:ring-red-400/30'

            : 'border-white border-slate-200/60 shadow-xl focus:border-brand-400 focus:ring-1 focus:ring-brand-400/25 focus:bg-white/8'

          }

        `}

        style={{ fontFamily: "'Inter', sans-serif" }}

      />

      {hint && !error && <p className="text-xs text-white/35">{hint}</p>}

      {error && <p className="text-xs text-red-400">{error}</p>}

    </div>

  )

}



function SelectField({

  label, name, value, onChange, options, optional = false,

}: {

  label: string; name: string; value: string; onChange: (v: string) => void;

  options: { value: string; label: string }[]; optional?: boolean;

}) {

  return (

    <div className="flex flex-col gap-1.5">

      <label className="text-sm font-medium text-slate-600 flex items-center gap-1.5" htmlFor={name}>

        {label}

        {optional && <span className="text-xs font-normal text-white/30">Optional</span>}

      </label>

      <select

        id={name}

        value={value}

        onChange={e => onChange(e.target.value)}

        className="

          w-full rounded-xl px-4 py-3 text-sm font-sans text-white

          bg-white/50 backdrop-blur-3xl border border-white border-slate-200/60 shadow-xl transition-all duration-200 outline-none

          focus:border-brand-400 focus:ring-1 focus:ring-brand-400/25 focus:bg-white/8

          appearance-none cursor-pointer

        "

        style={{

          fontFamily: "'Inter', sans-serif",

          backgroundImage: `url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='12' viewBox='0 0 24 24' fill='none' stroke='rgba(255,255,255,0.4)' stroke-width='2'%3E%3Cpath d='M6 9l6 6 6-6'/%3E%3C/svg%3E")`,

          backgroundRepeat: 'no-repeat',

          backgroundPosition: 'calc(100% - 14px) 50%',

          paddingRight: '40px',

        }}

      >

        <option value="" disabled style={{ background: '#0c4f38' }}>Select {label}</option>

        {options.map(o => (

          <option key={o.value} value={o.value} style={{ background: '#0c4f38' }}>{o.label}</option>

        ))}

      </select>

    </div>

  )

}






function StepBusiness({

  profile, onChange, onNext,

}: {

  profile: BusinessProfile

  onChange: (f: keyof BusinessProfile, v: string) => void

  onNext: () => void

}) {

  const [errors, setErrors] = useState<Partial<BusinessProfile>>({})



  const validate = () => {

    const e: Partial<BusinessProfile> = {}

    if (!profile.businessName.trim())   e.businessName = 'Business name is required'

    if (!profile.state)                 e.state = 'Please select a state'

    if (!profile.businessType)          e.businessType = 'Please select a business type'

    if (profile.gstin && !/^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}$/.test(profile.gstin))

      e.gstin = 'Invalid GSTIN format (e.g. 22AAAAA0000A1Z5)'

    setErrors(e)

    return Object.keys(e).length === 0

  }



  const handleNext = () => { if (validate()) onNext() }



  return (

    <div className="animate-fade-up">

      <div className="mb-8">

        <h2 className="font-display text-2xl font-bold text-white tracking-tight mb-1">

          Tell us about your business

        </h2>

        <p className="text-sm text-white/50 font-sans">

          This info appears on your quotations and invoices.

        </p>

      </div>



      {/* Business type selector */}

      <div className="mb-6">

        <p className="text-sm font-medium text-slate-600 mb-3">Business type</p>

        <div className="grid grid-cols-3 gap-2">

          {BUSINESS_TYPES.map(bt => (

            <button

              key={bt.value}

              type="button"

              onClick={() => onChange('businessType', bt.value)}

              className={`

                flex flex-col items-center gap-1.5 rounded-xl py-3 px-2 text-xs font-medium

                border transition-all duration-200 cursor-pointer

                ${profile.businessType === bt.value

                  ? 'bg-brand-500/20 border-brand-400 text-brand-600'

                  : 'bg-white/60 backdrop-blur-3xl border-white border-slate-200/60 shadow-xl text-white/50 hover:bg-white/7 hover:border-white/15 hover:text-white/75'

                }

              `}

            >

              <span className="text-xl">{bt.icon}</span>

              <span className="leading-tight text-center">{bt.label}</span>

            </button>

          ))}

        </div>

        {errors.businessType && (

          <p className="text-xs text-red-400 mt-1.5">{errors.businessType}</p>

        )}

      </div>



      <div className="grid grid-cols-1 gap-4">

        <InputField

          label="Business Name"

          name="businessName"

          value={profile.businessName}

          onChange={v => onChange('businessName', v)}

          placeholder="e.g. Sharma Steel & Hardware"

          error={errors.businessName}

        />



        <div className="grid grid-cols-2 gap-4">

          <InputField

            label="GST Number (GSTIN)"

            name="gstin"

            value={profile.gstin}

            onChange={v => onChange('gstin', v.toUpperCase())}

            placeholder="22AAAAA0000A1Z5"

            optional

            hint="Required for tax invoices"

            error={errors.gstin}

          />

          <SelectField

            label="State"

            name="state"

            value={profile.state}

            onChange={v => onChange('state', v)}

            options={INDIAN_STATES.map(s => ({ value: s, label: s }))}

          />

        </div>



        <InputField

          label="Business Address"

          name="address"

          value={profile.address}

          onChange={v => onChange('address', v)}

          placeholder="Shop no., street, city, PIN"

          optional

        />



        <div className="grid grid-cols-2 gap-4">

          <InputField

            label="Phone"

            name="phone"

            value={profile.phone}

            onChange={v => onChange('phone', v)}

            placeholder="+91 98765 43210"

            optional

          />

          <InputField

            label="Email"

            name="email"

            type="email"

            value={profile.email}

            onChange={v => onChange('email', v)}

            placeholder="you@business.com"

            optional

          />

        </div>

      </div>



      <button

        onClick={handleNext}

        className="

          mt-8 w-full py-3.5 rounded-xl font-display font-semibold text-sm text-white

          bg-brand-gradient shadow-glow

          hover:opacity-90 active:scale-[0.98]

          transition-all duration-200 flex items-center justify-center gap-2

        "

      >

        Continue to Catalog

        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5"><path d="M5 12h14M12 5l7 7-7 7"/></svg>

      </button>

    </div>

  )

}






function StepCatalog({

  items, onAdd, onRemove, onUpdate, onNext, onBack,

}: {

  items: CatalogItem[]

  onAdd: () => void

  onRemove: (id: string) => void

  onUpdate: (id: string, field: keyof CatalogItem, value: string) => void

  onNext: () => void

  onBack: () => void

}) {

  return (

    <div className="animate-fade-up">

      <div className="mb-6">

        <h2 className="font-display text-2xl font-bold text-white tracking-tight mb-1">

          Add your products or services

        </h2>

        <p className="text-sm text-white/50">

          You can always add more later from the Inventory page.

        </p>

      </div>



      {/* Item list */}

      <div className="flex flex-col gap-3 mb-4 max-h-[340px] overflow-y-auto pr-1 custom-scrollbar">

        {items.length === 0 && (

          <div className="flex flex-col items-center gap-3 py-10 rounded-2xl border border-dashed border-white border-slate-200/60 shadow-xl text-white/30">

            <span className="text-4xl">📦</span>

            <p className="text-sm">No items yet — add your first product below</p>

          </div>

        )}



        {items.map((item, idx) => (

          <div

            key={item.id}

            className="rounded-2xl border border-white border-slate-200/60 shadow-xl bg-white/3 p-4 flex flex-col gap-3 animate-fade-up"

            style={{ animationDelay: `${idx * 60}ms` }}

          >

            <div className="flex items-center justify-between">

              <span className="text-xs font-semibold text-brand-400 uppercase tracking-wide">

                Item {idx + 1}

              </span>

              <button

                onClick={() => onRemove(item.id)}

                className="w-6 h-6 rounded-lg bg-red-500/10 text-red-400 hover:bg-red-500/20 flex items-center justify-center text-xs transition-colors duration-150"

              >

                ×

              </button>

            </div>



            <div className="grid grid-cols-2 gap-3">

              <div className="col-span-2">

                <input

                  value={item.name}

                  onChange={e => onUpdate(item.id, 'name', e.target.value)}

                  placeholder="Product / service name"

                  className="w-full rounded-lg px-3 py-2.5 text-sm text-white placeholder-white/25 bg-white/50 backdrop-blur-3xl border border-white border-slate-200/60 shadow-xl focus:border-brand-400 focus:ring-1 focus:ring-brand-400/25 outline-none transition-all"

                  style={{ fontFamily: "'Inter', sans-serif" }}

                />

              </div>



              <input

                value={item.hsn}

                onChange={e => onUpdate(item.id, 'hsn', e.target.value)}

                placeholder="HSN Code (e.g. 7214)"

                className="w-full rounded-lg px-3 py-2.5 text-sm text-white placeholder-white/25 bg-white/50 backdrop-blur-3xl border border-white border-slate-200/60 shadow-xl focus:border-brand-400 focus:ring-1 focus:ring-brand-400/25 outline-none transition-all"

                style={{ fontFamily: "'Inter', sans-serif" }}

              />



              <div className="flex gap-2">

                <select

                  value={item.gstRate}

                  onChange={e => onUpdate(item.id, 'gstRate', e.target.value)}

                  className="flex-1 rounded-lg px-2 py-2.5 text-sm text-white bg-white/50 backdrop-blur-3xl border border-white border-slate-200/60 shadow-xl focus:border-brand-400 outline-none transition-all appearance-none cursor-pointer"

                  style={{ fontFamily: "'Inter', sans-serif", background: 'rgba(255,255,255,0.05)' }}

                >

                  {GST_RATES.map(r => <option key={r} value={r} style={{ background: '#0c4f38' }}>{r}% GST</option>)}

                </select>

              </div>



              <div className="relative">

                <span className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400 text-sm">₹</span>

                <input

                  value={item.price}

                  onChange={e => onUpdate(item.id, 'price', e.target.value)}

                  placeholder="Unit price"

                  type="number"

                  className="w-full rounded-lg pl-7 pr-3 py-2.5 text-sm text-white placeholder-white/25 bg-white/50 backdrop-blur-3xl border border-white border-slate-200/60 shadow-xl focus:border-brand-400 focus:ring-1 focus:ring-brand-400/25 outline-none transition-all"

                  style={{ fontFamily: "'Inter', sans-serif" }}

                />

              </div>



              <div className="flex gap-2">

                <select

                  value={item.unit}

                  onChange={e => onUpdate(item.id, 'unit', e.target.value)}

                  className="flex-1 rounded-lg px-2 py-2.5 text-sm text-white bg-white/50 backdrop-blur-3xl border border-white border-slate-200/60 shadow-xl focus:border-brand-400 outline-none transition-all appearance-none cursor-pointer"

                  style={{ fontFamily: "'Inter', sans-serif", background: 'rgba(255,255,255,0.05)' }}

                >

                  {UNITS.map(u => <option key={u} value={u} style={{ background: '#0c4f38' }}>{u}</option>)}

                </select>

                <div className="relative flex-1">

                  <input

                    value={item.stock}

                    onChange={e => onUpdate(item.id, 'stock', e.target.value)}

                    placeholder="Opening stock"

                    type="number"

                    className="w-full rounded-lg px-3 py-2.5 text-sm text-white placeholder-white/25 bg-white/50 backdrop-blur-3xl border border-white border-slate-200/60 shadow-xl focus:border-brand-400 focus:ring-1 focus:ring-brand-400/25 outline-none transition-all"

                    style={{ fontFamily: "'Inter', sans-serif" }}

                  />

                </div>

              </div>

            </div>

          </div>

        ))}

      </div>



      {/* Add item button */}

      <button

        onClick={onAdd}

        className="

          w-full py-3 rounded-xl border border-dashed border-brand-500/40 text-brand-400

          text-sm font-medium flex items-center justify-center gap-2

          hover:bg-brand-500/8 hover:border-brand-400/60 transition-all duration-200

        "

      >

        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5"><path d="M12 5v14M5 12h14"/></svg>

        Add another item

      </button>



      <div className="mt-6 flex gap-3">

        <button

          onClick={onBack}

          className="

            flex-[0.4] py-3.5 rounded-xl font-semibold text-sm text-slate-500

            bg-white/50 backdrop-blur-3xl border border-white border-slate-200/60 shadow-xl hover:bg-white/8 hover:text-slate-700

            transition-all duration-200

          "

        >

          Back

        </button>

        <button

          onClick={onNext}

          className="

            flex-1 py-3.5 rounded-xl font-display font-semibold text-sm text-white

            bg-brand-gradient shadow-glow

            hover:opacity-90 active:scale-[0.98]

            transition-all duration-200 flex items-center justify-center gap-2

          "

        >

          {items.length === 0 ? 'Skip for now' : 'Review & Finish'}

          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5"><path d="M5 12h14M12 5l7 7-7 7"/></svg>

        </button>

      </div>

    </div>

  )

}






function StepReview({

  profile, items, onSubmit, onBack, isSubmitting,

}: {

  profile: BusinessProfile

  items: CatalogItem[]

  onSubmit: () => void

  onBack: () => void

  isSubmitting: boolean

}) {

  return (

    <div className="animate-fade-up">

      <div className="mb-6">

        <h2 className="font-display text-2xl font-bold text-white tracking-tight mb-1">

          Looks great! Ready to launch?

        </h2>

        <p className="text-sm text-white/50">

          Review your setup and click Launch to get started.

        </p>

      </div>



      {/* Business summary card */}

      <div className="rounded-2xl bg-white/60 backdrop-blur-3xl border border-white border-slate-200/60 shadow-xl p-5 mb-4">

        <div className="flex items-start gap-3 mb-4">

          <div className="w-10 h-10 rounded-xl bg-brand-gradient flex items-center justify-center text-white font-display font-bold text-lg shadow-glow flex-shrink-0">

            {profile.businessName.charAt(0).toUpperCase() || 'B'}

          </div>

          <div>

            <p className="font-display font-semibold text-white text-base">{profile.businessName || 'Your Business'}</p>

            <p className="text-xs text-slate-400">{BUSINESS_TYPES.find(b => b.value === profile.businessType)?.label || 'Business'} · {profile.state}</p>

          </div>

        </div>



        <div className="grid grid-cols-2 gap-x-6 gap-y-2.5 text-xs">

          {profile.gstin && (

            <div className="flex justify-between col-span-2">

              <span className="text-slate-400">GSTIN</span>

              <span className="text-slate-700 font-mono">{profile.gstin}</span>

            </div>

          )}

          {profile.address && (

            <div className="flex justify-between col-span-2">

              <span className="text-slate-400">Address</span>

              <span className="text-slate-700 text-right max-w-[200px]">{profile.address}</span>

            </div>

          )}

          {profile.phone && (

            <div className="flex justify-between">

              <span className="text-slate-400">Phone</span>

              <span className="text-slate-700">{profile.phone}</span>

            </div>

          )}

          {profile.email && (

            <div className="flex justify-between">

              <span className="text-slate-400">Email</span>

              <span className="text-slate-700">{profile.email}</span>

            </div>

          )}

        </div>

      </div>



      {/* Catalog summary */}

      {items.length > 0 && (

        <div className="rounded-2xl bg-white/60 backdrop-blur-3xl border border-white border-slate-200/60 shadow-xl p-5 mb-4">

          <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-3">

            Catalog — {items.length} item{items.length !== 1 ? 's' : ''}

          </p>

          <div className="flex flex-col gap-2">

            {items.slice(0, 4).map(item => (

              <div key={item.id} className="flex items-center justify-between">

                <div className="flex items-center gap-2">

                  <div className="w-1.5 h-1.5 rounded-full bg-brand-400 flex-shrink-0" />

                  <span className="text-sm text-slate-700">{item.name || 'Unnamed item'}</span>

                </div>

                <span className="text-xs text-slate-400">₹{item.price || '—'} / {item.unit}</span>

              </div>

            ))}

            {items.length > 4 && (

              <p className="text-xs text-white/30 pl-3.5">+{items.length - 4} more items</p>

            )}

          </div>

        </div>

      )}



      {/* What's next */}

      <div className="rounded-2xl bg-brand-900/50 border border-brand-700/30 p-5 mb-6">

        <p className="text-xs font-semibold text-brand-400 uppercase tracking-wider mb-3">What's unlocked</p>

        <div className="flex flex-col gap-2.5">

          {FEATURE_BULLETS.map(f => (

            <div key={f.text} className="flex items-start gap-2.5">

              <span className="text-base leading-tight">{f.icon}</span>

              <span className="text-xs text-slate-500 leading-relaxed">{f.text}</span>

            </div>

          ))}

        </div>

      </div>



      <div className="flex gap-3">

        <button

          onClick={onBack}

          disabled={isSubmitting}

          className="

            flex-[0.4] py-3.5 rounded-xl font-semibold text-sm text-slate-500

            bg-white/50 backdrop-blur-3xl border border-white border-slate-200/60 shadow-xl hover:bg-white/8 hover:text-slate-700

            transition-all duration-200 disabled:opacity-40

          "

        >

          Back

        </button>

        <button

          onClick={onSubmit}

          disabled={isSubmitting}

          className="

            flex-1 py-3.5 rounded-xl font-display font-semibold text-sm text-white

            bg-brand-gradient shadow-glow

            hover:opacity-90 active:scale-[0.98]

            transition-all duration-200 flex items-center justify-center gap-2

            disabled:opacity-60 disabled:cursor-not-allowed

          "

        >

          {isSubmitting ? (

            <>

              <svg className="animate-spin" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5"><path d="M12 2v4M12 18v4M4.93 4.93l2.83 2.83M16.24 16.24l2.83 2.83M2 12h4M18 12h4M4.93 19.07l2.83-2.83M16.24 7.76l2.83-2.83"/></svg>

              Setting up…

            </>

          ) : (

            <>

              🚀 Launch Munim.ai

            </>

          )}

        </button>

      </div>

    </div>

  )

}






function HeroPanel({ step }: { step: number }) {

  const messages = [

    {

      headline: 'Your smart business copilot',

      body: 'Just chat — Munim.ai handles quotations, invoices, stock, and dues for you.',

    },

    {

      headline: 'Your catalog, powered by AI',

      body: 'Once your products are set up, just say "Create a quotation for 5 TMT rods" and the rest is automatic.',

    },

    {

      headline: 'Ready to launch',

      body: 'Munim.ai will remember everything. Focus on selling — we handle the paperwork.',

    },

  ]

  const m = messages[step - 1] ?? messages[0]



  return (

    <div className="hidden lg:flex flex-col justify-between h-full p-10 relative overflow-hidden">

      {/* Decorative blobs */}

      <div className="absolute -top-20 -right-20 w-80 h-80 rounded-full bg-brand-400/15 blur-3xl pointer-events-none animate-pulse-slow" />

      <div className="absolute bottom-0 -left-10 w-60 h-60 rounded-full bg-brand-600/20 blur-3xl pointer-events-none animate-float" />



      {/* Logo */}

      <div className="relative z-10">

        <div className="flex items-center gap-3">

          <div className="w-10 h-10 rounded-2xl bg-brand-gradient flex items-center justify-center shadow-glow">

            <svg width="22" height="22" viewBox="0 0 24 24" fill="none">

              <path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5" stroke="white" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"/>

            </svg>

          </div>

          <div>

            <p className="font-display font-bold text-white text-lg tracking-tight">Munim.ai</p>

            <p className="text-xs text-brand-600/70">by M1M</p>

          </div>

        </div>

      </div>



      {/* Feature card */}

      <div className="relative z-10 flex flex-col gap-6 animate-fade-up" key={step}>

        <div className="w-14 h-14 rounded-2xl bg-white/8 border border-white border-slate-200/60 shadow-xl flex items-center justify-center text-3xl shadow-soft">

          {step === 1 ? '🏢' : step === 2 ? '📦' : '🚀'}

        </div>

        <div>

          <h3 className="font-display font-bold text-white text-2xl leading-snug mb-2">

            {m.headline}

          </h3>

          <p className="text-sm text-white/50 leading-relaxed">

            {m.body}

          </p>

        </div>



        <div className="flex flex-col gap-3">

          {FEATURE_BULLETS.map((f, i) => (

            <div

              key={f.text}

              className="flex items-start gap-3 animate-fade-up"

              style={{ animationDelay: `${i * 80}ms` }}

            >

              <div className="w-7 h-7 rounded-lg bg-white/6 border border-white border-slate-200/60 shadow-xl flex items-center justify-center text-sm flex-shrink-0">

                {f.icon}

              </div>

              <p className="text-sm text-white/55 leading-relaxed">{f.text}</p>

            </div>

          ))}

        </div>

      </div>



      {/* Social proof */}

      <div className="relative z-10">

        <div className="flex items-center gap-3 rounded-2xl bg-white/50 backdrop-blur-3xl border border-white border-slate-200/60 shadow-xl p-4">

          <div className="flex -space-x-2">

            {['🧑🏽‍💼','👩🏻‍💼','👨🏾‍💼'].map((e, i) => (

              <div key={i} className="w-8 h-8 rounded-full bg-brand-gradient border-2 border-brand-200 flex items-center justify-center text-sm">{e}</div>

            ))}

          </div>

          <div>

            <p className="text-sm text-slate-700 font-medium leading-tight">Trusted by 1,200+ SMEs</p>

            <p className="text-xs text-white/35">across India · 4.9 ★ average rating</p>

          </div>

        </div>

      </div>

    </div>

  )

}






function SuccessScreen({ businessName }: { businessName: string }) {

  const [count, setCount] = useState(0)



  useEffect(() => {

    const t = setTimeout(() => {

      window.location.href = '/dashboard'

    }, 3000)

    const i = setInterval(() => setCount(c => Math.min(c + 1, 100)), 28)

    return () => { clearTimeout(t); clearInterval(i) }

  }, [])



  return (

    <div className="fixed inset-0 flex items-center justify-center z-50"

      style={{ background: 'linear-gradient(160deg, #ffffff 0%, #fff7ed 40%, #ffedd5 100%)' }}

    >

      {/* Confetti orbs */}

      {[...Array(8)].map((_, i) => (

        <div

          key={i}

          className="absolute rounded-full opacity-20 animate-float"

          style={{

            width: `${40 + i * 20}px`,

            height: `${40 + i * 20}px`,

            background: 'radial-gradient(circle, rgba(251,146,60,0.15), transparent)',

            top: `${10 + i * 10}%`,

            left: `${5 + i * 12}%`,

            animationDelay: `${i * 0.3}s`,

          }}

        />

      ))}



      <div className="relative z-10 text-center animate-fade-up px-6 max-w-md">

        <div className="w-24 h-24 rounded-full bg-brand-gradient flex items-center justify-center text-5xl mx-auto mb-6 shadow-glow animate-float">

          🎉

        </div>

        <h1 className="font-display font-bold text-white text-3xl tracking-tight mb-2">

          You're all set!

        </h1>

        <p className="text-slate-500 text-sm mb-8">

          <span className="text-slate-900 font-semibold">{businessName}</span> is ready on Munim.ai.

          <br/>Taking you to your dashboard…

        </p>



        {/* Progress bar */}

        <div className="w-full bg-white/80 rounded-full h-1.5 overflow-hidden">

          <div

            className="h-full bg-brand-gradient rounded-full transition-all duration-75"

            style={{ width: `${count}%` }}

          />

        </div>

      </div>

    </div>

  )

}






function Stepper({ current }: { current: number }) {

  return (

    <div className="flex items-center gap-2 mb-8">

      {STEPS.map((s, i) => (

        <div key={s.id} className="flex items-center gap-2">

          <div className={`

            flex items-center gap-1.5 transition-all duration-300

            ${current === s.id ? 'opacity-100' : current > s.id ? 'opacity-70' : 'opacity-30'}

          `}>

            <div className={`

              w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold transition-all duration-300

              ${current === s.id

                ? 'bg-brand-gradient text-white shadow-glow'

                : current > s.id

                  ? 'bg-brand-700/50 text-brand-600'

                  : 'bg-white/8 text-slate-400'

              }

            `}>

              {current > s.id

                ? <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3"><polyline points="20 6 9 17 4 12"/></svg>

                : s.id

              }

            </div>

            <span className={`text-xs font-medium hidden sm:block transition-colors duration-300 ${current === s.id ? 'text-white' : 'text-slate-400'}`}>

              {s.label}

            </span>

          </div>

          {i < STEPS.length - 1 && (

            <div className={`flex-1 h-px w-10 transition-all duration-500 ${current > s.id ? 'bg-brand-500/60' : 'bg-white/80'}`} />

          )}

        </div>

      ))}

    </div>

  )

}






const defaultProfile: BusinessProfile = {

  businessName: '', gstin: '', state: '', address: '', businessType: '', phone: '', email: '',

}



export default function Onboard() {

  const [step, setStep] = useState(1)

  const [profile, setProfile] = useState<BusinessProfile>(defaultProfile)

  const [items, setItems]     = useState<CatalogItem[]>([])

  const [isSubmitting, setIsSubmitting] = useState(false)

  const [done, setDone]       = useState(false)



  const updateProfile = (field: keyof BusinessProfile, value: string) => {

    setProfile(p => ({ ...p, [field]: value }))

  }



  const addItem = () => {

    setItems(prev => [...prev, {

      id: uid(), name: '', unit: 'pcs', price: '', gstRate: '18', hsn: '', stock: '',

    }])

  }



  const removeItem = (id: string) => setItems(prev => prev.filter(i => i.id !== id))



  const updateItem = (id: string, field: keyof CatalogItem, value: string) => {

    setItems(prev => prev.map(i => i.id === id ? { ...i, [field]: value } : i))

  }



  const handleSubmit = async () => {

    setIsSubmitting(true)

    
    await new Promise(r => setTimeout(r, 1400))

    setIsSubmitting(false)

    setDone(true)

  }



  if (done) return <SuccessScreen businessName={profile.businessName || 'Your Business'} />



  return (

    <div

      className="min-h-screen flex items-stretch"

      style={{

        fontFamily: "'Inter', 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, sans-serif",

        background: 'linear-gradient(160deg, #ffffff 0%, #fff7ed 40%, #ffedd5 100%)',

      }}

    >

      {/* ── Left hero panel (desktop) ── */}

      <div className="hidden lg:block flex-[0.95] relative border-r border-white border-slate-200/60 shadow-xl">

        <HeroPanel step={step} />

      </div>



      {/* ── Right form panel ── */}

      <div className="flex-1 flex flex-col justify-center px-6 py-10 lg:px-12 overflow-y-auto">

        <div className="w-full max-w-md mx-auto">



          {/* Mobile logo */}

          <div className="flex lg:hidden items-center gap-3 mb-8">

            <div className="w-9 h-9 rounded-xl bg-brand-gradient flex items-center justify-center shadow-glow">

              <svg width="18" height="18" viewBox="0 0 24 24" fill="none">

                <path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5" stroke="white" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>

              </svg>

            </div>

            <span className="font-display font-bold text-white text-lg">Munim.ai</span>

          </div>



          {/* Step progress */}

          <Stepper current={step} />



          {/* Card */}

          <div

            className="rounded-3xl border border-white border-slate-200/60 shadow-xl p-8"

            style={{

              background: 'rgba(255,255,255,0.04)',

              backdropFilter: 'blur(20px)',

              WebkitBackdropFilter: 'blur(20px)',

              boxShadow: '0 24px 64px rgba(0,0,0,0.2), inset 0 1px 0 rgba(255,255,255,0.06)',

            }}

          >

            {step === 1 && (

              <StepBusiness

                profile={profile}

                onChange={updateProfile}

                onNext={() => setStep(2)}

              />

            )}

            {step === 2 && (

              <StepCatalog

                items={items}

                onAdd={addItem}

                onRemove={removeItem}

                onUpdate={updateItem}

                onNext={() => setStep(3)}

                onBack={() => setStep(1)}

              />

            )}

            {step === 3 && (

              <StepReview

                profile={profile}

                items={items}

                onSubmit={handleSubmit}

                onBack={() => setStep(2)}

                isSubmitting={isSubmitting}

              />

            )}

          </div>



          {/* Footer */}

          <p className="text-center text-xs text-white/20 mt-6">

            Munim.ai · Built for Indian SMEs · GST-compliant · Secure

          </p>

        </div>

      </div>

    </div>

  )

}

