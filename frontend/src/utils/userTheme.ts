const THEME_CLASS_PREFIX = 'theme-'

export const VALID_THEMES = new Set([
  'default',
  'light',
  'dark',
  'snowy',
  'autumn',
  'spring',
  'summer',
  'holiday',
  'ocean',
  'forest',
  'sunset',
  'midnight',
  'desert',
  'lavender',
  'rose',
  'cherry',
  'aurora',
  'storm',
  'wine',
  'mint',
])

export function normalizeTheme(theme: string | null | undefined): string {
  const value = (theme || 'default').trim().toLowerCase()
  return VALID_THEMES.has(value) ? value : 'default'
}

/** Apply site theme to the document (matches legacy ``body.theme-*`` classes). */
export function applyUserTheme(theme: string | null | undefined): string {
  const normalized = normalizeTheme(theme)
  const { body, documentElement } = document

  for (const className of [...body.classList]) {
    if (className.startsWith(THEME_CLASS_PREFIX)) {
      body.classList.remove(className)
    }
  }

  body.classList.add(`${THEME_CLASS_PREFIX}${normalized}`)
  documentElement.removeAttribute('data-theme')
  documentElement.setAttribute('data-spa-theme', normalized)
  return normalized
}
