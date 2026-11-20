import { Fragment, useEffect, useRef, useState } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import { ArrowLeft, BookOpen, ExternalLink, History, Loader2, Plus, Scale, Send, X } from 'lucide-react'
import Layout from '../components/Layout'
import { api, clearToken, streamAdvisorChat } from '../api'

const SUGGESTED_QUESTIONS = [
  '안전관리자는 몇 명 이상 사업장부터 선임해야 하나요?',
  '위험성평가는 언제, 어떻게 실시해야 하나요?',
  '높이 2m 이상 작업 시 추락방지 조치는?',
  '밀폐공간 작업 전에 무엇을 해야 하나요?',
  '지게차 작업 시 지켜야 할 안전조치는?',
]

// 사진 분석 결과(context)를 가지고 들어왔을 때 보여줄 추천 질문
const CONTEXT_SUGGESTED_QUESTIONS = [
  '이 현장의 위험요소에 대해 사업주가 지켜야 할 법적 안전조치는 무엇인가요?',
  '이 작업 전에 근로자에게 실시해야 할 안전보건교육은 무엇인가요?',
  '이 현장에서 지급·착용해야 할 보호구는 무엇인가요?',
]

function citedNumbers(text, sources) {
  const numbers = new Set([...String(text).matchAll(/\[(\d+)\]/g)].map((match) => Number(match[1])))
  return sources.filter((source) => numbers.has(source.n)).map((source) => source.n)
}

// 조문 원문을 항(①②…) 단위로 줄바꿈
function formatArticleText(text) {
  return String(text ?? '').replace(/\s*([\u2460-\u2473])/g, '\n\n$1').trim()
}

function sourceTitle(source) {
  return `${source.law_title} ${source.article}`
}

// **굵게**, [n] 인용 배지만 처리하는 가벼운 렌더러
function InlineText({ text, sources, onCite }) {
  const parts = String(text).split(/(\*\*[^*]+\*\*|\[\d+\])/g)
  return parts.map((part, index) => {
    const bold = part.match(/^\*\*([^*]+)\*\*$/)
    if (bold) return <strong key={index} className="font-semibold text-slate-900">{bold[1]}</strong>

    const cite = part.match(/^\[(\d+)\]$/)
    if (cite) {
      const source = sources.find((item) => item.n === Number(cite[1]))
      if (!source) return null
      return (
        <button
          key={index}
          onClick={() => onCite(source)}
          className="inline-flex items-center justify-center min-w-5 h-5 px-1 mx-0.5 rounded-md bg-blue-100 text-blue-700 text-[11px] font-bold align-text-top active:bg-blue-200"
        >
          {cite[1]}
        </button>
      )
    }
    return <Fragment key={index}>{part}</Fragment>
  })
}

function AnswerText({ text, sources, onCite }) {
  const lines = String(text).split('\n').filter((line) => line.trim())
  return (
    <div className="flex flex-col gap-1.5 text-sm text-slate-700 leading-relaxed">
      {lines.map((line, index) => {
        const isDisclaimer = line.trim().startsWith('※')
        const bullet = line.match(/^\s*[-*]\s+(.*)$/)
        if (isDisclaimer) {
          return <p key={index} className="text-xs text-slate-400 mt-1">{line}</p>
        }
        if (bullet) {
          return (
            <div key={index} className="flex gap-2 pl-1">
              <span className="text-blue-500 mt-0.5">•</span>
              <p className="flex-1"><InlineText text={bullet[1]} sources={sources} onCite={onCite} /></p>
            </div>
          )
        }
        return <p key={index}><InlineText text={line} sources={sources} onCite={onCite} /></p>
      })}
    </div>
  )
}

function SourceCard({ source, onOpen }) {
  return (
    <button
      onClick={() => onOpen(source)}
      className="w-full text-left bg-slate-50 border border-slate-200 rounded-xl p-3 flex items-start gap-2.5 active:bg-slate-100"
    >
      <span className="w-6 h-6 rounded-md bg-blue-600 text-white text-xs font-bold flex items-center justify-center flex-shrink-0">
        {source.n}
      </span>
      <div className="flex-1 min-w-0">
        <p className="text-sm font-semibold text-slate-800">{sourceTitle(source)}</p>
        <p className="text-xs text-slate-500 truncate">{source.heading}</p>
      </div>
    </button>
  )
}

