export type PrintableDocument = {
  name: string
  is_pdf?: boolean
  is_image?: boolean
  view_url: string
  download_url: string
}

export type PrintPrepResult = {
  printable: PrintableDocument[]
  skipped: PrintableDocument[]
}

function nameLooksPdf(name: string) {
  return name.toLowerCase().endsWith('.pdf')
}

function nameLooksImage(name: string) {
  return /\.(png|jpe?g|gif|webp)$/i.test(name)
}

export function isPrintableDocument(doc: PrintableDocument) {
  return Boolean(doc.is_pdf || doc.is_image || nameLooksPdf(doc.name) || nameLooksImage(doc.name))
}

export function splitPrintableDocuments(docs: PrintableDocument[]): PrintPrepResult {
  const seen = new Set<string>()
  const printable: PrintableDocument[] = []
  const skipped: PrintableDocument[] = []
  for (const doc of docs) {
    const key = doc.download_url || doc.view_url || doc.name
    if (seen.has(key)) continue
    seen.add(key)
    if (isPrintableDocument(doc)) printable.push(doc)
    else skipped.push(doc)
  }
  return { printable, skipped }
}

/** Open immediately inside the click handler so the browser allows the popup. */
export function beginPrintSession(): Window | null {
  const win = window.open('', '_blank')
  if (!win) return null
  win.document.open()
  win.document.write(
    '<!doctype html><title>Preparing print…</title><body style="font-family:system-ui,sans-serif;padding:2rem;color:#334155">Preparing documents to print…</body>',
  )
  win.document.close()
  return win
}

async function fetchBytes(url: string): Promise<Uint8Array> {
  const response = await fetch(url, { credentials: 'same-origin', cache: 'no-store' })
  if (!response.ok) {
    throw new Error(`Could not load a document (${response.status}).`)
  }
  return new Uint8Array(await response.arrayBuffer())
}

function looksLikePdf(bytes: Uint8Array) {
  return bytes.length >= 4 && bytes[0] === 0x25 && bytes[1] === 0x50 && bytes[2] === 0x44 && bytes[3] === 0x46
}

function writePrintWindow(win: Window, blobUrl: string, title: string) {
  const safeTitle = title.replace(/[<>&"]/g, '')
  win.document.open()
  win.document.write(`<!doctype html>
<html>
<head>
  <meta charset="utf-8" />
  <title>${safeTitle}</title>
  <style>
    html, body { margin: 0; height: 100%; background: #f8fafc; }
    embed { width: 100%; height: 100vh; border: 0; }
    .bar { position: fixed; top: 12px; right: 12px; z-index: 2; }
    .bar button {
      border: 0; border-radius: 999px; background: #0f766e; color: white;
      font: 600 14px system-ui, sans-serif; padding: 8px 14px; cursor: pointer;
    }
    @media print { .bar { display: none; } }
  </style>
</head>
<body>
  <div class="bar"><button type="button" onclick="window.print()">Print</button></div>
  <embed src="${blobUrl}" type="application/pdf" />
  <script>
    setTimeout(function () {
      try { window.focus(); window.print(); } catch (e) {}
    }, 700);
  </script>
</body>
</html>`)
  win.document.close()
}

export async function finishPrintSession(win: Window, docs: PrintableDocument[]) {
  if (win.closed) return
  if (!docs.length) {
    win.close()
    throw new Error('Nothing to print.')
  }
  const { PDFDocument } = await import('pdf-lib')
  const merged = await PDFDocument.create()
  const failures: string[] = []

  for (const doc of docs) {
    try {
      const bytes = await fetchBytes(doc.download_url || doc.view_url)
      const pdf = doc.is_pdf || nameLooksPdf(doc.name) || looksLikePdf(bytes)
      if (pdf) {
        const src = await PDFDocument.load(bytes, { ignoreEncryption: true })
        const pages = await merged.copyPages(src, src.getPageIndices())
        pages.forEach((page) => merged.addPage(page))
        continue
      }
      const lower = doc.name.toLowerCase()
      const image = lower.endsWith('.png') ? await merged.embedPng(bytes) : await merged.embedJpg(bytes)
      const maxW = 612
      const maxH = 792
      const scale = Math.min(maxW / image.width, maxH / image.height, 1)
      const width = image.width * scale
      const height = image.height * scale
      const page = merged.addPage([maxW, maxH])
      page.drawImage(image, {
        x: (maxW - width) / 2,
        y: (maxH - height) / 2,
        width,
        height,
      })
    } catch {
      failures.push(doc.name)
    }
  }

  if (merged.getPageCount() === 0) {
    win.close()
    throw new Error(
      failures.length
        ? `Could not print ${failures.join(', ')}. Download those files instead.`
        : 'Could not prepare documents to print.',
    )
  }

  const saved = await merged.save()
  const copy = new Uint8Array(saved.byteLength)
  copy.set(saved)
  const blobUrl = URL.createObjectURL(new Blob([copy], { type: 'application/pdf' }))
  if (win.closed) {
    URL.revokeObjectURL(blobUrl)
    return
  }
  writePrintWindow(win, blobUrl, docs.length === 1 ? docs[0].name : 'Assignment documents')
  window.setTimeout(() => URL.revokeObjectURL(blobUrl), 120000)
  if (failures.length) {
    throw new Error(`Printed most files. Could not include: ${failures.join(', ')}.`)
  }
}
