"use client";

import { FormEvent, useState, useEffect } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

type Message = {
  role: "user" | "assistant";
  text: string;
  isStreaming?: boolean;
};

const API_URL = "http://localhost:8000/chat";

// 타자 치는 효과 Hook
function useTypewriter(text: string, speed = 10) {
  const [displayedText, setDisplayedText] = useState("");

  useEffect(() => {
    if (!text || text.length < displayedText.length) {
      setDisplayedText("");
      return;
    }

    if (displayedText.length >= text.length) {
      return;
    }

    const timeout = setTimeout(() => {
      setDisplayedText((prev) => {
        const nextCharIndex = prev.length;
        if (nextCharIndex < text.length) {
          return prev + text.charAt(nextCharIndex);
        }
        return prev;
      });
    }, speed);

    return () => clearTimeout(timeout);
  }, [text, displayedText, speed]);

  return displayedText;
}

// 메시지 컴포넌트
const MessageItem = ({ message }: { message: Message }) => {
  const shouldAnimate = message.role === "assistant" && message.isStreaming;
  const typedText = useTypewriter(message.text, 15);
  
  const content = shouldAnimate ? typedText : message.text;

  return (
    <div className={`flex w-full ${message.role === "user" ? "justify-end" : "justify-start"}`}>
      <div
        className={`max-w-[85%] rounded-2xl px-5 py-4 text-sm leading-relaxed shadow-sm ${
          message.role === "user"
            ? "bg-slate-800 text-slate-100"
            : "bg-slate-700/50 text-slate-100"
        }`}
      >
        <p className="mb-1 font-semibold uppercase tracking-[0.2em] text-[0.6rem] text-slate-400">
          {message.role === "user" ? "나" : "AI"}
        </p>
        
        {message.role === "assistant" ? (
          <div className="prose prose-invert prose-sm max-w-none">
            <ReactMarkdown 
              remarkPlugins={[remarkGfm]}
              components={{
                a: ({ node, ...props }) => (
                  <a {...props} target="_blank" rel="noopener noreferrer" className="text-pink-400 hover:underline" />
                ),
                img: ({ node, ...props }) => (
                  <span className="mx-auto my-6 block h-[250px] w-[250px] overflow-hidden rounded-2xl shadow-lg border border-slate-600/50 relative">
                    <img
                      {...props}
                      className="h-full w-full object-cover object-center scale-125"
                      alt={props.alt || "Perfume Image"}
                    />
                  </span>
                ),
                h2: ({ node, ...props }) => (
                  <h2 {...props} className="text-xl font-bold mt-8 mb-3 text-white border-l-4 border-pink-500 pl-3" />
                ),
                hr: ({ node, ...props }) => (
                  <hr {...props} className="my-10 border-slate-600" />
                ),
                // 👇 [수정됨] 제목 스타일: Sky Blue -> Soft Violet (라벤더)
                // 전체적으로 핑크/보라 톤인 앱과 훨씬 조화롭습니다.
                em: ({ node, ...props }) => (
                  <em {...props} className="not-italic text-violet-400 font-bold mr-1" />
                ),
                // 👇 [강조] 핑크색 유지
                strong: ({ node, ...props }) => (
                  <strong {...props} className="text-pink-300 font-extrabold" />
                ),
              }}
            >
              {content || "..."} 
            </ReactMarkdown>
          </div>
        ) : (
          <p>{content}</p>
        )}
      </div>
    </div>
  );
};