function AssistantMessage({ message, onCite, onAsk }) {
  const citedSources = message.sources.filter((source) => message.cited?.includes(source.n))

  return (
    <div className="flex flex-col gap-3">
      <div className="flex items-center gap-2">
        <div className="w-7 h-7 rounded-lg bg-blue-600 flex items-center justify-center">
          <Scale size={15} className="text-white" />
        </div>
        <span className="text-xs font-semibold text-slate-500">AI 어드바이저</span>
      </div>

      {message.content ? (
        <AnswerText text={message.content} sources={message.sources} onCite={onCite} />
      ) : null}

      {message.status === 'streaming' && !message.content ? (
        <div className="flex items-center gap-2 text-sm text-slate-400">
          <Loader2 size={16} className="animate-spin" />
          <span>{message.progress ?? '답변을 준비하고 있습니다'}</span>
        </div>
      ) : null}

      {message.error ? <p className="text-sm text-red-500">{message.error}</p> : null}

      {citedSources.length > 0 ? (
        <div className="flex flex-col gap-2 mt-1">
          <p className="flex items-center gap-1.5 text-xs font-semibold text-slate-500">
            <BookOpen size={14} /> 근거 조문 {citedSources.length}건
          </p>
          {citedSources.map((source) => (
            <SourceCard key={source.id} source={source} onOpen={onCite} />
          ))}
        </div>
      ) : null}

      {message.followups?.length > 0 ? (
        <div className="flex flex-col gap-1.5 mt-1">
          {message.followups.map((question) => (
            <button
              key={question}
              onClick={() => onAsk(question)}
              className="self-start text-left text-xs text-blue-700 bg-blue-50 border border-blue-100 rounded-full px-3 py-1.5 active:bg-blue-100"
            >
              {question}
            </button>
          ))}
        </div>
      ) : null}
    </div>
  )
}

function ArticleSheet({ source, onClose }) {
  if (!source) return null
  return (
    <div className="fixed inset-0 z-[60] flex justify-center">
      <div className="absolute inset-0 bg-black/40" onClick={onClose} />
      <div className="relative self-end w-full max-w-[430px] max-h-[80svh] bg-white rounded-t-2xl flex flex-col">
        <div className="flex items-start justify-between gap-3 px-5 pt-5 pb-3 border-b border-slate-100">
          <div>
            <p className="text-xs text-slate-500">{source.law_title}</p>
            <h2 className="text-base font-bold text-slate-900">
              {source.article}({source.heading})
            </h2>
          </div>
          <button onClick={onClose} className="text-slate-400 p-1">
            <X size={20} />
          </button>
        </div>
        <div className="flex-1 overflow-y-auto px-5 py-4">
          <p className="text-sm text-slate-700 leading-relaxed whitespace-pre-wrap">{formatArticleText(source.text)}</p>
        </div>
        {source.url ? (
          <div className="px-5 pt-3 pb-6 border-t border-slate-100">
            <a
              href={source.url}
              target="_blank"
              rel="noreferrer"
              className="w-full flex items-center justify-center gap-1.5 border border-slate-300 text-slate-700 text-sm font-semibold py-3 rounded-xl active:bg-slate-50"
            >
              국가법령정보센터에서 원문 보기 <ExternalLink size={14} />
            </a>
          </div>
        ) : null}
      </div>
    </div>
  )
}

