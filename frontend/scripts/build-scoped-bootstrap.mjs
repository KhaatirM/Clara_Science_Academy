import fs from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const __dirname = path.dirname(fileURLToPath(import.meta.url))
const scope = 'legacy-mgmt-bootstrap'

function stripCssComments(css) {
  return css.replace(/\/\*[\s\S]*?\*\//g, '').replace(/^@charset[^;]+;/i, '')
}

/** Prefix a stylesheet so rules only apply under `.scope`. */
function scopeBootstrapCss(css, scopeName) {
  const prefix = `.${scopeName}`
  const chunks = []
  let i = 0

  while (i < css.length) {
    const open = css.indexOf('{', i)
    if (open === -1) {
      chunks.push(css.slice(i))
      break
    }

    const selector = css.slice(i, open).trim()
    let depth = 1
    let j = open + 1
    while (j < css.length && depth > 0) {
      if (css[j] === '{') depth += 1
      else if (css[j] === '}') depth -= 1
      j += 1
    }

    const content = css.slice(open + 1, j - 1)

    if (selector.startsWith('@')) {
      if (/^@(media|supports|container|layer)\b/.test(selector)) {
        chunks.push(`${selector}{${scopeBootstrapCss(content, scopeName)}}`)
      } else {
        chunks.push(`${selector}{${content}}`)
      }
    } else {
      const scoped = selector
        .split(',')
        .map((part) => {
          const sel = part.trim()
          if (!sel) return sel
          if (sel === ':root' || sel === 'html' || sel === 'body') return prefix
          if (sel.startsWith(prefix)) return sel
          if (sel.startsWith('[data-bs-theme')) return `${prefix}${sel}`
          return `${prefix} ${sel}`
        })
        .join(', ')
      chunks.push(`${scoped}{${content}}`)
    }

    i = j
  }

  return chunks.join('')
}

const out = path.join(__dirname, '../../static/css/bootstrap-scoped.css')

const sourcePaths = [
  path.join(__dirname, '../node_modules/bootstrap/dist/css/bootstrap.min.css'),
  path.join(__dirname, '../../static/css/bootstrap.min.css'),
]

const source = sourcePaths.find((p) => fs.existsSync(p))
if (!source) {
  if (fs.existsSync(out)) {
    console.log(`bootstrap source missing; keeping existing ${out}`)
    process.exit(0)
  }
  throw new Error(`Bootstrap source not found. Run: npm install && npm run build:scoped-bootstrap`)
}

const css = stripCssComments(fs.readFileSync(source, 'utf8'))
const scoped = `@charset "UTF-8";${scopeBootstrapCss(css, scope)}`
fs.writeFileSync(out, scoped, 'utf8')
console.log(`Wrote ${out} (${scoped.length} bytes, scoped under .${scope})`)
