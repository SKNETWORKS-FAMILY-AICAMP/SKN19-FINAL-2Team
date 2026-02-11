"use client";

import { FormEvent, useState, useEffect, useRef } from "react";
import Link from "next/link";
import { useSession } from "next-auth/react";
import { useRouter } from "next/navigation";
import ChatList from "../../components/Chat/ChatList";
import { Message } from "../../components/Chat/MessageItem";
import ChatSidebar from "../../components/Chat/Sidebar"; // 좌측 채팅 기록 사이드바
import MagneticButton from "../../components/common/MagneticButton"; // [NEW] 마그네틱 버튼 추가
import { SavedPerfumesProvider } from "../../contexts/SavedPerfumesContext";
import PageLayout from "@/components/common/PageLayout";

const API_URL = "/api/chat";

type ProfileResponse = {
    nickname?: string | null;
    name?: string | null;
    kakao_nickname?: string | null;
    email?: string | null;
};

const toSafeName = (value?: string | null): string => {
    const trimmed = value?.trim();
    return trimmed && trimmed.length > 0 ? trimmed : "";
};

const resolvePreferredDisplayName = (params: {
    legacyNickname?: string | null;
    name?: string | null;
    kakaoNickname?: string | null;
    email?: string | null;
}) => {
    const emailLocalPart = params.email?.split("@")[0];

    return (
        toSafeName(params.legacyNickname) ||
        toSafeName(params.name) ||
        toSafeName(params.kakaoNickname) ||
        toSafeName(emailLocalPart) ||
        "Guest"
    );
};

