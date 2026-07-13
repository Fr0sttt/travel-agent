import { isValidElement, useEffect, useMemo, useRef, useState, type ReactNode } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { Download, Eye, FileEdit, FileText, Loader2, LockKeyhole, RotateCcw, X } from 'lucide-react'

type HeadingItem = {
  id: string
  label: string
}

const markdownUrl = `${import.meta.env.BASE_URL}how-it-works.md`
const editPasswordHash = import.meta.env.VITE_HOW_IT_WORKS_EDIT_PASSWORD_HASH
  || '35729e599293e76e7efe33ff652c6ba13cba1b40464fb509718a7cffb409b81d'
let diagramSequence = 0

async function sha256(value: string) {
  const data = new TextEncoder().encode(value)
  const digest = await crypto.subtle.digest('SHA-256', data)
  return Array.from(new Uint8Array(digest), (byte) => byte.toString(16).padStart(2, '0')).join('')
}

function MermaidBlock({ chart }: { chart: string }) {
  const containerRef = useRef<HTMLDivElement>(null)
  const diagramId = useRef(`how-it-works-diagram-${++diagramSequence}`)
  const [error, setError] = useState('')

  useEffect(() => {
    let cancelled = false

    async function renderDiagram() {
      try {
        setError('')
        const { default: mermaid } = await import('mermaid')
        mermaid.initialize({
          startOnLoad: false,
          securityLevel: 'strict',
          theme: 'base',
          themeVariables: {
            primaryColor: '#F4F9FD',
            primaryTextColor: '#0A2463',
            primaryBorderColor: '#8ECAE6',
            lineColor: '#5B7083',
            secondaryColor: '#FFFFFF',
            tertiaryColor: '#EDF6F9',
            fontFamily: 'Inter, Noto Sans SC, sans-serif',
          },
        })
        const { svg } = await mermaid.render(diagramId.current, chart)
        if (!cancelled && containerRef.current) {
          containerRef.current.innerHTML = svg
        }
      } catch {
        if (!cancelled) {
          setError('架构图渲染失败，请检查 Mermaid 语法')
        }
      }
    }

    void renderDiagram()
    return () => {
      cancelled = true
    }
  }, [chart])

  return (
    <div className="my-6 overflow-x-auto rounded-2xl border border-[#D7E7F3] bg-[#FBFDFF] p-4">
      <div ref={containerRef} className="min-w-[720px] [&_svg]:mx-auto [&_svg]:max-w-full" />
      {error && <p className="text-sm text-[#8B2E2E]">{error}</p>}
    </div>
  )
}

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
  const [editingMarkdown, setEditingMarkdown] = useState('')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [isEditing, setIsEditing] = useState(false)
  const [passwordDialogOpen, setPasswordDialogOpen] = useState(false)
  const [password, setPassword] = useState('')
  const [passwordError, setPasswordError] = useState('')
  const [isCheckingPassword, setIsCheckingPassword] = useState(false)

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

  const displayMarkdown = isEditing ? editingMarkdown : markdown
  const headings = useMemo(() => extractHeadings(displayMarkdown), [displayMarkdown])

  function openPasswordDialog() {
    setPassword('')
    setPasswordError('')
    setPasswordDialogOpen(true)
  }

  function closePasswordDialog() {
    if (isCheckingPassword) return
    setPasswordDialogOpen(false)
    setPassword('')
    setPasswordError('')
  }

  async function unlockEditor() {
    if (!password) {
      setPasswordError('请输入编辑密码')
      return
    }

    setIsCheckingPassword(true)
    try {
      const isValid = (await sha256(password)) === editPasswordHash
      if (!isValid) {
        setPasswordError('密码不正确')
        return
      }

      setEditingMarkdown(markdown)
      setIsEditing(true)
      closePasswordDialog()
    } catch {
      setPasswordError('当前浏览器不支持密码校验，请换用 HTTPS 或现代浏览器')
    } finally {
      setIsCheckingPassword(false)
    }
  }

  function downloadMarkdown() {
    const blob = new Blob([editingMarkdown], { type: 'text/markdown;charset=utf-8' })
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = 'how-it-works.md'
    document.body.appendChild(link)
    link.click()
    link.remove()
    URL.revokeObjectURL(url)
  }

  function resetEditingMarkdown() {
    setEditingMarkdown(markdown)
  }

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
    code: ({ children, className }: { children?: ReactNode; className?: string }) => {
      if (className?.includes('language-mermaid')) {
        return <MermaidBlock chart={String(children).replace(/\n$/, '')} />
      }
      return <code className="rounded bg-[#EEF5FB] px-1.5 py-0.5 font-mono text-[0.85em] text-[#0A2463]">{children}</code>
    },
    pre: ({ children }: { children?: ReactNode }) => {
      if (isValidElement(children) && children.type === MermaidBlock) {
        return children
      }
      return <pre className="overflow-x-auto rounded-xl bg-[#0B1F33] p-4 text-sm leading-7 text-white mb-4">{children}</pre>
    },
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

  const hasContent = Boolean(displayMarkdown.trim())

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
                按功能、架构、执行流程、数据来源与安全设计梳理 WanderMind 的核心实现。
              </p>
            </div>

            <button
              type="button"
              onClick={isEditing ? () => setIsEditing(false) : openPasswordDialog}
              className="inline-flex items-center gap-2 rounded-full border border-[#D7E7F3] bg-white px-4 py-2 text-sm font-medium text-[#0A2463] hover:border-[#1A659E] hover:text-[#1A659E] transition-colors"
            >
              {isEditing ? <Eye className="w-4 h-4" /> : <FileEdit className="w-4 h-4" />}
              {isEditing ? '退出编辑' : '编辑文档'}
            </button>
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
            {isEditing && (
              <div className="mb-6 rounded-xl border border-[#CBE4F4] bg-[#F4F9FD] p-4">
                <div className="flex flex-wrap items-center justify-between gap-3 mb-3">
                  <div>
                    <p className="text-sm font-semibold text-[#0A2463]">Markdown 编辑模式</p>
                    <p className="mt-1 text-xs leading-6 text-[#5B7083]">
                      修改后可下载为 `how-it-works.md`，替换仓库中的同名文件并重新部署。
                    </p>
                  </div>
                  <div className="flex flex-wrap gap-2">
                    <button
                      type="button"
                      onClick={resetEditingMarkdown}
                      className="inline-flex items-center gap-2 rounded-lg border border-[#D7E7F3] bg-white px-3 py-2 text-xs font-medium text-[#0A2463] hover:border-[#1A659E] transition-colors"
                    >
                      <RotateCcw className="w-3.5 h-3.5" />
                      恢复线上版本
                    </button>
                    <button
                      type="button"
                      onClick={downloadMarkdown}
                      className="inline-flex items-center gap-2 rounded-lg bg-[#0A2463] px-3 py-2 text-xs font-medium text-white hover:bg-[#1A659E] transition-colors"
                    >
                      <Download className="w-3.5 h-3.5" />
                      下载 Markdown
                    </button>
                  </div>
                </div>
                <textarea
                  value={editingMarkdown}
                  onChange={(event) => setEditingMarkdown(event.target.value)}
                  spellCheck={false}
                  aria-label="Markdown 文档编辑器"
                  className="min-h-[680px] w-full resize-y rounded-lg border border-[#D7E7F3] bg-[#0B1F33] p-4 font-mono text-sm leading-7 text-white outline-none ring-[#8ECAE6] focus:ring-2"
                />
              </div>
            )}

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
                  {displayMarkdown}
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

      {passwordDialogOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-[#0B1F33]/45 px-6" role="presentation" onMouseDown={closePasswordDialog}>
          <div
            role="dialog"
            aria-modal="true"
            aria-labelledby="edit-password-title"
            className="w-full max-w-md rounded-2xl border border-[#D7E7F3] bg-white p-6 shadow-2xl"
            onMouseDown={(event) => event.stopPropagation()}
          >
            <div className="flex items-start justify-between gap-4">
              <div>
                <div className="mb-3 flex h-10 w-10 items-center justify-center rounded-xl bg-[#F4F9FD] text-[#1A659E]">
                  <LockKeyhole className="h-5 w-5" />
                </div>
                <h2 id="edit-password-title" className="text-xl font-semibold text-[#0A2463]">解锁文档编辑</h2>
                <p className="mt-2 text-sm leading-6 text-[#5B7083]">编辑结果会在浏览器中预览，并可下载成新的 Markdown 文件。</p>
              </div>
              <button type="button" onClick={closePasswordDialog} aria-label="关闭" className="rounded-lg p-2 text-[#5B7083] hover:bg-[#F4F9FD] hover:text-[#0A2463]">
                <X className="h-5 w-5" />
              </button>
            </div>
            <form
              className="mt-6"
              onSubmit={(event) => {
                event.preventDefault()
                void unlockEditor()
              }}
            >
              <label htmlFor="edit-password" className="mb-2 block text-sm font-medium text-[#0A2463]">编辑密码</label>
              <input
                id="edit-password"
                type="password"
                value={password}
                onChange={(event) => {
                  setPassword(event.target.value)
                  setPasswordError('')
                }}
                autoFocus
                autoComplete="current-password"
                className="w-full rounded-lg border border-[#D7E7F3] px-3 py-2.5 text-sm text-[#0A2463] outline-none ring-[#8ECAE6] focus:ring-2"
                placeholder="请输入密码"
              />
              {passwordError && <p className="mt-2 text-sm text-[#8B2E2E]">{passwordError}</p>}
              <button type="submit" disabled={isCheckingPassword} className="mt-5 inline-flex w-full items-center justify-center gap-2 rounded-lg bg-[#0A2463] px-4 py-2.5 text-sm font-medium text-white hover:bg-[#1A659E] disabled:cursor-not-allowed disabled:opacity-60">
                {isCheckingPassword && <Loader2 className="h-4 w-4 animate-spin" />}
                解锁并编辑
              </button>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}
