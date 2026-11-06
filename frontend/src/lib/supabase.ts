// Sign-in is handled by Supabase Auth. Without these env vars (plain local
// development) there's no login, and the backend's dev mode serves the demo business.

import { createClient } from '@supabase/supabase-js'

const url = import.meta.env.VITE_SUPABASE_URL as string | undefined
const publishableKey = import.meta.env.VITE_SUPABASE_PUBLISHABLE_KEY as string | undefined

export const supabase = url && publishableKey
  ? createClient(url, publishableKey, { auth: { flowType: 'pkce' } })
  : null

/** Google sign-in needs setting up in the Supabase dashboard, so it stays hidden until then. */
export const googleSignInEnabled = import.meta.env.VITE_AUTH_GOOGLE === 'true'
