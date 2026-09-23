import { useEffect, useRef, useState } from 'react'
import { createPortal } from 'react-dom'

import {
  subscribeThemeReveal,
  type ThemeRevealMode,
  type ThemeRevealRequest,
} from '../../utils/themeReveal'
import {
  getThemeRevealMeta,
  type ThemeMotifKind,
  type ThemeRevealMeta,
} from '../../utils/themeRevealMeta'

const FULL_MS = 3500
const FLASH_MS = 700
const FULL_REDUCED_MS = 1200
const FLASH_REDUCED_MS = 400

type ActiveReveal = {
  meta: ThemeRevealMeta
  mode: ThemeRevealMode
  reduced: boolean
  key: number
}

function prefersReducedMotion(): boolean {
  return window.matchMedia('(prefers-reduced-motion: reduce)').matches
}

function MotifGraphic({ kind, accent }: { kind: ThemeMotifKind; accent: string }) {
  const sizeClass = 'h-28 w-28 drop-shadow-lg sm:h-36 sm:w-36'
  switch (kind) {
    case 'snow':
      return (
        <svg className={sizeClass} aria-hidden={true} viewBox="0 0 64 64" fill="none" stroke={accent} strokeWidth="2.4" strokeLinecap="round">
          <path d="M32 6v52M6 32h52M14 14l36 36M50 14L14 50" />
          <circle cx="32" cy="32" r="4" fill={accent} stroke="none" />
        </svg>
      )
    case 'leaf':
      return (
        <svg className={sizeClass} aria-hidden={true} viewBox="0 0 64 64">
          <path fill={accent} d="M32 8c8 10 22 14 22 28-8 2-16-2-22-10-6 8-14 12-22 10C10 22 24 18 32 8zm0 18v30" />
        </svg>
      )
    case 'bloom':
      return (
        <svg className={sizeClass} aria-hidden={true} viewBox="0 0 64 64">
          <circle cx="32" cy="20" r="8" fill={accent} />
          <circle cx="22" cy="30" r="8" fill={accent} opacity="0.75" />
          <circle cx="42" cy="30" r="8" fill={accent} opacity="0.75" />
          <circle cx="26" cy="40" r="8" fill={accent} opacity="0.85" />
          <circle cx="38" cy="40" r="8" fill={accent} opacity="0.85" />
          <circle cx="32" cy="32" r="6" fill="#fde68a" />
        </svg>
      )
    case 'sun':
      return (
        <svg className={sizeClass} aria-hidden={true} viewBox="0 0 64 64">
          <circle cx="32" cy="32" r="12" fill={accent} />
          <g stroke={accent} strokeWidth="3" strokeLinecap="round">
            <path d="M32 6v8M32 50v8M6 32h8M50 32h8M12 12l6 6M46 46l6 6M12 52l6-6M46 18l6-6" />
          </g>
        </svg>
      )
    case 'ornament':
      return (
        <svg className={sizeClass} aria-hidden={true} viewBox="0 0 48 56">
          <path fill={accent} d="M24 8c10 0 18 8 18 18s-8 18-18 18S6 36 6 26 14 8 24 8z" />
          <rect x="21" y="2" width="6" height="10" rx="1" fill="#fbbf24" />
        </svg>
      )
    case 'wave':
      return (
        <svg className={sizeClass} aria-hidden={true} viewBox="0 0 80 40" fill="none" stroke={accent} strokeWidth="3.5" strokeLinecap="round">
          <path d="M4 22c10-12 18 12 28 0s18 12 28 0 18 12 20 0" />
        </svg>
      )
    case 'tree':
      return (
        <svg className={sizeClass} aria-hidden={true} viewBox="0 0 48 64">
          <path fill={accent} d="M24 4L40 28H30l14 20H4l14-20H8L24 4z" />
          <rect x="21" y="48" width="6" height="12" fill="#78541f" />
        </svg>
      )
    case 'sunset':
      return (
        <svg className={sizeClass} aria-hidden={true} viewBox="0 0 64 40">
          <circle cx="32" cy="28" r="14" fill={accent} />
          <path fill={accent} opacity="0.45" d="M4 34h56v6H4z" />
        </svg>
      )
    case 'star':
      return (
        <svg className={sizeClass} aria-hidden={true} viewBox="0 0 40 40">
          <polygon
            fill={accent}
            points="20,4 24,16 36,16 26,24 30,36 20,28 10,36 14,24 4,16 16,16"
          />
        </svg>
      )
    case 'dune':
      return (
        <svg className={sizeClass} aria-hidden={true} viewBox="0 0 80 36">
          <path fill={accent} d="M0 28c12-12 24 4 40-4s20 8 40 0v12H0z" />
        </svg>
      )
    case 'sprig':
      return (
        <svg className={sizeClass} aria-hidden={true} viewBox="0 0 40 64">
          <ellipse cx="20" cy="14" rx="8" ry="12" fill={accent} />
          <ellipse cx="12" cy="26" rx="7" ry="11" fill={accent} opacity="0.8" />
          <ellipse cx="28" cy="26" rx="7" ry="11" fill={accent} opacity="0.8" />
          <rect x="18" y="36" width="4" height="24" fill="#86efac" />
        </svg>
      )
    case 'petal':
      return (
        <svg className={sizeClass} aria-hidden={true} viewBox="0 0 48 48">
          <path
            fill={accent}
            d="M24 42s-14-9-14-20a10 10 0 0 1 20 0c0-6 4-10 8-10a10 10 0 0 1 0 20c0 11-14 20-14 20z"
          />
        </svg>
      )
    case 'cherry':
      return (
        <svg className={sizeClass} aria-hidden={true} viewBox="0 0 56 56">
          <circle cx="18" cy="34" r="10" fill={accent} />
          <circle cx="36" cy="30" r="10" fill={accent} opacity="0.85" />
          <path fill="none" stroke="#86efac" strokeWidth="2.5" d="M18 24c4-10 14-14 22-12" />
        </svg>
      )
    case 'ribbon':
      return (
        <svg className={sizeClass} aria-hidden={true} viewBox="0 0 100 40">
          <path fill={accent} d="M0 28c16-18 28 6 42-6s22 14 36-2 14 8 22 2v18H0z" opacity="0.9" />
        </svg>
      )
    case 'cloud':
      return (
        <svg className={sizeClass} aria-hidden={true} viewBox="0 0 72 44">
          <path fill={accent} d="M18 28a14 14 0 0 1 2-28 16 16 0 0 1 30 6 12 12 0 0 1 4 24H18z" />
          <path fill="#fbbf24" d="M40 30L34 42h6l-2 8 12-14h-6l4-6z" />
        </svg>
      )
    case 'grape':
      return (
        <svg className={sizeClass} aria-hidden={true} viewBox="0 0 40 56">
          <circle cx="14" cy="16" r="8" fill={accent} />
          <circle cx="26" cy="14" r="8" fill={accent} opacity="0.9" />
          <circle cx="20" cy="26" r="8" fill={accent} opacity="0.85" />
          <path fill="none" stroke="#86efac" strokeWidth="2" d="M20 34v18" />
        </svg>
      )
    case 'mint':
      return (
        <svg className={sizeClass} aria-hidden={true} viewBox="0 0 48 48">
          <path
            fill={accent}
            d="M24 40c0-12 10-18 10-28-8 2-10 10-10 16 0-6-2-14-10-16 0 10 10 16 10 28z"
          />
        </svg>
      )
    case 'coral':
      return (
        <svg className={sizeClass} aria-hidden={true} viewBox="0 0 48 56">
          <path
            fill={accent}
            d="M24 4c0 10-8 14-8 24 6-2 10 2 12 8 2-6 6-10 12-8 0-10-8-14-8-24-2 4-6 6-8 0z"
          />
        </svg>
      )
    case 'gem':
      return (
        <svg className={sizeClass} aria-hidden={true} viewBox="0 0 48 56">
          <path fill={accent} d="M24 4L40 20 24 52 8 20z" />
          <path fill="#fff" opacity="0.35" d="M24 4L40 20 24 28z" />
        </svg>
      )
    case 'hex':
      return (
        <svg className={sizeClass} aria-hidden={true} viewBox="0 0 48 52">
          <path fill={accent} d="M24 2l12 8v16l-12 8-12-8V10z" />
          <path fill="#fff" opacity="0.3" d="M24 2l12 8-12 8L12 10z" />
        </svg>
      )
    case 'shard':
      return (
        <svg className={sizeClass} aria-hidden={true} viewBox="0 0 56 40">
          <path fill={accent} d="M4 28L18 8l16 6 14-4v22H4z" />
        </svg>
      )
    case 'wash':
    default:
      return (
        <svg className={sizeClass} aria-hidden={true} viewBox="0 0 64 64">
          <circle cx="32" cy="32" r="22" fill={accent} opacity="0.35" />
          <circle cx="32" cy="32" r="12" fill={accent} />
        </svg>
      )
  }
}

