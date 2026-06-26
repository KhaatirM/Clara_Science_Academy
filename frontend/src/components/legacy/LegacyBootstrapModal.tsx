import { useEffect, type ReactNode } from 'react'
import { createPortal } from 'react-dom'
import { useLegacyMgmtPortal } from './LegacyMgmtScope'

/** Bootstrap-styled modal matching legacy Jinja templates (no Bootstrap JS). */
export function LegacyBootstrapModal({
  show,
  onClose,
  title,
  children,
  className = '',
  size = '',
  id,
  scrollable = false,
  headerClassName = '',
  closeWhite = false,
  hideHeaderClose = false,
  contentStyle,
  rootClassName = '',
}: {
  show: boolean
  onClose: () => void
  title: ReactNode
  children: ReactNode
  className?: string
  size?: 'lg' | ''
  id?: string
  scrollable?: boolean
  headerClassName?: string
  closeWhite?: boolean
  hideHeaderClose?: boolean
  contentStyle?: React.CSSProperties
  /** Wrapper class (backdrop + dialog), e.g. mgmt-cal-modal mgmt-cal-modal--warm */
  rootClassName?: string
}) {
  const portalRoot = useLegacyMgmtPortal()

  useEffect(() => {
    if (!show) return
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose()
    }
    document.body.classList.add('modal-open')
    document.body.style.overflow = 'hidden'
    window.addEventListener('keydown', onKey)
    return () => {
      document.body.classList.remove('modal-open')
      document.body.style.overflow = ''
      window.removeEventListener('keydown', onKey)
    }
  }, [show, onClose])

  if (!show) return null

  const target = portalRoot ?? document.body

  return createPortal(
    <div className={['legacy-modal-stack', rootClassName].filter(Boolean).join(' ')}>
      <div className="modal-backdrop fade show mgmt-cal-modal-backdrop" onClick={onClose} aria-hidden />
      <div
        id={id}
        className={`modal fade show d-block mgmt-cal-modal-dialog ${className}`}
        tabIndex={-1}
        role="dialog"
        aria-modal
        onClick={onClose}
      >
        <div
          className={`modal-dialog ${size === 'lg' ? 'modal-lg' : ''} ${
            scrollable ? 'modal-dialog-scrollable' : 'modal-dialog-centered'
          }`}
          onClick={(e) => e.stopPropagation()}
        >
          <div
            className="modal-content"
            style={{ borderRadius: '1rem', border: 'none', boxShadow: '0 10px 40px rgba(0,0,0,0.2)', ...contentStyle }}
          >
            <div
              className={`modal-header ${headerClassName}`}
              style={
                headerClassName.includes('text-white')
                  ? { borderRadius: '1rem 1rem 0 0', border: 'none', padding: '1.5rem' }
                  : undefined
              }
            >
              <h5 className="modal-title fw-bold">{title}</h5>
              {hideHeaderClose ? null : (
                <button
                  type="button"
                  className={`btn-close ${closeWhite ? 'btn-close-white' : ''}`}
                  aria-label="Close"
                  onClick={onClose}
                />
              )}
            </div>
            {children}
          </div>
        </div>
      </div>
    </div>,
    target,
  )
}