function SessionSheet({ onClose, onSelect }) {
  const [sessions, setSessions] = useState(null) // null = 불러오는 중

  useEffect(() => {
    api.get('/api/v1/advisor/sessions')
      .then((response) => setSessions(response.data))
      .catch(() => setSessions([]))
  }, [])

  return (
    <div className="fixed inset-0 z-[60] flex justify-center">
      <div className="absolute inset-0 bg-black/40" onClick={onClose} />
      <div className="relative self-end w-full max-w-[430px] max-h-[70svh] bg-white rounded-t-2xl flex flex-col">
        <div className="flex items-center justify-between px-5 pt-5 pb-3 border-b border-slate-100">
          <h2 className="text-base font-bold text-slate-900">이전 상담</h2>
          <button onClick={onClose} className="text-slate-400 p-1"><X size={20} /></button>
        </div>
        <div className="flex-1 overflow-y-auto px-3 py-2 pb-6">
          {sessions === null ? <p className="text-sm text-slate-400 px-2 py-4">불러오는 중...</p> : null}
          {sessions?.length === 0 ? (
            <p className="text-sm text-slate-400 px-2 py-4">저장된 상담이 없습니다</p>
          ) : null}
          {(sessions ?? []).map((session) => (
            <button
              key={session.id}
              onClick={() => onSelect(session.id)}
              className="w-full text-left px-3 py-3 rounded-xl active:bg-slate-50"
            >
              <p className="text-sm font-medium text-slate-800 truncate">{session.title}</p>
              <p className="text-xs text-slate-400">{session.updated_at?.split(' ')[0]}</p>
            </button>
          ))}
        </div>
      </div>
    </div>
  )
}