export default function ChatPage() {
    const { data: session } = useSession(); // 카카오 로그인 세션
    const router = useRouter();
    const [isSidebarOpen, setIsSidebarOpen] = useState(false); // 좌측 채팅 내역 사이드바

    const [messages, setMessages] = useState<Message[]>([]);
    const [inputValue, setInputValue] = useState("");
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState("");
    const [statusLog, setStatusLog] = useState("");
    const [isMounted, setIsMounted] = useState(false);
    const [threadId, setThreadId] = useState("");
    const [memberId, setMemberId] = useState<number | null>(null);
    const [displayName, setDisplayName] = useState("Guest");
    const messagesEndRef = useRef<HTMLDivElement>(null);
    const inputRef = useRef<HTMLTextAreaElement>(null);

    // localAuth 제거: 세션 기반으로만 사용자 상태 관리

    const [placeholder, setPlaceholder] = useState("어떤 향수를 찾으시나요?"); // [NEW] Responsive Placeholder

    useEffect(() => {
        setIsMounted(true);

        // [NEW] Window Resize Listener for Placeholder
        const handleResize = () => {
            if (window.innerWidth >= 768) { // md breakpoint
                setPlaceholder("어떤 향수를 찾으시나요? 무엇이든 물어보세요.");
            } else {
                setPlaceholder("어떤 향수를 찾으시나요?");
            }
        };
        handleResize();
        window.addEventListener('resize', handleResize);

        // Always start a new session on visit (per requirements)
        const newId = crypto.randomUUID();
        localStorage.setItem("chat_thread_id", newId);
        setThreadId(newId);
        setMessages([]);

        return () => window.removeEventListener('resize', handleResize);
    }, []);

    useEffect(() => {
        // localAuth 제거: memberId는 세션에서만 가져옴
        const currentId = session?.user?.id;
        if (!currentId) {
            setMemberId(null);
            return;
        }
        setMemberId(parseInt(currentId, 10));
    }, [session]);

    useEffect(() => {
        const currentId = session?.user?.id;
        const fallbackName = resolvePreferredDisplayName({
            kakaoNickname: session?.user?.name,
            email: session?.user?.email,
        });

        if (!currentId) {
            setDisplayName(fallbackName);
            return;
        }

        const controller = new AbortController();

        fetch(`/api/users/profile/${currentId}`, {
            cache: "no-store",
            signal: controller.signal,
        })
            .then((res) => (res.ok ? res.json() : null))
            .then((data: ProfileResponse | null) => {
                const preferredName = resolvePreferredDisplayName({
                    legacyNickname: data?.nickname,
                    name: data?.name,
                    kakaoNickname: data?.kakao_nickname || session?.user?.name,
                    email: data?.email || session?.user?.email,
                });
                setDisplayName(preferredName);
            })
            .catch(() => {
                setDisplayName(fallbackName);
            });

        return () => controller.abort();
    }, [session?.user?.id, session?.user?.name, session?.user?.email]);

    const chatContainerRef = useRef<HTMLDivElement>(null);
    const [isUserScrolledUp, setIsUserScrolledUp] = useState(false);
    const [showScrollButton, setShowScrollButton] = useState(false);

    const scrollToLatestMessage = (behavior: ScrollBehavior = "auto") => {
        if (messagesEndRef.current) {
            messagesEndRef.current.scrollIntoView({ behavior, block: "end" });
            return;
        }
        if (chatContainerRef.current) {
            chatContainerRef.current.scrollTo({
                top: chatContainerRef.current.scrollHeight,
                behavior,
            });
        }
    };

    // [New] Add ArrowDown icon import manually if not present, or use SVG. 
    // Since we can't see imports easily without context re-read, I'll allow Lucide import at top if I can, OR just use SVG inline.
    // Given previous file view show Lucide imports like Home, Sparkles etc.. I assume I can add ArrowDown.
    // But I will stick to inline SVG to be safe and avoid multi-file edits for imports.



    // [Simple IsUserScrolledUp State Logic]
    // No complex locking refs. Trust the state.
    // If user scrolls up, state becomes true -> auto-scroll stops.
    // If user is at bottom, state becomes false -> auto-scroll works.
    const handleScroll = () => {
        if (!chatContainerRef.current) return;
        const { scrollTop, scrollHeight, clientHeight } = chatContainerRef.current;
        const isAtBottom = scrollHeight - scrollTop - clientHeight <= 30; // 30px Threshold

        // Only update state if it changes to prevent re-renders
        if (isAtBottom && isUserScrolledUp) {
            setIsUserScrolledUp(false);
            setShowScrollButton(false);
        } else if (!isAtBottom && !isUserScrolledUp) {
            setIsUserScrolledUp(true);
            setShowScrollButton(true);
        }
    };

    const forceScrollToBottom = () => {
        scrollToLatestMessage("smooth");
        // Optimistic update
        setIsUserScrolledUp(false);
        setShowScrollButton(false);
    };

    useEffect(() => {
        const lastMsg = messages[messages.length - 1];
        if (!lastMsg) return;

        const isUserMsg = lastMsg.role === 'user';

        if (isUserMsg) {
            // User's message: Always scroll to bottom (smooth)
            setTimeout(() => {
                scrollToLatestMessage("smooth");
            }, 50);
        } else {
            // Bot's message: Only scroll if user WAS at the bottom before this update.
            if (!isUserScrolledUp) {
                setTimeout(() => {
                    // Use auto behavior for rapid updates to avoid animation queue issues.
                    scrollToLatestMessage("auto");
                }, 10);
            }
        }
    }, [messages, isUserScrolledUp]);

    useEffect(() => {
        if (!loading) {
            setTimeout(() => inputRef.current?.focus(), 0);
        }
    }, [loading]);
    // Note: isUserScrolledUp dependency ensures that if user scrolls down manually to bottom, it re-enables auto-scroll for NEXT render, 
    // but doesn't necessarily trigger scroll immediately unless messages change. 
    // Actually, if messages change, effect runs. It reads current isUserScrolledUp. 
    // If isUserScrolledUp is true, it skips scroll. That's correct.

    if (!isMounted) return <div className="min-h-screen bg-[#FAF8F5]" />;


    const handleNewChat = () => {
        if (loading) return;
        const newId = crypto.randomUUID();
        localStorage.setItem("chat_thread_id", newId);
        setThreadId(newId);
        setMessages([]);
        setInputValue("");
        setError("");
    };

    const handleSelectThread = async (id: string) => {
        if (loading) return;

        setLoading(true);
        setThreadId(id);
        localStorage.setItem("chat_thread_id", id); // 로컬 스토리지 갱신

        try {
            const response = await fetch(`/api/chat/history/${id}`);
            if (!response.ok) throw new Error("내역 로드 실패");

            const data = await response.json();
            // 백엔드 필드명(text)을 프론트엔드 필드명(text)에 맞춰 매핑
            const formattedMessages = data.messages.map((m: any) => ({
                role: m.role,
                text: m.text,
                isStreaming: false
            }));

            setMessages(formattedMessages);
            // setIsSidebarOpen(false); // [수정] 리스트 선택 시 사이드바 자동 닫힘 방지 (사용자 요청)
        } catch (err) {
            console.error(err);
            setError("대화 내역을 불러오는데 실패했습니다.");
        } finally {
            setLoading(false);
        }
    };

    const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
        event.preventDefault();
        const trimmed = inputValue.trim();
        if (!trimmed || !threadId) return;

        // localAuth 제거: member_id/user_mode는 BFF가 헤더로 주입
        setMessages((prev) => prev.map(m => ({ ...m, isStreaming: false })));
        setMessages((prev) => [...prev, { role: "user", text: trimmed, isStreaming: false }]);
        setInputValue("");
        setError("");
        setLoading(true);
        setStatusLog("AI가 요청을 분석 중입니다...");

        try {
            const response = await fetch(API_URL, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    user_query: trimmed,
                    thread_id: threadId
                }),
            });

            if (!response.ok || !response.body) throw new Error("서버 연결 실패");

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
                            const data = JSON.parse(trimmedLine.replace("data: ", ""));
                            console.log("Stream Data:", data);
                            if (data.type === "answer") {
                                setStatusLog("");
                                setMessages((prev) => {
                                    const updated = [...prev];
                                    const lastIndex = updated.length - 1;
                                    const lastMsg = updated[lastIndex];

                                    if (lastMsg.role === "assistant") {
                                        let nextChunk = data.content;
                                        const prevText = lastMsg.text;
                                        const prevTrimmed = prevText.trimEnd();
                                        if (
                                            prevTrimmed.endsWith("---") &&
                                            !prevText.endsWith("\n") &&
                                            typeof nextChunk === "string" &&
                                            nextChunk.startsWith("##")
                                        ) {
                                            nextChunk = `\n${nextChunk}`;
                                        }
                                        updated[lastIndex] = {
                                            ...lastMsg,
                                            text: prevText + nextChunk
                                        };
                                    }
                                    return updated;
                                });
                            } else if (data.type === "log") {
                                setStatusLog(data.content);
                            } else if (data.type === "error") {
                                setStatusLog(`오류: ${data.content}`);
                            }
                        } catch (e: any) {
                            console.error(e);
                        }
                    }
                }
            }
        } catch (e: any) {
            setError("오류가 발생했습니다.");
        } finally {
            setLoading(false);
            setStatusLog("");
        }
    };

    return (
        <SavedPerfumesProvider memberId={memberId}>
            <PageLayout
                subTitle="AI Perfume Advisor"
                sidebarContext="chat"
                disableContentPadding={true}
                className="flex flex-col h-[100dvh] bg-[#FDFBF8] overflow-hidden overscroll-behavior-none text-black relative font-sans"
            >
                {/* 3. Content Wrapper (Sidebar + Main) */}
                <div className="flex-1 flex relative overflow-hidden pt-[56px] sm:pt-[64px] md:pt-[72px]">

                    {/* ... Sidebars ... (Skipping 50 lines to keep context manageable if needed, but tool replaces contiguous block) */}
                    {/* Actually I need to replace from start of component to end of chat area to be safe? 
                       No, I can target specific range. 
                       I will replace the main chat area div.
                    */}

                    {/* Left Chat Sidebar Container */}
                    <div
                        className={`hidden md:block overflow-hidden transition-all duration-300 ease-in-out ${isSidebarOpen ? "w-64" : "w-0"}`}
                    >
                        <ChatSidebar
                            isOpen={isSidebarOpen}
                            activeThreadId={threadId}
                            onToggle={() => setIsSidebarOpen(!isSidebarOpen)}
                            onNewChat={handleNewChat}
                            onSelectThread={handleSelectThread}
                            loading={loading}
                            showToggleButton={false}
                            currentMemberId={memberId}
                        />
                    </div>

                    {/* Mobile Sidebar */}
                    <div className="md:hidden">
                        <ChatSidebar
                            isOpen={isSidebarOpen}
                            activeThreadId={threadId}
                            onToggle={() => setIsSidebarOpen(!isSidebarOpen)}
                            onNewChat={handleNewChat}
                            onSelectThread={handleSelectThread}
                            loading={loading}
                            showToggleButton={false}
                            currentMemberId={memberId}
                        />
                    </div>

                    {/* Main Chat Area */}
                    <main
                        className={`flex-1 flex flex-col relative bg-[#FDFBF8] overflow-hidden gap-3 transition-transform duration-300 ease-in-out
                            ${isSidebarOpen ? "translate-x-[248px] max-[360px]:translate-x-[232px] md:translate-x-0" : "translate-x-0"}
                        `}
                    >
                        {/* Mobile Shift Overlay */}
                        {isSidebarOpen && (
                            <div
                                className="absolute inset-0 z-[35] bg-black/[0.03] md:hidden cursor-pointer"
                                onClick={() => setIsSidebarOpen(false)}
                            />
                        )}

                        {/* Sidebar Toggle Button */}
                        <div className="absolute top-1.5 left-2 sm:left-3 md:left-4 z-40">
                            <button onClick={() => setIsSidebarOpen(!isSidebarOpen)} className="p-1 md:p-2 hover:bg-gray-100 rounded-lg transition-colors text-black">
                                <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor" className="w-4 h-4 md:w-6 md:h-6">
                                    <rect x="3" y="3" width="18" height="18" rx="2" ry="2" strokeLinecap="round" strokeLinejoin="round" />
                                    <path strokeLinecap="round" strokeLinejoin="round" d="M9 3v18" />
                                </svg>
                            </button>
                        </div>

                        {/* ✅ Smart Scroll-to-Bottom Button */}
                        <div
                            className={`absolute bottom-24 left-1/2 transform -translate-x-1/2 z-50 transition-all duration-300 ${showScrollButton ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-4 pointer-events-none'
                                }`}
                        >
                            <button
                                onClick={forceScrollToBottom}
                                className="flex items-center gap-2 bg-black/80 backdrop-blur-md text-white px-4 py-2 rounded-full shadow-lg hover:bg-black transition-colors"
                            >
                                <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor" className="w-4 h-4">
                                    <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 8.25l-7.5 7.5-7.5-7.5" />
                                </svg>
                                <span className="text-xs font-medium">최신 메시지 보기</span>
                            </button>
                        </div>

                        {/* Chat Messages */}
                        <div
                            ref={chatContainerRef}
                            onScroll={handleScroll}
                            className="flex-1 overflow-y-auto pt-5 pb-3 custom-scrollbar overscroll-behavior-contain touch-pan-y"
                        >
                            <div className={`w-full max-w-5xl mx-auto px-4 ${messages.length === 0 ? "h-full" : ""}`}>
                                <ChatList
                                    messages={messages}
                                    loading={loading}
                                    statusLog={statusLog}
                                    messagesEndRef={messagesEndRef}
                                    userName={displayName}
                                />
                            </div>
                        </div>

                        {/* ✅ 채팅 입력창 (사이드바 간섭 없애고 볼륨감있게 수정 Floating Box) */}
                        {/* [수정 가이드] 채팅 입력창 너비 조절
                            - max-w-5xl: 출력창과 동일하게 맞춤 (균형 유지)
                            - w-full: 화면이 좁아질 때 유연하게 줄어듦
                            - px-4: 좌우 여백 확보
                        */}
                        <div className="shrink-0 px-4 pb-5 z-30 w-full md:w-[80%] max-w-3xl mx-auto">
                            <form onSubmit={handleSubmit} className="relative bg-white rounded-[26px] shadow-sm border border-[#E5E4DE] focus-within:ring-1 focus-within:ring-[#D97757]/30 transition-all">
                                <div className="flex items-center min-h-[50px] pr-2">
                                    <textarea
                                        ref={inputRef}
                                        className="flex-1 w-full bg-transparent py-3 pl-5 text-[#393939] placeholder:text-gray-400 outline-none resize-none text-base custom-scrollbar"
                                        placeholder={placeholder}
                                        rows={1}
                                        value={inputValue}
                                        onChange={(e) => {
                                            setInputValue(e.target.value);
                                            e.target.style.height = 'auto';
                                            e.target.style.height = `${Math.min(e.target.scrollHeight, 120)}px`;
                                        }}
                                        onKeyDown={(e) => {
                                            if (e.key === 'Enter' && !e.shiftKey) {
                                                e.preventDefault();
                                                handleSubmit(e as any);
                                            }
                                        }}
                                        disabled={loading}
                                    />
                                    <div className="flex shrink-0 gap-2 items-center">
                                        <button
                                            className={`
                                                flex items-center justify-center transition-all duration-200 ease-in-out
                                                ${inputValue.trim()
                                                    ? "bg-gradient-to-r from-[#FF9F9F] to-[#D97757] text-white shadow-md hover:shadow-lg hover:scale-105 active:scale-95"
                                                    : "bg-gray-100 text-gray-300 cursor-not-allowed"}
                                            `}
                                            type="submit"
                                            disabled={loading || !inputValue.trim()}
                                            style={{ width: "38px", height: "38px", borderRadius: "50%" }}
                                        >
                                            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" className="w-5 h-5">
                                                <path fillRule="evenodd" d="M10.5 3a.75.75 0 0 1 .75.75v2.25h1.5V3.75a.75.75 0 0 1 1.5 0v3a.75.75 0 0 1-.75.75h-3a.75.75 0 0 1-.75-.75v-3a.75.75 0 0 1 .75-.75ZM7.5 9a2.25 2.25 0 0 1 2.25-2.25h4.5A2.25 2.25 0 0 1 16.5 9v9.75a2.25 2.25 0 0 1-2.25 2.25h-4.5A2.25 2.25 0 0 1 7.5 18.75V9ZM12 11.25a1.5 1.5 0 1 0 0 3 1.5 1.5 0 0 0 0-3Z" clipRule="evenodd" />
                                            </svg>
                                        </button>
                                    </div>
                                </div>
                            </form>
                            <div className="text-center mt-2 md:mt-3">
                                <span className="text-[10px] md:text-[11px] text-gray-400">AI는 가끔 실수할 때도 있습니다. 따뜻한 마음으로 대화해 주세요.</span>
                            </div>
                        </div>
                    </main>

                    {/* Mobile/Nav Overlay */}
                    {/* Mobile/Nav Overlay Strategy */}




                </div>
            </PageLayout>
        </SavedPerfumesProvider >
    );
}
