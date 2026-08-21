import { useEffect, useRef, useState, type FormEvent } from 'react'
import { Bot, Info, Send, Sparkles, Trash2, User } from 'lucide-react'
import { Alert, Badge, Card, CardHeader, Spinner } from '../components/ui'
import { useToast } from '../context/ToastContext'
import { describeError } from '../services/api'
import { assistantApi } from '../services/endpoints'
import { relativeTime } from '../utils/format'
import type { ChatMessage, ChatResponse } from '../types'

const CONFIDENCE_TONE: Record<string, string> = {
  high: 'border-cane-300 bg-cane-100 text-cane-900 dark:border-cane-800 dark:bg-cane-950 dark:text-cane-200',
  medium:
    'border-sky-300 bg-sky-100 text-sky-900 dark:border-sky-800 dark:bg-sky-950 dark:text-sky-200',
  low: 'border-amber-300 bg-amber-100 text-amber-900 dark:border-amber-800 dark:bg-amber-950 dark:text-amber-200',
}

/**
 * Minimal markdown renderer for the assistant's replies.
 * The backend only emits **bold**, *italic*, bullet lists and numbered lists,
 * so a full markdown dependency would be overkill here.
 */
function RichText({ text }: { text: string }) {
  const inline = (line: string) => {
    const parts = line.split(/(\*\*[^*]+\*\*|\*[^*]+\*)/g)
    return parts.map((part, index) => {
      if (part.startsWith('**') && part.endsWith('**')) {
        return (
          <strong key={index} className="font-semibold text-slate-900 dark:text-white">
            {part.slice(2, -2)}
          </strong>
        )
      }
      if (part.startsWith('*') && part.endsWith('*') && part.length > 2) {
        return (
          <em key={index} className="text-slate-500 dark:text-slate-400">
            {part.slice(1, -1)}
          </em>
        )
      }
      return <span key={index}>{part}</span>
    })
  }

  const blocks: React.ReactNode[] = []
  let list: string[] = []
  let ordered = false

  const flush = () => {
    if (list.length === 0) return
    const Tag = ordered ? 'ol' : 'ul'
    blocks.push(
      <Tag
        key={`list-${blocks.length}`}
        className={`my-2 space-y-1.5 pl-5 ${ordered ? 'list-decimal' : 'list-disc'}`}
      >
        {list.map((item, index) => (
          <li key={index}>{inline(item)}</li>
        ))}
      </Tag>,
    )
    list = []
  }

  text.split('\n').forEach((rawLine, index) => {
    const line = rawLine.trimEnd()
    const bullet = line.match(/^\s*-\s+(.*)$/)
    const numbered = line.match(/^\s*\d+\.\s+(.*)$/)

    if (bullet) {
      if (ordered) flush()
      ordered = false
      list.push(bullet[1])
      return
    }
    if (numbered) {
      if (!ordered) flush()
      ordered = true
      list.push(numbered[1])
      return
    }
    flush()
    if (line.trim() === '') return
    blocks.push(
      <p key={`p-${index}`} className="my-1.5 leading-relaxed">
        {inline(line)}
      </p>,
    )
  })
  flush()

  return <div className="text-sm">{blocks}</div>
}

