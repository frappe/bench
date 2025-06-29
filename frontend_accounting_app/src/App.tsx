import { useState, useEffect } from 'react'
import { supabase } from './lib/supabaseClient'
import Auth from './components/Auth'
import { Session } from '@supabase/supabase-js'
import './App.css' // We can keep this for now, or remove if Tailwind handles all styling
import InvoicesPage from './components/invoices/InvoicesPage';
import ProfitAndLossReport from './components/reports/ProfitAndLossReport';
import BankStatementUpload from './components/banking/BankStatementUpload';
import PayrollPage from './components/payroll/PayrollPage'; // Import PayrollPage

function App() {
  const [session, setSession] = useState<Session | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    setLoading(true)
    supabase.auth.getSession().then(({ data: { session } }) => {
      setSession(session)
      setLoading(false)
    })

    const { data: authListener } = supabase.auth.onAuthStateChange(
      (_event, session) => {
        setSession(session)
        setLoading(false)
      }
    )

    return () => {
      authListener?.unsubscribe()
    }
  }, [])

  const handleSignOut = async () => {
    const { error } = await supabase.auth.signOut()
    if (error) console.error('Error signing out:', error)
  }

  if (loading) {
    return <div style={{textAlign: 'center', marginTop: '50px'}}>Loading...</div>
  }

  return (
    <div className="container" style={{ padding: '20px', maxWidth: '960px', margin: '0 auto' }}>
      <header style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px', paddingBottom: '10px', borderBottom: '1px solid #eee' }}>
        <h1>Accounting App</h1>
        {session && (
          <button
            onClick={handleSignOut}
            style={{ padding: '8px 12px', backgroundColor: '#6c757d', color: 'white', border: 'none', borderRadius: '4px', cursor: 'pointer' }}
          >
            Sign Out
          </button>
        )}
      </header>

      {!session ? (
        <Auth />
      ) : (
        <div>
          <p style={{ marginBottom: '20px' }}>Signed in as: <strong>{session.user.email}</strong></p>
          <InvoicesPage userId={session.user.id} />
          <hr style={{margin: '30px 0'}} />
          <ProfitAndLossReport userId={session.user.id} />
          <hr style={{margin: '30px 0'}} />
          <BankStatementUpload userId={session.user.id} />
          <hr style={{margin: '30px 0'}} />
          <PayrollPage userId={session.user.id} />
        </div>
      )}
    </div>
  )
}

export default App
