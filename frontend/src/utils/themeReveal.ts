import { normalizeTheme } from './userTheme'

export type ThemeRevealMode = 'full' | 'flash'

export type ThemeRevealRequest = {
  theme: string
  mode: ThemeRevealMode
}

type Listener = (request: ThemeRevealRequest) => void

const listeners = new Set<Listener>()

/**
 * Imperative API for Settings pages. ThemeRevealHost subscribes once in AppLayout.
 * Does not apply the theme itself — callers still call applyUserTheme.
 */
export function playThemeReveal(theme: string, mode: ThemeRevealMode): void {
  const request: ThemeRevealRequest = {
    theme: normalizeTheme(theme),
    mode,
  }
  for (const listener of listeners) {
    listener(request)
  }
}

export function subscribeThemeReveal(listener: Listener): () => void {
  listeners.add(listener)
  return () => {
    listeners.delete(listener)
  }
}
