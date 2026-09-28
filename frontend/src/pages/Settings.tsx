export default function Settings() {
  return (
    <div style={{ padding: '24px', fontFamily: 'Inter, system-ui, sans-serif', backgroundColor: '#0f172a', color: '#f8fafc', minHeight: '100vh' }}>
      <header style={{ marginBottom: '24px' }}>
        <h1 style={{ margin: 0, fontSize: '28px', color: '#38bdf8' }}>Settings</h1>
        <p style={{ margin: '4px 0 0', color: '#94a3b8' }}>Manage your account and preferences.</p>
      </header>

      <nav style={{ display: 'flex', gap: '12px', marginBottom: '24px', flexWrap: 'wrap' }}>
        <a href="/chat" style={{ color: '#fff', padding: '8px 16px', borderRadius: '6px', background: '#00a884', textDecoration: 'none', fontWeight: 600 }}>← M1M Chat</a>
        <a href="/dashboard" style={{ color: '#94a3b8', padding: '8px 16px', borderRadius: '6px', textDecoration: 'none' }}>Dashboard</a>
      </nav>

      <div style={{ background: '#1e293b', padding: '20px', borderRadius: '12px', border: '1px solid #334155' }}>
         <p style={{ color: '#94a3b8' }}>Settings options will be available soon.</p>
      </div>
    </div>
  )
}
