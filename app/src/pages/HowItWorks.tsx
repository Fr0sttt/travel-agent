import { useEffect, useMemo, useState, type ReactNode } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { ArrowRight, FileText, Loader2 } from 'lucide-react'

type HeadingItem = {
  id: string
  label: string
}

const markdownUrl = `${import.meta.env.BASE_URL}how-it-works.md`

function slugifyHeading(text: string) {
  const normalized = text
    .trim()
    .toLowerCase()
    .replace(/[^\p{L}\p{N}\s-]/gu, '')
    .replace(/\s+/g, '-')
    .replace(/-+/g, '-')
  return normalized || 'section'
}

function extractHeadings(markdown: string): HeadingItem[] {
  const headings: HeadingItem[] = []
  const seen = new Map<string, number>()
  const lines = markdown.split('\n')

  for (const line of lines) {
    const match = /^(#{1,3})\s+(.+?)\s*$/.exec(line)
    if (!match) continue

    const level = match[1].length
    const label = match[2].replace(/\s+/g, ' ').trim()
    if (level === 1) continue

    const base = slugifyHeading(label)
    const count = (seen.get(base) ?? 0) + 1
    seen.set(base, count)
    const id = count === 1 ? base : `${base}-${count}`

    headings.push({ id, label })
  }

  return headings
}

export default function HowItWorks() {
  const [markdown, setMarkdown] = useState('')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    let ignore = false

    async function loadMarkdown() {
      try {
        setLoading(true)
        setError('')
        const response = await fetch(markdownUrl, { cache: 'no-store' })
        if (!response.ok) {
          throw new Error(`无法加载源文档：${response.status}`)
        }
        const text = await response.text()
        if (!ignore) {
          setMarkdown(text)
        }
      } catch (err) {
        if (!ignore) {
          setError(err instanceof Error ? err.message : '无法加载源文档')
        }
      } finally {
        if (!ignore) {
          setLoading(false)
        }
      }
    }

    loadMarkdown()
    return () => {
      ignore = true
    }
  }, [])

  const headings = useMemo(() => extractHeadings(markdown), [markdown])

  let headingCursor = 0
  const components = {
    h1: ({ children }: { children?: ReactNode }) => (
      <h1 className="text-3xl font-bold tracking-tight text-[#0A2463] mt-2 mb-6">{children}</h1>
    ),
    h2: ({ children }: { children?: React.ReactNode }) => {
      const item = headings[headingCursor++] ?? { id: `section-${headingCursor}`, label: '' }
      return (
        <h2 id={item.id} className="scroll-mt-24 text-2xl font-semibold tracking-tight text-[#0A2463] mt-10 mb-4">
          {children}
        </h2>
      )
    },
    h3: ({ children }: { children?: ReactNode }) => {
      const item = headings[headingCursor++] ?? { id: `section-${headingCursor}`, label: '' }
      return (
        <h3 id={item.id} className="scroll-mt-24 text-lg font-semibold text-[#0A2463] mt-6 mb-3">
          {children}
        </h3>
      )
    },
    p: ({ children }: { children?: ReactNode }) => (
      <p className="text-sm leading-8 text-[#27415C] mb-4">{children}</p>
    ),
    ul: ({ children }: { children?: ReactNode }) => (
      <ul className="list-disc space-y-2 pl-5 text-sm leading-8 text-[#27415C] mb-4">{children}</ul>
    ),
    ol: ({ children }: { children?: ReactNode }) => (
      <ol className="list-decimal space-y-2 pl-5 text-sm leading-8 text-[#27415C] mb-4">{children}</ol>
    ),
    li: ({ children }: { children?: ReactNode }) => <li>{children}</li>,
    blockquote: ({ children }: { children?: ReactNode }) => (
      <blockquote className="border-l-4 border-[#1A659E] bg-[#F4F9FD] px-4 py-3 text-sm leading-8 text-[#24415D] mb-4">
        {children}
      </blockquote>
    ),
    code: ({ children }: { children?: ReactNode }) => (
      <code className="rounded bg-[#EEF5FB] px-1.5 py-0.5 font-mono text-[0.85em] text-[#0A2463]">{children}</code>
    ),
    pre: ({ children }: { children?: ReactNode }) => (
      <pre className="overflow-x-auto rounded-xl bg-[#0B1F33] p-4 text-sm leading-7 text-white mb-4">{children}</pre>
    ),
    table: ({ children }: { children?: ReactNode }) => (
      <div className="overflow-x-auto mb-4">
        <table className="w-full border-collapse text-sm text-[#27415C]">{children}</table>
      </div>
    ),
    th: ({ children }: { children?: ReactNode }) => (
      <th className="border-b border-[#D7E7F3] px-3 py-2 text-left font-semibold text-[#0A2463]">{children}</th>
    ),
    td: ({ children }: { children?: ReactNode }) => (
      <td className="border-b border-[#E6EEF6] px-3 py-2 align-top">{children}</td>
    ),
    a: ({ children, href }: { children?: ReactNode; href?: string }) => (
      <a href={href} className="text-[#1A659E] underline decoration-[#9AC7E5] underline-offset-4">
        {children}
      </a>
    ),
  }

  const hasContent = Boolean(markdown.trim())

  return (
    <div className="min-h-[calc(100dvh-64px)] bg-[#F7FAFF] text-[#0A2463]">
      <div className="max-w-[1280px] mx-auto px-6 py-10 lg:py-14">
        <div className="max-w-4xl mb-10">
          <div className="inline-flex items-center gap-2 rounded-full px-3 py-1 text-xs font-medium mb-4" style={{ background: 'rgba(33,158,188,0.12)', color: '#1A659E' }}>
            <FileText className="w-3.5 h-3.5" />
            技术文档
          </div>
          <div className="flex flex-wrap items-center gap-3 justify-between">
            <div>
              <h1 className="text-4xl font-bold tracking-tight mb-4" style={{ fontFamily: "'Outfit Variable', Outfit, sans-serif" }}>
                WanderMind 旅行代理项目技术文档
              </h1>
              <p className="text-base leading-8 max-w-3xl" style={{ color: 'rgba(10,36,99,0.78)', fontFamily: "'Inter Variable', Inter, sans-serif" }}>
                这页直接读取 `app/public/how-it-works.md` 并渲染。你以后只要改那份 md，页面内容就会跟着更新。
              </p>
            </div>

            <a
              href={markdownUrl}
              target="_blank"
              rel="noreferrer"
              className="inline-flex items-center gap-2 rounded-full border border-[#D7E7F3] bg-white px-4 py-2 text-sm font-medium text-[#0A2463] hover:border-[#1A659E] hover:text-[#1A659E] transition-colors"
            >
              源文档
              <ArrowRight className="w-4 h-4" />
            </a>
          </div>
        </div>

        <div className="grid lg:grid-cols-[240px_minmax(0,1fr)] gap-6">
          <aside className="lg:sticky lg:top-20 self-start rounded-2xl border border-[#D7E7F3] bg-white p-5 shadow-[0_12px_40px_rgba(10,36,99,0.05)]">
            <p className="text-xs font-semibold uppercase tracking-wider mb-4" style={{ color: 'rgba(10,36,99,0.5)' }}>
              目录
            </p>
            <nav className="space-y-2">
              {headings.length > 0 ? (
                headings.map((item, index) => (
                  <a
                    key={`${item.id}-${index}`}
                    href={`#${item.id}`}
                    className="block text-sm leading-6 hover:text-[#1A659E] transition-colors"
                    style={{ color: 'rgba(10,36,99,0.82)' }}
                  >
                    {item.label}
                  </a>
                ))
              ) : (
                <div className="text-sm text-[#5B7083]">源文档加载后会自动生成目录</div>
              )}
            </nav>
          </aside>

          <main className="rounded-2xl border border-[#D7E7F3] bg-white p-6 shadow-[0_12px_40px_rgba(10,36,99,0.05)]">
            {loading ? (
              <div className="min-h-[360px] flex items-center justify-center text-[#5B7083]">
                <Loader2 className="w-5 h-5 mr-2 animate-spin" />
                正在加载源文档
              </div>
            ) : error ? (
              <div className="rounded-xl border border-[#E9B7B7] bg-[#FFF6F6] p-4 text-sm leading-7 text-[#8B2E2E]">
                {error}
              </div>
            ) : hasContent ? (
              <article className="max-w-none">
                <ReactMarkdown remarkPlugins={[remarkGfm]} components={components}>
                  {markdown}
                </ReactMarkdown>
              </article>
            ) : (
              <div className="min-h-[240px] flex items-center justify-center text-[#5B7083]">
                源文档为空
              </div>
            )}
          </main>
        </div>

      </div>
    </div>
  )
}
