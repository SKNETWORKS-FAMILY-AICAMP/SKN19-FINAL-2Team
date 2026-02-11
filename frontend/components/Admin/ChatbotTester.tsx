import { useState, useRef, FormEvent } from "react";
import TestPanel from "./TestPanel";
import AdminMessageItem, { Message } from "./AdminMessageItem";

type Evaluation = {
    verdict: string;
    issue_type: string | null;
    severity: string | null;
    expected_output: string;
    suggestion: string;
    target_agent: string | null;
    affected_file: string | null;
};

export default function ChatbotTester() {
    const [messages, setMessages] = useState<Message[]>([]);
    const [evaluations, setEvaluations] = useState<Evaluation[]>([]);
    const [logs, setLogs] = useState<string[]>([]);

    // Context State
    const [userMode, setUserMode] = useState<"BEGINNER" | "EXPERT">("BEGINNER");
    const [memberId, setMemberId] = useState<number>(0); // 0 = 비회원

    const [input, setInput] = useState("");
    const [loading, setLoading] = useState(false);

    // Session State
    const [sessionId, setSessionId] = useState(() => `test_${Date.now()}`);
    const [turnCount, setTurnCount] = useState(1);

    const messagesEndRef = useRef<HTMLDivElement>(null);

    const scrollToBottom = () => {
        setTimeout(() => {
            if (messagesEndRef.current) {
                const scrollContainer = messagesEndRef.current.closest('div.overflow-y-auto');
                if (scrollContainer) {
                    scrollContainer.scrollTo({
                        top: scrollContainer.scrollHeight,
                        behavior: 'smooth'
                    });
                }
            }
        }, 50);
    };

    const handleSubmit = async (e: FormEvent) => {
        e.preventDefault();
        if (!input.trim() || loading) return;

        const query = input.trim();
        setInput("");
        setLoading(true);

        setMessages(prev => [...prev, { role: "user", text: query, isStreaming: false }]);
        scrollToBottom();

        setMessages(prev => [...prev, { role: "assistant", text: "", isStreaming: true }]);

        try {
            const res = await fetch("/api/admin/test/chat", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    user_query: query,
                    session_id: sessionId,
                    turn_count: turnCount,
                    member_id: memberId,   // [Context] 회원 ID
                    user_mode: userMode,   // [Context] 사용자 모드
                    context: {
                        history: messages.map(m => ({
                            role: m.role,
                            content: m.text
                        }))
                    }
                }),
            });

            if (!res.ok || !res.body) {
                throw new Error(res.statusText || "Stream Error");
            }

            const reader = res.body.getReader();
            const decoder = new TextDecoder();
            let accumulatedText = "";
            let buffer = ""; // [BUG FIX] 스트림 버퍼 추가: 패킷이 잘려서 오더라도 완벽한 JSON이 될 때까지 대기

            while (true) {
                const { done, value } = await reader.read();
                if (done) break;

                const chunk = decoder.decode(value, { stream: true });
                buffer += chunk;

                // SSE 메시지는 '\n\n'으로 구분됨
                const lines = buffer.split("\n\n");

                // 마지막 조각은 미완성일 수 있으므로 버퍼에 남겨둠
                buffer = lines.pop() || "";

                for (const line of lines) {
                    if (line.startsWith("data: ")) {
                        try {
                            const jsonStr = line.slice(6);
                            const event = JSON.parse(jsonStr);

                            if (event.type === "token") {
                                accumulatedText += event.content;
                                setMessages(prev => {
                                    const newMsgs = [...prev];
                                    const lastMsg = newMsgs[newMsgs.length - 1];
                                    if (lastMsg && lastMsg.role === "assistant") {
                                        lastMsg.text = accumulatedText;
                                    }
                                    return newMsgs;
                                });
                                scrollToBottom();
                            }
                            else if (event.type === "log") {
                                setLogs(prev => [...prev, event.content]);
                            }
                            else if (event.type === "evaluation") {
                                setEvaluations(prev => [...prev, event.content]);
                            }
                        } catch (e) {
                            console.error("Parse Error (Retry next chunk):", e);
                            // 파싱 에러가 나면 해당 라인은 버림 (오염된 데이터)
                        }
                    }
                }
            }

            setMessages(prev => {
                const newMsgs = [...prev];
                const lastMsg = newMsgs[newMsgs.length - 1];
                if (lastMsg) lastMsg.isStreaming = false;
                return newMsgs;
            });

            setTurnCount(prev => prev + 1);

        } catch (error: any) {
            console.error(error);
            setLogs(prev => [...prev, `❌ 클라이언트 에러: ${error.message}`]);
            setMessages(prev => [...prev, {
                role: "assistant",
                text: "⚠️ 통신 오류가 발생했습니다.",
                isStreaming: false
            }]);
        } finally {
            setLoading(false);
            scrollToBottom();
        }
    };

    const handleExport = (format: "csv" | "xlsx" | "md") => {
        window.location.href = `/api/admin/test/export/${sessionId}?format=${format}`;
    };

    // [New] 세션 초기화 (완전히 새로운 시작)
    const handleReset = async () => {
        // 이전 세션 정리 (선택 사항)
        try {
            await fetch(`/api/admin/test/session/${sessionId}`, { method: "DELETE" });
        } catch (e) { console.error(e); }

        // 상태 초기화
        setMessages([]);
        setEvaluations([]);
        setLogs([]);
        setTurnCount(1);

        // 새로운 세션 ID 발급 -> 백엔드에서 새 대화로 인식
        const newSessionId = `test_${Date.now()}`;
        setSessionId(newSessionId);

        // 시스템 로그 추가
        setLogs([`🔄 세션이 초기화되었습니다. (ID: ${newSessionId})`]);
    };

    return (
        <div className="flex h-[calc(100vh-140px)] border rounded-xl overflow-hidden shadow-sm bg-white">
            {/* [Left] Chatbot Interact Area */}
            <div className="flex-1 flex flex-col border-r border-gray-100 min-w-0">
                {/* Header with Context Controls */}
                <div className="p-3 border-b border-gray-100 bg-gray-50/50 flex flex-wrap gap-4 justify-between items-center">
                    <div className="flex items-center gap-3">
                        <div className="flex items-center gap-2">
                            <span className="text-xs font-bold text-gray-500">모드:</span>
                            <div className="flex bg-white rounded border border-gray-200 p-0.5">
                                <button
                                    onClick={() => setUserMode("BEGINNER")}
                                    className={`px-2 py-1 text-[10px] font-bold rounded transition-colors ${userMode === "BEGINNER" ? "bg-black text-white" : "text-gray-400 hover:text-gray-600"
                                        }`}
                                >
                                    BEGINNER
                                </button>
                                <button
                                    onClick={() => setUserMode("EXPERT")}
                                    className={`px-2 py-1 text-[10px] font-bold rounded transition-colors ${userMode === "EXPERT" ? "bg-black text-white" : "text-gray-400 hover:text-gray-600"
                                        }`}
                                >
                                    EXPERT
                                </button>
                            </div>
                        </div>

                        <div className="flex items-center gap-2">
                            <span className="text-xs font-bold text-gray-500">Member ID:</span>
                            <input
                                type="number"
                                value={memberId}
                                onChange={(e) => setMemberId(parseInt(e.target.value) || 0)}
                                className="w-16 px-1.5 py-1 text-xs border border-gray-200 rounded text-center focus:outline-none focus:border-black"
                            />
                        </div>
                    </div>

                    <div className="flex items-center gap-3">
                        <div className="flex flex-col items-end">
                            <span className="text-[10px] font-bold text-gray-400 leading-none">SESSION ID</span>
                            <span
                                key={sessionId} // 세션 변경 시 깜빡임 효과
                                className="text-xs font-mono text-blue-600 font-bold animate-[pulse_0.5s_ease-in-out]"
                            >
                                {sessionId}
                            </span>
                        </div>
                        <button
                            onClick={handleReset}
                            className="text-[10px] px-2.5 py-1.5 bg-white border border-gray-200 hover:bg-red-50 hover:text-red-500 hover:border-red-200 text-gray-500 font-bold rounded transition-all flex items-center gap-1 shadow-sm"
                        >
                            🔄 New Session
                        </button>
                    </div>
                </div>

                {/* Messages Area */}
                <div className="flex-1 overflow-y-auto bg-white p-4 custom-scrollbar">
                    {messages.length === 0 ? (
                        <div className="h-full flex flex-col items-center justify-center text-gray-300 space-y-2 select-none">
                            <div className="w-12 h-12 bg-gray-50 rounded-full flex items-center justify-center mb-1">
                                <span className="text-xl">🧪</span>
                            </div>
                            <p className="text-sm font-medium">테스트 준비 완료</p>
                            <div className="text-xs text-center opacity-70">
                                Mode: <span className="font-bold">{userMode}</span> | User: <span className="font-bold">{memberId}</span>
                            </div>
                        </div>
                    ) : (
                        <div className="space-y-6">
                            {messages.map((msg, idx) => (
                                <AdminMessageItem key={idx} message={msg} />
                            ))}

                            {loading && (
                                <div className="flex justify-start">
                                    <div className="rounded-2xl bg-white/80 border border-[#E5E4DE] px-5 py-4 text-sm text-[#8E8E8E] animate-pulse shadow-sm">
                                        Thinking... 💭
                                    </div>
                                </div>
                            )}
                            <div ref={messagesEndRef} />
                        </div>
                    )}
                </div>

                {/* Input Area */}
                <form onSubmit={handleSubmit} className="p-3 border-t border-gray-100 bg-gray-50/30">
                    <div className="flex gap-2">
                        <input
                            type="text"
                            value={input}
                            onChange={(e) => setInput(e.target.value)}
                            placeholder="명령어 입력..."
                            className="flex-1 px-4 py-2.5 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-black/5 transition-all text-sm shadow-sm"
                            disabled={loading}
                        />
                        <button
                            type="submit"
                            disabled={loading || !input.trim()}
                            className={`px-5 py-2 rounded-lg text-sm font-bold transition-all shadow-sm ${loading || !input.trim()
                                ? "bg-gray-200 text-gray-400 cursor-not-allowed"
                                : "bg-black text-white hover:bg-gray-800"
                                }`}
                        >
                            {loading ? "..." : "Run"}
                        </button>
                    </div>
                </form>
            </div>

            {/* [Right] Test Result Panel */}
            <TestPanel
                evaluations={evaluations}
                logs={logs}
                onExport={handleExport}
            />
        </div>
    );
}
