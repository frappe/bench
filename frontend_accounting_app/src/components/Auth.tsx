import { useState } from 'react'
import { supabase } from '@/lib/supabaseClient'

export default function Auth() {
  const [loading, setLoading] = useState(false)
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [isSignUp, setIsSignUp] = useState(true) // Toggle between Sign Up and Sign In
  const [message, setMessage] = useState('')

  const handleAuth = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    setLoading(true)
    setMessage('')

    try {
      let error = null
      if (isSignUp) {
        const { data, error: signUpError } = await supabase.auth.signUp({ email, password })
        error = signUpError
        if (!error) setMessage('Sign up successful! Check your email for a confirmation link.')
        console.log('Sign up data:', data)
      } else {
        const { data, error: signInError } = await supabase.auth.signInWithPassword({ email, password })
        error = signInError
        if (!error) setMessage('Sign in successful!')
         // Session is automatically handled by Supabase client, App.tsx will react
        console.log('Sign in data:', data)
      }
      if (error) throw error
    } catch (error: any) {
      console.error('Error during authentication:', error)
      setMessage(`Error: ${error.error_description || error.message}`)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div style={{ maxWidth: '420px', margin: '50px auto', padding: '20px', border: '1px solid #ccc', borderRadius: '8px' }}>
      <h1>{isSignUp ? 'Create an Account' : 'Sign In'}</h1>
      <p>{isSignUp ? 'Enter your email and password to sign up.' : 'Enter your credentials to sign in.'}</p>
      <form onSubmit={handleAuth}>
        <div>
          <label htmlFor="email">Email:</label><br />
          <input
            id="email"
            type="email"
            value={email}
            required
            onChange={(e) => setEmail(e.target.value)}
            style={{ width: '100%', padding: '8px', marginBottom: '10px', border: '1px solid #ddd' }}
          />
        </div>
        <div>
          <label htmlFor="password">Password:</label><br />
          <input
            id="password"
            type="password"
            value={password}
            required
            onChange={(e) => setPassword(e.target.value)}
            style={{ width: '100%', padding: '8px', marginBottom: '20px', border: '1px solid #ddd' }}
          />
        </div>
        <div>
          <button type="submit" disabled={loading} style={{ padding: '10px 15px', width: '100%', backgroundColor: '#007bff', color: 'white', border: 'none', borderRadius: '4px' }}>
            {loading ? <span>Loading...</span> : (isSignUp ? 'Sign Up' : 'Sign In')}
          </button>
        </div>
      </form>
      {message && <p style={{ color: message.startsWith('Error:') ? 'red' : 'green', marginTop: '15px' }}>{message}</p>}
      <button onClick={() => setIsSignUp(!isSignUp)} style={{ background: 'none', border: 'none', color: '#007bff', textDecoration: 'underline', cursor: 'pointer', marginTop: '20px', display: 'block', textAlign: 'center' }}>
        {isSignUp ? 'Already have an account? Sign In' : "Don't have an account? Sign Up"}
      </button>
    </div>
  )
}
