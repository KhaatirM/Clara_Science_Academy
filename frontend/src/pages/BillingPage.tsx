import { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'

import {
  billingAddInvoicePlaceholder,
  billingRecordPaymentPlaceholder,
  fetchBillingHub,
} from '../api/billing'
import { useSession } from '../hooks/useSession'
import type { BillingHubResponse } from '../types/billing'
import { spaRoute } from '../utils/spaRoute'

function formatCurrency(value: number): string {
  return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(value)
}

function InsightCard({
  icon,
  value,
  label,
}: {
  icon: string
  value: string | number
  label: string
}) {
  return (
    <div className="flex items-start gap-3 rounded-2xl border border-white/80 bg-white/95 p-4 shadow-sm" role="listitem">
      <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-teal-100 text-lg text-teal-800">
        <i className={`bi ${icon}`} aria-hidden />
      </span>
      <div>
        <div className="text-xl font-bold text-hub-text">{value}</div>
        <div className="text-sm text-hub-muted">{label}</div>
      </div>
    </div>
  )
}

function SectionCard({
  title,
  icon,
  tone,
  description,
  actions,
}: {
  title: string
  icon: string
  tone: 'success' | 'reports'
  description: string
  actions: string[]
}) {
  const headerClass =
    tone === 'success'
      ? 'border-emerald-200 bg-gradient-to-r from-emerald-50 to-white text-emerald-900'
      : 'border-amber-200 bg-gradient-to-r from-amber-50 to-white text-amber-950'

  return (
    <section className="flex h-full flex-col overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
      <div className={`border-b px-5 py-4 ${headerClass}`}>
        <h2 className="flex items-center gap-2 text-base font-bold">
          <i className={`bi ${icon}`} aria-hidden />
          {title}
        </h2>
      </div>
      <div className="flex flex-1 flex-col p-5">
        <p className="text-sm text-hub-muted">{description}</p>
        <div className="mt-4 grid gap-2">
          {actions.map((label) => (
            <button
              key={label}
              type="button"
              disabled
              title="Coming soon"
              className="rounded-xl border border-slate-200 bg-slate-50 px-4 py-2.5 text-sm font-semibold text-slate-400"
            >
              {label}
            </button>
          ))}
        </div>
      </div>
    </section>
  )
}

function canAccessBilling(user: { role_canonical: string; permissions: string[] }): boolean {
  if (user.role_canonical === 'Director') return true
  return user.permissions.includes('billing:manage')
}

export default function BillingPage() {
  const { user } = useSession()
  const [data, setData] = useState<BillingHubResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [message, setMessage] = useState<string | null>(null)
  const [actionBusy, setActionBusy] = useState(false)

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      setData(await fetchBillingHub())
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not load billing hub.')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    void load()
  }, [load])

  async function handlePlaceholderAction(action: 'invoice' | 'payment') {
    setActionBusy(true)
    setMessage(null)
    try {
      const result =
        action === 'invoice'
          ? await billingAddInvoicePlaceholder()
          : await billingRecordPaymentPlaceholder()
      setMessage(result.message)
    } catch (err) {
      setMessage(err instanceof Error ? err.message : 'Action failed.')
    } finally {
      setActionBusy(false)
    }
  }

  if (!user || !canAccessBilling(user)) {
    return (
      <div className="rounded-2xl border border-amber-200 bg-amber-50 p-6 text-amber-950">
        <h1 className="text-lg font-bold">Billing &amp; financials</h1>
        <p className="mt-2 text-sm">This area is limited to directors and staff with billing access.</p>
        <Link to={spaRoute('/management')} className="mt-4 inline-block text-sm font-semibold text-teal-800">
          Return to home
        </Link>
      </div>
    )
  }

  if (loading && !data) {
    return (
      <div className="rounded-2xl border border-slate-200 bg-white p-8 text-center text-hub-muted shadow-sm">
        Loading billing hub…
      </div>
    )
  }

  if (error || !data) {
    return (
      <div className="rounded-2xl border border-red-200 bg-red-50 p-6 text-red-800">
        {error || 'Could not load billing hub.'}
      </div>
    )
  }

  const { metrics } = data
  const shellClass = data.is_director
    ? 'bg-gradient-to-br from-violet-50 via-[#f0ecf5] to-[#e8e4f0]'
    : 'bg-gradient-to-br from-teal-50 via-[#e8f0ec] to-[#dce8e4]'

  return (
    <div className={`rounded-3xl p-5 shadow-sm md:p-6 ${shellClass}`}>
      <header className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
        <div>
          <p className="text-xs font-bold uppercase tracking-wide text-hub-muted">Financial operations</p>
          <h1 className="mt-1 text-2xl font-bold text-hub-text">Billing &amp; financials</h1>
          <p className="mt-2 text-sm text-hub-muted">
            <i className="bi bi-currency-dollar mr-1 text-teal-700" aria-hidden />
            Tuition, fees, invoices, and school-wide financial reporting
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          {data.is_director ? (
            <span className="inline-flex items-center gap-1 rounded-full bg-violet-100 px-3 py-1.5 text-xs font-bold text-violet-900">
              <i className="bi bi-award-fill" aria-hidden />
              Director
            </span>
          ) : (
            <span className="inline-flex items-center gap-1 rounded-full bg-teal-100 px-3 py-1.5 text-xs font-bold text-teal-900">
              <i className="bi bi-shield-fill" aria-hidden />
              Billing access
            </span>
          )}
          <Link
            to={spaRoute(data.urls.home)}
            className="inline-flex items-center gap-2 rounded-xl border border-slate-200 bg-white px-4 py-2 text-sm font-semibold text-hub-text hover:bg-slate-50"
          >
            <i className="bi bi-house-door" aria-hidden />
            Dashboard
          </Link>
          <button
            type="button"
            disabled={actionBusy}
            onClick={() => void handlePlaceholderAction('invoice')}
            className="inline-flex items-center gap-2 rounded-xl border border-slate-200 bg-white px-4 py-2 text-sm font-semibold text-hub-text hover:bg-slate-50 disabled:opacity-60"
          >
            <i className="bi bi-receipt" aria-hidden />
            New invoice
          </button>
          <button
            type="button"
            disabled={actionBusy}
            onClick={() => void handlePlaceholderAction('payment')}
            className="inline-flex items-center gap-2 rounded-xl bg-teal-700 px-4 py-2 text-sm font-semibold text-white hover:bg-teal-800 disabled:opacity-60"
          >
            <i className="bi bi-cash-coin" aria-hidden />
            Record payment
          </button>
        </div>
      </header>

      {message ? (
        <div className="mt-4 rounded-2xl border border-sky-200 bg-sky-50 px-4 py-3 text-sm text-sky-900">
          {message}
        </div>
      ) : null}

      <div className="mt-5 grid gap-3 sm:grid-cols-2 xl:grid-cols-4" role="list">
        <InsightCard icon="bi-graph-up-arrow" value={formatCurrency(metrics.total_revenue)} label="Total revenue" />
        <InsightCard icon="bi-wallet2" value={formatCurrency(metrics.total_payments)} label="Payments received" />
        <InsightCard
          icon="bi-exclamation-circle"
          value={formatCurrency(metrics.outstanding_balance)}
          label="Outstanding balance"
        />
        <InsightCard icon="bi-people" value={metrics.student_count} label="Students on file" />
      </div>

      <div className="mt-5 space-y-5">
        <div className="flex gap-3 rounded-2xl border border-sky-200 bg-sky-50/80 p-4 text-sm text-sky-950">
          <i className="bi bi-info-circle mt-0.5 shrink-0 text-lg" aria-hidden />
          <div>
            <strong className="font-bold">Financial management</strong>
            <p className="mt-1 text-sky-900/90">
              Manage tuition, fees, and financial records. Invoice and payment workflows are being expanded; use the
              actions above for placeholders until full billing is live.
            </p>
            {data.urls.payment_policy ? (
              <a
                href={data.urls.payment_policy}
                target="_blank"
                rel="noopener noreferrer"
                className="mt-2 inline-flex items-center gap-1 font-semibold text-teal-800 hover:text-teal-900"
              >
                <i className="bi bi-file-earmark-pdf" aria-hidden />
                Payment of fees policy
              </a>
            ) : null}
          </div>
        </div>

        <div className="grid gap-4 lg:grid-cols-2">
          <SectionCard
            title="Tuition management"
            icon="bi-mortarboard"
            tone="success"
            description="Manage student tuition and payment plans."
            actions={['View tuition records', 'Generate invoices', 'Payment history']}
          />
          <SectionCard
            title="Financial reports"
            icon="bi-bar-chart-line"
            tone="reports"
            description="Generate financial reports and analytics."
            actions={['Revenue report', 'Expense report', 'Budget analysis']}
          />
        </div>

        <section className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
          <div className="border-b border-slate-200 bg-slate-50 px-5 py-4">
            <h2 className="flex items-center gap-2 text-base font-bold text-hub-text">
              <i className="bi bi-receipt-cutoff text-teal-700" aria-hidden />
              Invoices &amp; pending payments
            </h2>
          </div>
          <div className="p-8 text-center">
            <i className="bi bi-inbox text-4xl text-slate-300" aria-hidden />
            <p className="mt-3 font-bold text-hub-text">No invoices yet</p>
            <p className="mt-1 text-sm text-hub-muted">
              {metrics.active_invoices} active invoice{metrics.active_invoices === 1 ? '' : 's'},{' '}
              {metrics.pending_invoices} pending — billing data models are not connected yet.
            </p>
          </div>
        </section>
      </div>
    </div>
  )
}