export default function Home() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [inputValue, setInputValue] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  
  const [threadId, setThreadId] = useState("");

  useEffect(() => {
    const savedId = localStorage.getItem("chat_thread_id");
    if (savedId) {
      setThreadId(savedId);
    } else {
      const newId = crypto.randomUUID();
      localStorage.setItem("chat_thread_id", newId);
      setThreadId(newId);
    }
  }, []);

  const handleNewChat = () => {
    if (loading) return; 
    const newId = crypto.randomUUID();
    localStorage.setItem("chat_thread_id", newId); 
    setThreadId(newId);
    setMessages([]); 
    setInputValue("");
    setError("");
    console.log("Session Reset. New Thread ID:", newId);
  };

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();

    const trimmed = inputValue.trim();
    if (!trimmed || !threadId) return;

    setMessages((prev) => prev.map(m => ({ ...m, isStreaming: false })));
    setMessages((prev) => [...prev, { role: "user", text: trimmed, isStreaming: false }]);
    setInputValue("");
    setError("");
    setLoading(true);

    try {
      const response = await fetch(API_URL, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ 
          user_query: trimmed, 
          thread_id: threadId 
        }),
      });

      if (!response.ok || !response.body) {
        throw new Error("서버 연결 실패");
      }

      setMessages((prev) => [...prev, { role: "assistant", text: "", isStreaming: true }]);

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let done = false;
      let buffer = "";

      while (!done) {
        const { value, done: readerDone } = await reader.read();
        done = readerDone;

        if (value) {
          const chunk = decoder.decode(value, { stream: true });
          buffer += chunk;
          const lines = buffer.split("\n\n");
          buffer = lines.pop() || "";

          for (const line of lines) {
            const trimmedLine = line.trim();
            if (!trimmedLine.startsWith("data: ")) continue;

            try {
              const jsonStr = trimmedLine.replace("data: ", "");
              const data = JSON.parse(jsonStr);

              if (data.type === "answer") {
                setMessages((prev) => {
                  const updated = [...prev];
                  const lastMsg = updated[updated.length - 1];
                  if (lastMsg.role === "assistant") {
                    lastMsg.text = data.content; 
                  }
                  return updated;
                });
              }
            } catch (e) {
              console.error("Parsing Error:", e);
            }
          }
        }
      }
    } catch (e) {
      setError("응답을 받아오는 중 오류가 발생했습니다.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex min-h-screen flex-col bg-slate-950 px-4 py-12 text-slate-50">
      <div className="mx-auto w-full max-w-3xl space-y-8">
        
        <header className="space-y-2">
          <p className="text-sm uppercase tracking-[0.4em] text-slate-400">Perfume Assistant</p>
          <div className="flex items-center justify-between">
            <h1 className="text-3xl font-semibold text-white">향수 추천 AI</h1>
            
            <button 
              onClick={handleNewChat}
              disabled={loading}
              className="group flex items-center gap-2 rounded-full border border-slate-700 bg-slate-800/50 px-4 py-2 text-xs font-medium text-slate-300 transition-all hover:bg-slate-700 hover:text-white hover:border-pink-500/50 active:scale-95 disabled:opacity-50"
            >
              <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" className="w-4 h-4 transition-transform group-hover:rotate-180">
                <path strokeLinecap="round" strokeLinejoin="round" d="M16.023 9.348h4.992v-.001M2.985 19.644v-4.992m0 0h4.992m-4.993 0l3.181 3.183a8.25 8.25 0 0013.803-3.7M4.031 9.865a8.25 8.25 0 0113.803-3.7l3.181 3.182m0-4.991v4.99" />
              </svg>
              새 대화
            </button>
          </div>
          <p className="text-slate-300">LangGraph 기반 실시간 스트리밍 챗봇</p>
        </header>

        <section className="min-h-[400px] rounded-2xl border border-slate-800 bg-white/5 p-6 shadow-lg shadow-slate-900/40">
          <div className="space-y-6">
            {messages.length === 0 && (
              <p className="text-slate-400">질문을 입력하면 AI가 분석 및 조사를 시작합니다.</p>
            )}
            {messages.map((msg, idx) => (
              <MessageItem key={idx} message={msg} />
            ))}
            {loading && messages[messages.length - 1]?.role === "user" && (
              <div className="flex justify-start">
                 <div className="rounded-2xl bg-slate-700/50 px-5 py-4 text-sm text-slate-400 animate-pulse">
                   AI가 생각하고 있습니다... 💭
                 </div>
              </div>
            )}
          </div>
        </section>

        <form onSubmit={handleSubmit} className="space-y-3">
          <div className="flex gap-3">
            <input
              className="flex-1 rounded-2xl border border-slate-800 bg-slate-900/80 px-4 py-3 text-base text-white outline-none focus:border-pink-500/50 transition-colors"
              placeholder="예) 여름에 쓰기 좋은 시트러스 향수"
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              disabled={loading}
            />
            <button
              className="rounded-2xl bg-gradient-to-r from-pink-500 to-purple-500 px-6 py-3 font-semibold text-white hover:opacity-90 transition-opacity disabled:opacity-50"
              type="submit"
              disabled={loading}
            >
              {loading ? "..." : "전송"}
            </button>
          </div>
          {error && <p className="text-sm text-rose-300">{error}</p>}
        </form>
      </div>
    </div>
  );
}