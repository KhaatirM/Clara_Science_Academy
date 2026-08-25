import { useState } from 'react'
import { getCsrfToken } from '../../api/client'
import type { SessionUser } from '../../types/session'

type Props = {
  user: SessionUser
  onChanged: () => Promise<void> | void
}

export function ForcePasswordChangeHost({ user, onChanged }: Props) {
  const mustChange = Boolean(user.must_change_password || user.is_temporary_password)
  const [newPassword, setNewPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [saving, setSaving] = useState(false)
  const [doneCreds, setDoneCreds] = useState<{
    username: string
    password: string
    display_id: string
  } | null>(null)

  if (!mustChange && !doneCreds) return null

  async function submit() {
    setError(null)
    if (newPassword.length < 8) {
      setError('Password must be at least 8 characters long.')
      return
    }
    if (newPassword !== confirmPassword) {
      setError('Passwords do not match.')
      return
    }
    setSaving(true)
    try {
      const token = getCsrfToken() || user.csrf_token
      const body = new FormData()
      body.set('new_password', newPassword)
      body.set('confirm_password', confirmPassword)
      if (token) body.set('csrf_token', token)
      const res = await fetch('/change-password-popup', {
        method: 'POST',
        credentials: 'same-origin',
        headers: token ? { 'X-CSRFToken': token } : undefined,
        body,
      })
      const data = (await res.json()) as {
        success?: boolean
        message?: string
        username?: string
        password?: string
        user_id?: string
      }
      if (!data.success) {
        setError(data.message || 'Could not change password.')
        return
      }
      setDoneCreds({
        username: data.username || user.username,
        password: data.password || newPassword,
        display_id: data.user_id || String(user.id),
      })
      await onChanged()
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Could not change password.')
    } finally {
      setSaving(false)
    }
  }

  return (
    <div
      className="fixed inset-0 z-[2000] flex items-center justify-center bg-slate-900/60 p-4"
      role="dialog"
      aria-modal="true"
      aria-labelledby="force-pw-title"
    >
      <div className="w-full max-w-md overflow-hidden rounded-2xl bg-white shadow-2xl ring-1 ring-black/10">
        {doneCreds ? (
          <>
            <div className="bg-emerald-700 px-5 py-4 text-white">
              <h2 id="force-pw-title" className="text-lg font-bold">
                Password changed
              </h2>
            </div>
            <div className="space-y-3 px-5 py-4 text-sm text-slate-800">
              <p>Save your login details. You will need them next time you sign in.</p>
              <div>
                <div className="text-xs font-bold uppercase tracking-wide text-slate-500">Username</div>
                <div className="font-semibold">{doneCreds.username}</div>
              </div>
              <div>
                <div className="text-xs font-bold uppercase tracking-wide text-slate-500">Password</div>
                <div className="font-semibold break-all">{doneCreds.password}</div>
              </div>
              <div>
                <div className="text-xs font-bold uppercase tracking-wide text-slate-500">ID</div>
                <div className="font-semibold">{doneCreds.display_id}</div>
              </div>
              <button
                type="button"
                className="mt-2 w-full rounded-full bg-emerald-700 px-4 py-2.5 text-sm font-bold text-white hover:bg-emerald-800"
                onClick={() => setDoneCreds(null)}
              >
                Continue
              </button>
            </div>
          </>
        ) : (
          <>
            <div className="bg-amber-500 px-5 py-4 text-slate-900">
              <h2 id="force-pw-title" className="text-lg font-bold">
                Password change required
              </h2>
            </div>
            <div className="space-y-3 px-5 py-4 text-sm text-slate-800">
              <p className="rounded-xl bg-sky-50 px-3 py-2 text-sky-950">
                You are using a temporary password or this is your first login. Choose a new
                password to continue.
              </p>
              <label className="block">
                <span className="mb-1 block text-xs font-bold uppercase tracking-wide text-slate-500">
                  New password
                </span>
                <input
                  type="password"
                  autoComplete="new-password"
                  value={newPassword}
                  onChange={(e) => setNewPassword(e.target.value)}
                  className="w-full rounded-lg border border-slate-200 px-3 py-2"
                  minLength={8}
                />
              </label>
              <label className="block">
                <span className="mb-1 block text-xs font-bold uppercase tracking-wide text-slate-500">
                  Confirm password
                </span>
                <input
                  type="password"
                  autoComplete="new-password"
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  className="w-full rounded-lg border border-slate-200 px-3 py-2"
                />
              </label>
              <p className="text-xs text-slate-500">
                At least 8 characters, with uppercase, lowercase, and a number. Must differ from
                your temporary password.
              </p>
              {error ? (
                <div className="rounded-xl border border-red-200 bg-red-50 px-3 py-2 text-red-800">
                  {error}
                </div>
              ) : null}
              <button
                type="button"
                disabled={saving}
                onClick={() => void submit()}
                className="w-full rounded-full bg-violet-700 px-4 py-2.5 text-sm font-bold text-white hover:bg-violet-800 disabled:opacity-60"
              >
                {saving ? 'Saving…' : 'Change password'}
              </button>
            </div>
          </>
        )}
      </div>
    </div>
  )
}
