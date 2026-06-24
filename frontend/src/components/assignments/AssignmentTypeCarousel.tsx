import { useCallback, useEffect, useRef, useState } from 'react'
import '../../styles/assignmentTypeCarousel.css'

export type AssignmentTypeKey = 'pdf' | 'quiz' | 'discussion' | 'group'

export type AssignmentTypeOption = {
  key: AssignmentTypeKey
  title: string
  description: string
  icon: string
  cta: string
  features: string[]
  guidelineTitle: string
  guidelineBody: string
  guidelineLead: string
}

const TYPE_LABELS = ['PDF / Paper', 'Quiz', 'Discussion', 'Group assignment']

function slideRole(slideIndex: number, currentIndex: number, slideCount: number) {
  if (slideIndex === currentIndex) return 'center'
  const diff = (slideIndex - currentIndex + slideCount) % slideCount
  if (diff === 1) return 'next'
  if (diff === slideCount - 1) return 'prev'
  return 'hidden'
}

export function AssignmentTypeCarousel({
  types,
  onSelect,
}: {
  types: AssignmentTypeOption[]
  onSelect: (key: AssignmentTypeKey) => void
}) {
  const slideCount = types.length
  const [currentIndex, setCurrentIndex] = useState(0)
  const dragRef = useRef({ active: false, startX: 0 })

  const goTo = useCallback((index: number) => {
    setCurrentIndex(((index % slideCount) + slideCount) % slideCount)
  }, [slideCount])

  const step = useCallback(
    (delta: number) => {
      goTo(currentIndex + delta)
    },
    [currentIndex, goTo],
  )

  useEffect(() => {
    const onKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'ArrowLeft') step(-1)
      if (e.key === 'ArrowRight') step(1)
    }
    document.addEventListener('keydown', onKeyDown)
    return () => document.removeEventListener('keydown', onKeyDown)
  }, [step])

  const handleSlideClick = (index: number, key: AssignmentTypeKey) => {
    if (index !== currentIndex) {
      goTo(index)
      return
    }
    onSelect(key)
  }

  const activeType = types[currentIndex]

  return (
    <div className="assignment-type-carousel-wrap">
      <div className="assignment-type-carousel">
        <button
          type="button"
          className="carousel-nav carousel-nav--prev"
          onClick={() => step(-1)}
          aria-label="Previous assignment type"
        >
          <i className="bi bi-chevron-left" aria-hidden />
        </button>

        <div
          className="carousel-viewport"
          onPointerDown={(e) => {
            dragRef.current = { active: true, startX: e.clientX }
          }}
          onPointerUp={(e) => {
            if (!dragRef.current.active) return
            dragRef.current.active = false
            const dx = e.clientX - dragRef.current.startX
            if (Math.abs(dx) > 50) step(dx < 0 ? 1 : -1)
          }}
          onPointerCancel={() => {
            dragRef.current.active = false
          }}
        >
          <div className="carousel-track">
            {types.map((type, index) => {
              const role = slideRole(index, currentIndex, slideCount)
              return (
                <article
                  key={type.key}
                  className={`carousel-slide assignment-type-card is-${role}${role === 'center' ? ' is-active-slide' : ''}`}
                  data-type={type.key}
                  data-index={index}
                  onClick={() => handleSlideClick(index, type.key)}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter' || e.key === ' ') {
                      e.preventDefault()
                      handleSlideClick(index, type.key)
                    }
                  }}
                  role="button"
                  tabIndex={role === 'hidden' ? -1 : 0}
                  aria-hidden={role === 'hidden'}
                >
                  <div className={`carousel-slide-inner carousel-slide-inner--${type.key}`}>
                    <div className="carousel-slide-icon">
                      <i className={`bi ${type.icon}`} aria-hidden />
                    </div>
                    <h4 className="carousel-slide-title">{type.title}</h4>
                    <p className="carousel-slide-desc">{type.description}</p>
                    <ul className="carousel-slide-features">
                      {type.features.map((feature) => (
                        <li key={feature}>
                          <i className="bi bi-check2" aria-hidden />
                          {feature}
                        </li>
                      ))}
                    </ul>
                    <button
                      type="button"
                      className={`carousel-slide-cta carousel-slide-cta--${type.key}`}
                      onClick={(e) => {
                        e.stopPropagation()
                        onSelect(type.key)
                      }}
                    >
                      <i className={`bi ${type.icon} me-2`} aria-hidden />
                      {type.cta}
                    </button>
                  </div>
                </article>
              )
            })}
          </div>
        </div>

        <button
          type="button"
          className="carousel-nav carousel-nav--next"
          onClick={() => step(1)}
          aria-label="Next assignment type"
        >
          <i className="bi bi-chevron-right" aria-hidden />
        </button>
      </div>

      <div className="carousel-footer">
        <div className="carousel-dots" role="tablist" aria-label="Assignment type">
          {types.map((type, index) => (
            <button
              key={type.key}
              type="button"
              className={`carousel-dot${index === currentIndex ? ' is-active' : ''}`}
              data-index={index}
              role="tab"
              aria-selected={index === currentIndex}
              aria-label={type.title}
              onClick={() => goTo(index)}
            />
          ))}
        </div>
        <p className="carousel-type-label">{TYPE_LABELS[currentIndex]}</p>
      </div>

      <section className="assignment-guidelines-panel" aria-labelledby="assignmentGuidelinesHeading">
        <div className="assignment-guidelines-panel__head">
          <h4 className="assignment-guidelines-panel__title" id="assignmentGuidelinesHeading">
            <i className="bi bi-info-circle me-2" aria-hidden />
            Assignment type tips
          </h4>
          <p className="assignment-guidelines-panel__lead">{activeType.guidelineLead}</p>
        </div>
        <div className="assignment-guidelines-grid">
          {types.map((type, index) => (
            <button
              key={type.key}
              type="button"
              className={`guideline-chip guideline-chip--${type.key}${index === currentIndex ? ' is-highlighted' : ''}`}
              data-guideline-index={index}
              onClick={() => goTo(index)}
            >
              <strong>
                <i className={`bi ${type.icon} me-1`} aria-hidden />
                {type.guidelineTitle}
              </strong>
              <span>{type.guidelineBody}</span>
            </button>
          ))}
        </div>
      </section>
    </div>
  )
}