export default function AdvisorPage() {
  const navigate = useNavigate()
  const location = useLocation()
  const [messages, setMessages] = useState([])
  const [sessionId, setSessionId] = useState(null)
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [openSource, setOpenSource] = useState(null)
  const [showSessions, setShowSessions] = useState(false)
  const [context, setContext] = useState(location.state?.context ?? null)
  const bottomRef = useRef(null)
  const abortRef = useRef(null)
  // 분석 결과에서 들어온 경우에만 결과 화면으로 돌아가는 버튼을 보여준다
  const cameFromResult = location.state?.from === 'result'

  const backToResult = () => {
    abortRef.current?.abort()
    // 히스토리의 결과 화면(state 포함)으로 복귀 — push 하면 결과↔어드바이저 루프가 쌓인다
    navigate(-1)
  }

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  useEffect(() => () => abortRef.current?.abort(), [])

  const updateLastMessage = (patch) => {
    setMessages((prev) => {
      const next = [...prev]
      const last = next[next.length - 1]
      next[next.length - 1] = { ...last, ...(typeof patch === 'function' ? patch(last) : patch) }
      return next
    })
  }

  const ask = async (question) => {
    const text = question.trim()
    if (!text || loading) return
    setInput('')
    setLoading(true)
    setMessages((prev) => [
      ...prev,
      { role: 'user', content: text },
      { role: 'assistant', content: '', sources: [], status: 'streaming' },
    ])

    const controller = new AbortController()
    abortRef.current = controller
    try {
      await streamAdvisorChat(
        { message: text, session_id: sessionId, context },
        (event, data) => {
          if (event === 'progress') updateLastMessage({ progress: data.message })
          if (event === 'sources') {
            setSessionId(data.session_id)
            updateLastMessage({ sources: data.sources })
          }
          if (event === 'delta') updateLastMessage((last) => ({ content: last.content + data.text }))
          if (event === 'done') {
            updateLastMessage({ status: 'done', cited: data.cited, followups: data.followups })
          }
          if (event === 'error') updateLastMessage({ status: 'error', error: data.message })
        },
        controller.signal,
      )
      setContext(null) // 현장 상황은 첫 질문에만 붙인다
    } catch (error) {
      if (error.status === 401) {
        clearToken()
        navigate('/login', { replace: true })
        return
      }
      if (error.name !== 'AbortError') {
        updateLastMessage({ status: 'error', error: error.message || '연결에 실패했습니다.' })
      }
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    const initialQuestion = location.state?.question
    if (!initialQuestion) return undefined
    // StrictMode(개발)의 마운트→언마운트→재마운트에서 첫 요청이 abort 되지 않도록,
    // 실제로 남아 있는 마운트에서만 한 번 전송한다.
    const timer = setTimeout(() => ask(initialQuestion), 0)
    return () => clearTimeout(timer)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const startNewChat = () => {
    abortRef.current?.abort()
    setMessages([])
    setSessionId(null)
    setContext(null)
  }

  const loadSession = async (id) => {
    setShowSessions(false)
    abortRef.current?.abort()
    const { data } = await api.get(`/api/v1/advisor/sessions/${id}`)
    setSessionId(data.id)
    setContext(null)
    setMessages(
      data.messages.map((message) => (message.role === 'user'
        ? { role: 'user', content: message.content }
        : {
            role: 'assistant',
            content: message.content,
            sources: message.sources,
            cited: citedNumbers(message.content, message.sources),
            status: 'done',
          })),
    )
  }

  return (
    <Layout>
      <header className="sticky top-0 z-10 bg-white flex items-center justify-between px-5 pt-10 pb-4 border-b border-slate-100">
        <div className="flex items-center gap-3">
          {cameFromResult ? (
            <button onClick={backToResult} className="text-slate-500" aria-label="분석 결과로 돌아가기">
              <ArrowLeft size={22} />
            </button>
          ) : null}
          <h1 className="text-lg font-bold text-slate-900">AI 어드바이저</h1>
        </div>
        <div className="flex items-center gap-1">
          <button onClick={() => setShowSessions(true)} className="p-2 text-slate-500" aria-label="이전 상담">
            <History size={20} />
          </button>
          <button onClick={startNewChat} className="p-2 text-slate-500" aria-label="새 상담">
            <Plus size={20} />
          </button>
        </div>
      </header>

      <div className="flex-1 flex flex-col gap-6 px-5 pt-5 pb-24">
        {messages.length === 0 ? (
          <div className="flex flex-col gap-5 pt-6">
            <div className="flex flex-col items-center text-center gap-3">
              <div className="w-14 h-14 rounded-2xl bg-blue-600 flex items-center justify-center">
                <Scale size={26} className="text-white" />
              </div>
              <p className="text-base font-bold text-slate-900">산업안전보건 법령 어드바이저</p>
              <p className="text-sm text-slate-500 leading-relaxed">
                궁금한 안전보건 의무와 기준을 물어보세요.<br />
                관련 법령 조문을 근거로 답해 드립니다.
              </p>
            </div>
            {context ? (
              <div className="bg-orange-50 border border-orange-100 rounded-xl p-3 text-xs text-orange-700">
                사진 분석 결과를 참고해 답변합니다.
              </div>
            ) : null}
            <div className="flex flex-col gap-2">
              <p className="text-xs font-semibold text-slate-500">이런 질문을 해보세요</p>
              {(context ? CONTEXT_SUGGESTED_QUESTIONS : SUGGESTED_QUESTIONS).map((question) => (
                <button
                  key={question}
                  onClick={() => ask(question)}
                  className="text-left text-sm text-slate-700 bg-slate-50 border border-slate-200 rounded-xl px-4 py-3 active:bg-slate-100"
                >
                  {question}
                </button>
              ))}
            </div>
          </div>
        ) : null}

        {messages.map((message, index) => (message.role === 'user' ? (
          <div key={index} className="self-end max-w-[85%] bg-blue-600 text-white text-sm rounded-2xl rounded-tr-md px-4 py-2.5">
            {message.content}
          </div>
        ) : (
          <AssistantMessage key={index} message={message} onCite={setOpenSource} onAsk={ask} />
        )))}
        <div ref={bottomRef} />
      </div>

      <form
        onSubmit={(event) => {
          event.preventDefault()
          ask(input)
        }}
        className="fixed bottom-16 left-1/2 -translate-x-1/2 w-full max-w-[430px] bg-white border-t border-slate-100 px-4 py-3 flex items-center gap-2 z-40"
      >
        <input
          value={input}
          onChange={(event) => setInput(event.target.value)}
          placeholder="안전보건 법령에 대해 질문하세요"
          className="flex-1 bg-slate-100 rounded-xl px-4 py-2.5 text-sm outline-none focus:ring-2 focus:ring-blue-200"
        />
        <button
          type="submit"
          disabled={loading || !input.trim()}
          className="w-10 h-10 rounded-xl bg-blue-600 text-white flex items-center justify-center disabled:opacity-40"
          aria-label="보내기"
        >
          {loading ? <Loader2 size={18} className="animate-spin" /> : <Send size={18} />}
        </button>
      </form>

      <ArticleSheet source={openSource} onClose={() => setOpenSource(null)} />
      {showSessions ? <SessionSheet onClose={() => setShowSessions(false)} onSelect={loadSession} /> : null}
    </Layout>
  )
}