export function ThemeRevealHost() {
  const [active, setActive] = useState<ActiveReveal | null>(null)
  const [leaving, setLeaving] = useState(false)
  const fullOpenRef = useRef(false)
  const timerRef = useRef<number | null>(null)
  const keyRef = useRef(0)

  function clearTimer() {
    if (timerRef.current != null) {
      window.clearTimeout(timerRef.current)
      timerRef.current = null
    }
  }

  function dismiss() {
    clearTimer()
    setLeaving(true)
    window.setTimeout(() => {
      setActive(null)
      setLeaving(false)
      fullOpenRef.current = false
    }, 280)
  }

  function startReveal(request: ThemeRevealRequest) {
    const reduced = prefersReducedMotion()
    if (request.mode === 'flash' && fullOpenRef.current) return
    if (request.mode === 'full' && fullOpenRef.current) return

    clearTimer()
    keyRef.current += 1
    const meta = getThemeRevealMeta(request.theme)
    const duration =
      request.mode === 'full'
        ? reduced
          ? FULL_REDUCED_MS
          : FULL_MS
        : reduced
          ? FLASH_REDUCED_MS
          : FLASH_MS

    if (request.mode === 'full') fullOpenRef.current = true
    setLeaving(false)
    setActive({ meta, mode: request.mode, reduced, key: keyRef.current })
    timerRef.current = window.setTimeout(() => {
      dismiss()
    }, duration)
  }

  useEffect(() => {
    return subscribeThemeReveal(startReveal)
    // eslint-disable-next-line react-hooks/exhaustive-deps -- subscribe once; startReveal uses refs
  }, [])

  useEffect(() => () => clearTimer(), [])

  if (!active || typeof document === 'undefined') return null

  const { meta, mode, reduced } = active
  const isFull = mode === 'full'
  const durationMs = isFull ? (reduced ? FULL_REDUCED_MS : FULL_MS) : reduced ? FLASH_REDUCED_MS : FLASH_MS

  return createPortal(
    <div
      key={active.key}
      className={`theme-reveal-overlay fixed inset-0 z-[2000] flex items-center justify-center p-6 ${
        leaving ? 'theme-reveal-overlay--out' : 'theme-reveal-overlay--in'
      } ${isFull ? 'theme-reveal-overlay--full' : 'theme-reveal-overlay--flash'} ${
        reduced ? 'theme-reveal-overlay--reduced' : ''
      }`}
      style={{ background: meta.gradient }}
      role="dialog"
      aria-modal={isFull}
      aria-label={`${meta.label} theme`}
    >
      <div className="theme-reveal-glow pointer-events-none absolute inset-0" aria-hidden />
      <div className="relative z-10 flex max-w-lg flex-col items-center text-center text-white">
        <div className="theme-reveal-motif mb-5 flex items-center justify-center rounded-full bg-white/10 p-6 backdrop-blur-sm ring-1 ring-white/20">
          <MotifGraphic kind={meta.motif} accent={meta.accent} />
        </div>
        <p className="mb-1 text-[0.7rem] font-bold uppercase tracking-[0.2em] text-white/70">
          {isFull ? 'Switching theme' : 'Preview'}
        </p>
        <h2 className="m-0 text-3xl font-extrabold tracking-tight drop-shadow-sm sm:text-4xl">
          {meta.label}
        </h2>
        <p className="mt-2 mb-0 max-w-sm text-base text-white/85 sm:text-lg">{meta.tagline}</p>

        {isFull ? (
          <div
            className="theme-reveal-progress mt-8 h-1.5 w-48 overflow-hidden rounded-full bg-white/20 sm:w-56"
            aria-hidden
          >
            <div
              className="theme-reveal-progress__bar h-full rounded-full"
              style={{
                background: meta.accent,
                animationDuration: `${durationMs}ms`,
              }}
            />
          </div>
        ) : null}
      </div>

      {isFull ? (
        <button
          type="button"
          className="absolute bottom-6 right-6 rounded-xl border border-white/30 bg-black/25 px-4 py-2 text-sm font-semibold text-white backdrop-blur-sm hover:bg-black/40"
          onClick={() => dismiss()}
        >
          Skip
        </button>
      ) : null}

      <style>{`
        .theme-reveal-overlay--in {
          animation: theme-reveal-fade-in 280ms ease-out both;
        }
        .theme-reveal-overlay--out {
          animation: theme-reveal-fade-out 280ms ease-in both;
        }
        .theme-reveal-overlay--flash {
          pointer-events: none;
        }
        .theme-reveal-overlay--full {
          pointer-events: auto;
        }
        .theme-reveal-motif {
          animation: theme-reveal-pop 700ms cubic-bezier(0.22, 1, 0.36, 1) both;
        }
        .theme-reveal-overlay--full:not(.theme-reveal-overlay--reduced) .theme-reveal-motif {
          animation: theme-reveal-pop 900ms cubic-bezier(0.22, 1, 0.36, 1) both,
            theme-reveal-drift 3.2s ease-in-out 0.4s both;
        }
        .theme-reveal-overlay--reduced .theme-reveal-motif {
          animation: none;
        }
        .theme-reveal-glow {
          background:
            radial-gradient(ellipse at 50% 30%, rgba(255,255,255,0.18), transparent 55%),
            radial-gradient(ellipse at 20% 80%, rgba(255,255,255,0.08), transparent 45%);
        }
        .theme-reveal-progress__bar {
          width: 100%;
          transform-origin: left center;
          animation-name: theme-reveal-progress;
          animation-timing-function: linear;
          animation-fill-mode: forwards;
        }
        .theme-reveal-overlay--reduced .theme-reveal-progress__bar {
          animation: none;
          transform: scaleX(1);
        }
        @keyframes theme-reveal-fade-in {
          from { opacity: 0; }
          to { opacity: 1; }
        }
        @keyframes theme-reveal-fade-out {
          from { opacity: 1; }
          to { opacity: 0; }
        }
        @keyframes theme-reveal-pop {
          from { opacity: 0; transform: scale(0.82) translateY(12px); }
          to { opacity: 1; transform: scale(1) translateY(0); }
        }
        @keyframes theme-reveal-drift {
          from { transform: translateY(0) rotate(0deg); }
          to { transform: translateY(-10px) rotate(3deg); }
        }
        @keyframes theme-reveal-progress {
          from { transform: scaleX(0); }
          to { transform: scaleX(1); }
        }
        @media (prefers-reduced-motion: reduce) {
          .theme-reveal-overlay--in,
          .theme-reveal-overlay--out,
          .theme-reveal-motif,
          .theme-reveal-progress__bar {
            animation: none !important;
          }
        }
      `}</style>
    </div>,
    document.body,
  )
}
