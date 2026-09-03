import React, { useState } from 'react'
import { useNavigate } from 'react-router-dom'

export default function Login() {
  const [phone, setPhone] = useState('9876543210')
  const navigate = useNavigate()

  const handleLogin = (e: React.FormEvent) => {
    e.preventDefault()
    // Development authentication flow: navigate directly to dashboard using dev phone context
    navigate('/dashboard')
  }

  return (
    <div style={{
      padding: '40px 20px',
      fontFamily: 'Inter, system-ui, sans-serif',
      backgroundColor: '#0f172a',
      color: '#f8fafc',
      minHeight: '100vh',
      display: 'flex',
      justifyContent: 'center',
      alignItems: 'center'
    }}>
      <div style={{
        background: '#1e293b',
        padding: '32px',
        borderRadius: '16px',
        border: '1px solid #334155',
        width: '100%',
        maxWidth: '400px',
        boxShadow: '0 20px 25px -5px rgba(0, 0, 0, 0.5)'
      }}>
        <h1 style={{ margin: '0 0 8px 0', fontSize: '26px', color: '#38bdf8', textAlign: 'center' }}>Munim.ai</h1>
        <p style={{ margin: '0 0 24px 0', color: '#94a3b8', fontSize: '14px', textAlign: 'center' }}>
          WhatsApp + Web Business Copilot for Indian SMEs
        </p>

        <form onSubmit={handleLogin}>
          <div style={{ marginBottom: '20px' }}>
            <label style={{ display: 'block', fontSize: '13px', color: '#cbd5e1', marginBottom: '6px' }}>
              Development Phone Number
            </label>
            <input
              type="text"
              value={phone}
              onChange={(e) => setPhone(e.target.value)}
              placeholder="9876543210"
              style={{
                width: '100%',
                padding: '12px',
                borderRadius: '8px',
                border: '1px solid #334155',
                background: '#0f172a',
                color: '#fff',
                fontSize: '15px',
                boxSizing: 'border-box'
              }}
            />
            <span style={{ fontSize: '12px', color: '#64748b', marginTop: '4px', display: 'block' }}>
              Pre-configured test tenant ID
            </span>
          </div>

          <button
            type="submit"
            style={{
              width: '100%',
              padding: '12px',
              borderRadius: '8px',
              border: 'none',
              background: 'linear-gradient(135deg, #0284c7, #2563eb)',
              color: '#fff',
              fontSize: '15px',
              fontWeight: 600,
              cursor: 'pointer'
            }}
          >
            Enter Faculty Demo Dashboard
          </button>
        </form>
      </div>
    </div>
  )
}
