import { normalizeTheme } from './userTheme'

export type ThemeMotifKind =
  | 'wash'
  | 'snow'
  | 'leaf'
  | 'bloom'
  | 'sun'
  | 'ornament'
  | 'wave'
  | 'tree'
  | 'sunset'
  | 'star'
  | 'dune'
  | 'sprig'
  | 'petal'
  | 'cherry'
  | 'ribbon'
  | 'cloud'
  | 'grape'
  | 'mint'
  | 'coral'
  | 'gem'
  | 'hex'
  | 'shard'

export type ThemeRevealMeta = {
  id: string
  label: string
  tagline: string
  /** CSS gradient for the reveal wash */
  gradient: string
  /** Primary accent for progress / buttons */
  accent: string
  accentSoft: string
  motif: ThemeMotifKind
}

const META: Record<string, ThemeRevealMeta> = {
  default: {
    id: 'default',
    label: 'Default',
    tagline: "Clara's classic teal and indigo calm",
    gradient: 'linear-gradient(145deg, #0f766e 0%, #312e81 55%, #0f172a 100%)',
    accent: '#5eead4',
    accentSoft: 'rgba(94, 234, 212, 0.2)',
    motif: 'wash',
  },
  light: {
    id: 'light',
    label: 'Light',
    tagline: 'Clean daylight for everyday work',
    gradient: 'linear-gradient(145deg, #e2e8f0 0%, #94a3b8 45%, #64748b 100%)',
    accent: '#1e293b',
    accentSoft: 'rgba(30, 41, 59, 0.12)',
    motif: 'wash',
  },
  snowy: {
    id: 'snowy',
    label: 'Snowy (Winter)',
    tagline: 'Quiet winter light and soft snowfall',
    gradient: 'linear-gradient(145deg, #e0f2fe 0%, #7dd3fc 40%, #0369a1 100%)',
    accent: '#e0f2fe',
    accentSoft: 'rgba(224, 242, 254, 0.25)',
    motif: 'snow',
  },
  autumn: {
    id: 'autumn',
    label: 'Autumn',
    tagline: 'Warm leaves and harvest gold',
    gradient: 'linear-gradient(145deg, #fdba74 0%, #c2410c 50%, #7c2d12 100%)',
    accent: '#fed7aa',
    accentSoft: 'rgba(254, 215, 170, 0.22)',
    motif: 'leaf',
  },
  spring: {
    id: 'spring',
    label: 'Spring',
    tagline: 'Fresh blooms and new growth',
    gradient: 'linear-gradient(145deg, #fbcfe8 0%, #86efac 45%, #059669 100%)',
    accent: '#fce7f3',
    accentSoft: 'rgba(252, 231, 243, 0.25)',
    motif: 'bloom',
  },
  summer: {
    id: 'summer',
    label: 'Summer',
    tagline: 'Bright sun and coastal waves',
    gradient: 'linear-gradient(145deg, #fde68a 0%, #38bdf8 50%, #0284c7 100%)',
    accent: '#fef08a',
    accentSoft: 'rgba(254, 240, 138, 0.25)',
    motif: 'sun',
  },
  holiday: {
    id: 'holiday',
    label: 'Holiday',
    tagline: 'Festive red, green, and gold cheer',
    gradient: 'linear-gradient(145deg, #dc2626 0%, #166534 55%, #854d0e 100%)',
    accent: '#fbbf24',
    accentSoft: 'rgba(251, 191, 36, 0.22)',
    motif: 'ornament',
  },
  ocean: {
    id: 'ocean',
    label: 'Ocean',
    tagline: 'Cool coastal blues and deep water',
    gradient: 'linear-gradient(145deg, #7dd3fc 0%, #0284c7 50%, #0c4a6e 100%)',
    accent: '#bae6fd',
    accentSoft: 'rgba(186, 230, 253, 0.22)',
    motif: 'wave',
  },
  forest: {
    id: 'forest',
    label: 'Forest',
    tagline: 'Deep greens under a canopy of trees',
    gradient: 'linear-gradient(145deg, #86efac 0%, #15803d 50%, #14532d 100%)',
    accent: '#bbf7d0',
    accentSoft: 'rgba(187, 247, 208, 0.22)',
    motif: 'tree',
  },
  sunset: {
    id: 'sunset',
    label: 'Sunset',
    tagline: 'Orange skies fading into rose',
    gradient: 'linear-gradient(145deg, #fdba74 0%, #f43f5e 50%, #9f1239 100%)',
    accent: '#fecdd3',
    accentSoft: 'rgba(254, 205, 211, 0.22)',
    motif: 'sunset',
  },
  midnight: {
    id: 'midnight',
    label: 'Midnight',
    tagline: 'Starlit dark for late focus',
    gradient: 'linear-gradient(145deg, #334155 0%, #0f172a 55%, #020617 100%)',
    accent: '#e2e8f0',
    accentSoft: 'rgba(226, 232, 240, 0.18)',
    motif: 'star',
  },
  desert: {
    id: 'desert',
    label: 'Desert',
    tagline: 'Sun-baked dunes and warm sand',
    gradient: 'linear-gradient(145deg, #fcd34d 0%, #d97706 50%, #78350f 100%)',
    accent: '#fde68a',
    accentSoft: 'rgba(253, 230, 138, 0.22)',
    motif: 'dune',
  },
  lavender: {
    id: 'lavender',
    label: 'Lavender',
    tagline: 'Soft purple fields and quiet calm',
    gradient: 'linear-gradient(145deg, #ddd6fe 0%, #8b5cf6 50%, #4c1d95 100%)',
    accent: '#ede9fe',
    accentSoft: 'rgba(237, 233, 254, 0.22)',
    motif: 'sprig',
  },
  rose: {
    id: 'rose',
    label: 'Rose',
    tagline: 'Gentle petals in blush pink',
    gradient: 'linear-gradient(145deg, #fecdd3 0%, #f43f5e 50%, #9f1239 100%)',
    accent: '#ffe4e6',
    accentSoft: 'rgba(255, 228, 230, 0.22)',
    motif: 'petal',
  },
  cherry: {
    id: 'cherry',
    label: 'Cherry Blossom',
    tagline: 'Pink blossoms on soft spring air',
    gradient: 'linear-gradient(145deg, #fecdd3 0%, #fb7185 45%, #be123c 100%)',
    accent: '#ffe4e6',
    accentSoft: 'rgba(255, 228, 230, 0.22)',
    motif: 'cherry',
  },
  aurora: {
    id: 'aurora',
    label: 'Aurora',
    tagline: 'Northern lights in green and violet',
    gradient: 'linear-gradient(145deg, #6ee7b7 0%, #818cf8 50%, #312e81 100%)',
    accent: '#c7d2fe',
    accentSoft: 'rgba(199, 210, 254, 0.22)',
    motif: 'ribbon',
  },
  storm: {
    id: 'storm',
    label: 'Storm',
    tagline: 'Thunderclouds with a flash of lightning',
    gradient: 'linear-gradient(145deg, #94a3b8 0%, #475569 50%, #0f172a 100%)',
    accent: '#fbbf24',
    accentSoft: 'rgba(251, 191, 36, 0.2)',
    motif: 'cloud',
  },
  wine: {
    id: 'wine',
    label: 'Wine',
    tagline: 'Deep burgundy and vineyard dusk',
    gradient: 'linear-gradient(145deg, #fb7185 0%, #9f1239 50%, #4c0519 100%)',
    accent: '#fecdd3',
    accentSoft: 'rgba(254, 205, 211, 0.2)',
    motif: 'grape',
  },
  mint: {
    id: 'mint',
    label: 'Mint',
    tagline: 'Cool mint leaves and fresh air',
    gradient: 'linear-gradient(145deg, #99f6e4 0%, #2dd4bf 50%, #0f766e 100%)',
    accent: '#ccfbf1',
    accentSoft: 'rgba(204, 251, 241, 0.22)',
    motif: 'mint',
  },
  coral: {
    id: 'coral',
    label: 'Coral',
    tagline: 'Reef pinks and warm peach',
    gradient: 'linear-gradient(145deg, #fda4af 0%, #fb7185 45%, #ea580c 100%)',
    accent: '#ffe4e6',
    accentSoft: 'rgba(255, 228, 230, 0.22)',
    motif: 'coral',
  },
  sapphire: {
    id: 'sapphire',
    label: 'Sapphire',
    tagline: 'Faceted blues like deep gemstone',
    gradient: 'linear-gradient(145deg, #93c5fd 0%, #2563eb 50%, #1e3a8a 100%)',
    accent: '#dbeafe',
    accentSoft: 'rgba(219, 234, 254, 0.22)',
    motif: 'gem',
  },
  honey: {
    id: 'honey',
    label: 'Honey',
    tagline: 'Warm amber glow and honeycomb gold',
    gradient: 'linear-gradient(145deg, #fde68a 0%, #f59e0b 50%, #b45309 100%)',
    accent: '#fef3c7',
    accentSoft: 'rgba(254, 243, 199, 0.22)',
    motif: 'hex',
  },
  slate: {
    id: 'slate',
    label: 'Slate',
    tagline: 'Cool stone calm and steady focus',
    gradient: 'linear-gradient(145deg, #cbd5e1 0%, #64748b 50%, #334155 100%)',
    accent: '#e2e8f0',
    accentSoft: 'rgba(226, 232, 240, 0.2)',
    motif: 'shard',
  },
}

export function getThemeRevealMeta(theme: string | null | undefined): ThemeRevealMeta {
  const id = normalizeTheme(theme)
  return META[id] || META.default
}