export default function Assistant() {
  const toast = useToast()
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [input, setInput] = useState('')
  const [sending, setSending] = useState(false)
  const [lastResponse, setLastResponse] = useState<ChatResponse | null>(null)
  const [suggestions, setSuggestions] = useState<string[]>([
    'When should I irrigate my sugarcane?',
    'Why are my leaves turning yellow?',
    'Which variety is suitable for my soil?',
    'How can I improve an infected plant?',
    'What fertilizer should I consider?',
    'How can I save water?',
    'What does low soil moisture mean?',
  ])
  const scrollRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    assistantApi
      .history(60)
      .then(setMessages)
      .catch(() => setMessages([]))
  }, [])

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: 'smooth' })
  }, [messages, sending])

  const send = async (text: string) => {
    const message = text.trim()
    if (!message || sending) return

    const optimistic: ChatMessage = {
      id: Date.now(),
      role: 'user',
      content: message,
      created_at: new Date().toISOString(),
    }
    setMessages((current) => [...current, optimistic])
    setInput('')
    setSending(true)

    try {
      const response = await assistantApi.chat(message)
      setLastResponse(response)
      if (response.suggested_questions?.length) setSuggestions(response.suggested_questions)
      setMessages((current) => [
        ...current,
        {
          id: Date.now() + 1,
          role: 'assistant',
          content: response.reply,
          topic: response.topic,
          created_at: response.created_at,
        },
      ])
    } catch (caught) {
      toast.error('The assistant could not reply', describeError(caught))
      setMessages((current) => current.filter((item) => item.id !== optimistic.id))
      setInput(message)
    } finally {
      setSending(false)
    }
  }

  const handleSubmit = (event: FormEvent) => {
    event.preventDefault()
    void send(input)
  }

  const handleClear = async () => {
    try {
      await assistantApi.clear()
      setMessages([])
      setLastResponse(null)
      toast.success('Chat cleared')
    } catch (caught) {
      toast.error('Could not clear the chat', describeError(caught))
    }
  }

  return (
    <div className="space-y-6">
      <div>
        <h2 className="font-display text-2xl font-extrabold">Sugarcane Assistant</h2>
        <p className="mt-1 text-slate-600 dark:text-slate-400">
          Ask about irrigation, disease, soil, varieties or fertilizer. Answers use your own saved
          analyses where they exist.
        </p>
      </div>

      <Alert tone="info" title="What this assistant is" icon={Info}>
        A <strong>rule-based assistant</strong>, not a large language model. It matches your question
        to a topic and answers from your saved records plus the project's knowledge base. It will tell
        you when it is unsure rather than inventing an answer, and it is not a substitute for a
        qualified agricultural officer. English only for now; Kannada and Hindi are planned.
      </Alert>

      <div className="grid gap-6 lg:grid-cols-[1fr_300px]">
        <Card className="flex h-[600px] flex-col">
          <CardHeader
            title="Chat"
            subtitle={`${messages.length} message${messages.length === 1 ? '' : 's'}`}
            icon={Bot}
            action={
              messages.length > 0 ? (
                <button
                  type="button"
                  onClick={handleClear}
                  className="btn-ghost shrink-0 px-3 py-1.5 text-xs text-red-600 hover:bg-red-50 dark:hover:bg-red-950"
                >
                  <Trash2 className="size-3.5" />
                  Clear
                </button>
              ) : undefined
            }
          />

          <div ref={scrollRef} className="scrollbar-thin flex-1 space-y-4 overflow-y-auto p-5">
            {messages.length === 0 && (
              <div className="grid h-full place-items-center text-center">
                <div>
                  <span className="mx-auto grid size-14 place-items-center rounded-2xl bg-amber-100 text-amber-600 dark:bg-amber-950 dark:text-amber-400">
                    <Bot className="size-7" />
                  </span>
                  <h3 className="mt-4 text-base font-bold">Ask me about your crop</h3>
                  <p className="mx-auto mt-2 max-w-sm text-sm text-slate-500 dark:text-slate-400">
                    Try one of the suggested questions, or type your own. I work best after you have
                    run an irrigation check or uploaded a photo.
                  </p>
                </div>
              </div>
            )}

            {messages.map((message) => (
              <div
                key={message.id}
                className={`flex gap-3 ${message.role === 'user' ? 'flex-row-reverse' : ''}`}
              >
                <span
                  className={`grid size-8 shrink-0 place-items-center rounded-lg ${
                    message.role === 'user'
                      ? 'bg-cane-600 text-white'
                      : 'bg-amber-100 text-amber-700 dark:bg-amber-950 dark:text-amber-400'
                  }`}
                >
                  {message.role === 'user' ? <User className="size-4" /> : <Bot className="size-4" />}
                </span>
                <div
                  className={`max-w-[80%] rounded-2xl px-4 py-3 ${
                    message.role === 'user'
                      ? 'bg-cane-600 text-white'
                      : 'bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-300'
                  }`}
                >
                  {message.role === 'user' ? (
                    <p className="text-sm leading-relaxed">{message.content}</p>
                  ) : (
                    <RichText text={message.content} />
                  )}
                  <p
                    className={`mt-1.5 text-[11px] ${
                      message.role === 'user' ? 'text-cane-100' : 'text-slate-400'
                    }`}
                  >
                    {relativeTime(message.created_at)}
                  </p>
                </div>
              </div>
            ))}

            {sending && (
              <div className="flex gap-3">
                <span className="grid size-8 shrink-0 place-items-center rounded-lg bg-amber-100 text-amber-700 dark:bg-amber-950 dark:text-amber-400">
                  <Bot className="size-4" />
                </span>
                <div className="rounded-2xl bg-slate-100 px-4 py-3 dark:bg-slate-800">
                  <span className="flex gap-1">
                    {[0, 1, 2].map((dot) => (
                      <span
                        key={dot}
                        className="size-2 animate-pulse rounded-full bg-slate-400"
                        style={{ animationDelay: `${dot * 0.15}s` }}
                      />
                    ))}
                  </span>
                </div>
              </div>
            )}
          </div>

          <form
            onSubmit={handleSubmit}
            className="flex gap-2 border-t border-slate-200 p-4 dark:border-slate-800"
          >
            <input
              className="input flex-1"
              placeholder="Ask about irrigation, disease, soil, varieties..."
              value={input}
              onChange={(event) => setInput(event.target.value)}
              disabled={sending}
              maxLength={2000}
            />
            <button type="submit" disabled={sending || !input.trim()} className="btn-primary px-4">
              {sending ? <Spinner className="size-4" /> : <Send className="size-4" />}
            </button>
          </form>
        </Card>

        <div className="space-y-6">
          <Card>
            <CardHeader title="Suggested questions" icon={Sparkles} />
            <div className="space-y-2 p-4">
              {suggestions.map((question) => (
                <button
                  key={question}
                  type="button"
                  onClick={() => void send(question)}
                  disabled={sending}
                  className="w-full rounded-xl border border-slate-200 px-3 py-2.5 text-left text-xs leading-relaxed text-slate-600 transition hover:border-cane-300 hover:bg-cane-50 disabled:opacity-50 dark:border-slate-800 dark:text-slate-400 dark:hover:border-cane-800 dark:hover:bg-cane-950/40"
                >
                  {question}
                </button>
              ))}
            </div>
          </Card>

          {lastResponse && (
            <Card>
              <CardHeader title="About that answer" icon={Info} />
              <div className="space-y-3 p-4 text-xs">
                <div className="flex items-center justify-between gap-2">
                  <span className="text-slate-500">Match confidence</span>
                  <Badge className={CONFIDENCE_TONE[lastResponse.confidence]}>
                    {lastResponse.confidence}
                  </Badge>
                </div>
                <div className="flex items-center justify-between gap-2">
                  <span className="text-slate-500">Topic</span>
                  <span className="font-medium">{lastResponse.topic.replace(/_/g, ' ')}</span>
                </div>

                {lastResponse.used_context.length > 0 && (
                  <div className="border-t border-slate-100 pt-3 dark:border-slate-800">
                    <p className="mb-2 font-semibold text-slate-600 dark:text-slate-400">
                      Records used
                    </p>
                    <ul className="space-y-2">
                      {lastResponse.used_context.map((source, index) => (
                        <li key={index}>
                          <p className="font-medium text-slate-700 dark:text-slate-300">
                            {source.label}
                          </p>
                          <p className="text-slate-500 dark:text-slate-400">{source.detail}</p>
                        </li>
                      ))}
                    </ul>
                  </div>
                )}

                <p className="border-t border-slate-100 pt-3 leading-relaxed text-slate-500 dark:border-slate-800 dark:text-slate-400">
                  {lastResponse.disclaimer}
                </p>
              </div>
            </Card>
          )}
        </div>
      </div>
    </div>
  )
}
