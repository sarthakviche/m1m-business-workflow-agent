export default function Login() {
  return (
    <div style={{ padding: '24px', fontFamily: 'Inter, system-ui, sans-serif', backgroundColor: '#0f172a', color: '#f8fafc', minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
      <div style={{ background: '#1e293b', padding: '40px', borderRadius: '12px', border: '1px solid #334155', textAlign: 'center' }}>
        <h1 style={{ margin: '0 0 16px 0', fontSize: '28px', color: '#38bdf8' }}>Login to M1M</h1>
        <p style={{ color: '#94a3b8', marginBottom: '24px' }}>Authentication is coming in Phase 1.</p>
        <a href="/onboard" style={{ background: 'linear-gradient(135deg, #0284c7, #2563eb)', color: '#fff', padding: '10px 20px', borderRadius: '8px', textDecoration: 'none', fontWeight: 600 }}>Go to Onboarding</a>
      </div>
    </div>
  )
}
