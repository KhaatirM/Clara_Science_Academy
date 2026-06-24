import { useEffect, type ReactNode } from 'react'
import { createPortal } from 'react-dom'

/** Bootstrap-styled modal matching legacy Jinja templates (no Bootstrap JS). */
export function LegacyBootstrapModal({
  show,
  onClose,
  title,
  children,
  className = '',
  size = '',
}: {
  show: boolean
  onClose: () => void
  title: ReactNode
  children: ReactNode
  className?: string
  size?: 'lg' | ''
}) {
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

  return createPortal(
    <>
      <div className="modal-backdrop fade show" onClick={onClose} aria-hidden />
      <div
        className={`modal fade show d-block ${className}`}
        tabIndex={-1}
        role="dialog"
        aria-modal
        onClick={onClose}
      >
        <div
          className={`modal-dialog ${size === 'lg' ? 'modal-lg' : ''} modal-dialog-centered`}
          onClick={(e) => e.stopPropagation()}
        >
          <div className="modal-content">
            <div className="modal-header">
              <h5 className="modal-title">{title}</h5>
              <button type="button" className="btn-close" aria-label="Close" onClick={onClose} />
            </div>
            {children}
          </div>
        </div>
      </div>
    </>,
    document.body,
  )
}
