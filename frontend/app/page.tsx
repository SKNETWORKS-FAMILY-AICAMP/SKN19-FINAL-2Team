"use client";

import { FormEvent, useState, useEffect, useRef } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

type Message = {
  role: "user" | "assistant";
  text: string;
  isStreaming?: boolean; // 현재 타자 치는 중인지 여부
};

type ChatMeta = {
  clarified_query?: string;
  research_result?: string;
  conversation_history?: { question: string; answer: string }[];
};

const API_URL = "http://localhost:8000/chat";

// 타자 치는 효과를 위한 커스텀 훅
function useTypewriter(text: string, speed = 10) {
  const [displayedText, setDisplayedText] = useState("");
  
  useEffect(() => {
    let i = 0;
    setDisplayedText(""); // 초기화
    
    if (!text) return;

    const timer = setInterval(() => {
      if (i < text.length) {
        setDisplayedText((prev) => prev + text.charAt(i));
        i++;
      } else {
        clearInterval(timer);
      }
    }, speed);

    return () => clearInterval(timer);
  }, [text, speed]);

  return displayedText;
}

// 메시지 컴포넌트 (개별 메시지 렌더링)
const MessageItem = ({ message }: { message: Message }) => {
  // 봇이면서 스트리밍 중(방금 도착한 메시지)일 때만 타자 효과 적용
  // 이미 지나간 메시지나 유저는 그냥 보여줌
  const shouldAnimate = message.role === "assistant" && message.isStreaming;
  const typedText = useTypewriter(message.text, 15); // 속도 조절 (작을수록 빠름)
  
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
  const [meta, setMeta] = useState<ChatMeta | null>(null);

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();

    const trimmed = inputValue.trim();
    if (!trimmed) return;

    // 1. 이전 메시지들의 isStreaming을 모두 false로 변경 (애니메이션 중지)
    setMessages((prev) => prev.map(m => ({ ...m, isStreaming: false })));

    // 2. 새 유저 메시지 추가
    setMessages((prev) => [...prev, { role: "user", text: trimmed, isStreaming: false }]);
    setInputValue("");
    setError("");
    setLoading(true);
    setMeta(null);

    try {
      const response = await fetch(API_URL, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ user_query: trimmed }),
      });

      if (!response.ok || !response.body) {
        throw new Error("서버 연결 실패");
      }

      // 3. 봇 응답 Placeholder 추가 (빈 텍스트)
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
                // 답변 도착! -> 메시지 업데이트
                setMessages((prev) => {
                  const updated = [...prev];
                  const lastMsg = updated[updated.length - 1];
                  if (lastMsg.role === "assistant") {
                    lastMsg.text = data.content; 
                    // isStreaming은 유지하여 Typewriter 효과 발생
                  }
                  return updated;
                });
              } else if (data.type === "log") {
                // 로그(조사 결과 등) 처리 로직 (필요시 구현)
                console.log("Log:", data.content);
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
          <h1 className="text-3xl font-semibold text-white">향수 추천 AI</h1>
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