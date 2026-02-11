"use client";

import { type MouseEvent, useEffect, useRef, useState } from "react";
import { useSession } from "next-auth/react";

const BACKEND_URL = "/api";

interface ChatRoom {
    thread_id: string;
    title: string;
    last_chat_dt: string;
}

interface SidebarProps {
    isOpen: boolean;
    activeThreadId?: string;
    onToggle: () => void;
    onNewChat: () => void;
    onSelectThread: (id: string) => void;
    loading: boolean;
    showToggleButton?: boolean;
    currentMemberId?: number | null; // ✅ [수정] 부모(Page)로부터 전달받는 유저 ID
}

const Sidebar = ({ isOpen, activeThreadId, onToggle, onNewChat, onSelectThread, loading, showToggleButton = false, currentMemberId }: SidebarProps) => {
    const { data: session } = useSession(); // 카카오 로그인 세션
    const [chatRooms, setChatRooms] = useState<ChatRoom[]>([]);
    const [openMenuThreadId, setOpenMenuThreadId] = useState<string | null>(null);
    const [pendingDeleteRoom, setPendingDeleteRoom] = useState<ChatRoom | null>(null);
    const [isDeletingRoom, setIsDeletingRoom] = useState(false);
    const menuRef = useRef<HTMLDivElement | null>(null);

    const resolveMemberId = () => {
        if (typeof currentMemberId === "number" && currentMemberId > 0) {
            return currentMemberId;
        }
        const sessionUserId = Number(session?.user?.id);
        if (Number.isFinite(sessionUserId) && sessionUserId > 0) {
            return sessionUserId;
        }
        return null;
    };

    const openDeleteModal = (room: ChatRoom) => {
        setOpenMenuThreadId(null);
        setPendingDeleteRoom(room);
    };

    const handleDeleteRoom = async () => {
        if (!pendingDeleteRoom || isDeletingRoom) return;

        const memberId = resolveMemberId();
        if (!memberId) return;
        const room = pendingDeleteRoom;

        try {
            setIsDeletingRoom(true);
            const response = await fetch(`${BACKEND_URL}/chat/rooms/${memberId}/${room.thread_id}`, {
                method: "DELETE",
            });
            if (!response.ok) {
                throw new Error(`Delete failed with status ${response.status}`);
            }

            const result = await response.json();
            if (!result?.ok) {
                throw new Error("Delete response is invalid");
            }

            setChatRooms((prev) => prev.filter((item) => item.thread_id !== room.thread_id));
            setOpenMenuThreadId(null);
            setPendingDeleteRoom(null);

            if (activeThreadId === room.thread_id) {
                onNewChat();
            }
        } catch (err) {
            console.error("History Delete Error:", err);
            window.alert("대화 삭제에 실패했습니다. 잠시 후 다시 시도해주세요.");
        } finally {
            setIsDeletingRoom(false);
        }
    };

    const handleShareRoom = async (room: ChatRoom) => {
        const shareUrl = `${window.location.origin}/chat?threadId=${encodeURIComponent(room.thread_id)}`;
        const shareTitle = room.title?.trim() || "Scentence 채팅";

        try {
            if (navigator.share) {
                await navigator.share({
                    title: shareTitle,
                    text: "Scentence 채팅 공유",
                    url: shareUrl,
                });
            } else {
                await navigator.clipboard.writeText(shareUrl);
                window.alert("공유 링크가 복사되었습니다.");
            }
            setOpenMenuThreadId(null);
        } catch (err) {
            // 사용자가 공유 시트를 닫은 경우 등은 조용히 무시
            console.debug("Share cancelled or failed:", err);
        }
    };

    const handleMenuButtonClick = (event: MouseEvent<HTMLButtonElement>, threadId: string) => {
        event.stopPropagation();
        setOpenMenuThreadId((prev) => (prev === threadId ? null : threadId));
    };

    // [1] 사이드바가 열리거나 유저 ID가 변경될 때 목록 불러오기
    useEffect(() => {
        console.log("[Sidebar Debug] Current Props:", { isOpen, currentMemberId, sessionUserId: session?.user?.id });

        // 1. Props로 전달받은 ID가 있으면 최우선 사용
        if (currentMemberId) {
            console.log("[Sidebar] Fetching rooms for member_id (Prop):", currentMemberId);
            fetch(`${BACKEND_URL}/chat/rooms/${currentMemberId}`)
                .then(res => {
                    console.log("[Sidebar] API Response Status:", res.status);
                    return res.json();
                })
                .then(data => {
                    console.log("[Sidebar] Loaded Rooms:", data);
                    setChatRooms(data.rooms || []);
                })
                .catch(err => console.error("History Load Error:", err));
            return;
        }

        // 2. Props가 없으면 세션 기반으로만 조회
        if (session?.user?.id) {
            if (isOpen) {
                console.log("[Sidebar] Fetching rooms for member_id (Session):", session.user.id);
                fetch(`${BACKEND_URL}/chat/rooms/${session.user.id}`)
                    .then(res => res.json())
                    .then(data => setChatRooms(data.rooms || []))
                    .catch(err => console.error("History Load Error:", err));
            }
            return;
        }
    }, [isOpen, session, currentMemberId]);

    useEffect(() => {
        const handleOutsideClick = (event: globalThis.MouseEvent) => {
            const target = event.target;
            if (!(target instanceof Node)) return;
            if (target instanceof Element && target.closest("[data-history-menu-trigger='true']")) {
                return;
            }
            if (!menuRef.current) return;
            if (!menuRef.current.contains(target)) {
                setOpenMenuThreadId(null);
            }
        };

        const handleEsc = (event: KeyboardEvent) => {
            if (event.key === "Escape") {
                if (pendingDeleteRoom) {
                    setPendingDeleteRoom(null);
                    return;
                }
                setOpenMenuThreadId(null);
            }
        };

        document.addEventListener("mousedown", handleOutsideClick);
        document.addEventListener("keydown", handleEsc);
        return () => {
            document.removeEventListener("mousedown", handleOutsideClick);
            document.removeEventListener("keydown", handleEsc);
        };
    }, [pendingDeleteRoom]);

    useEffect(() => {
        if (!isOpen) {
            setOpenMenuThreadId(null);
        }
    }, [isOpen]);

    return (
        <>
            {showToggleButton && (
                <button onClick={onToggle} className="fixed top-4 left-4 z-[60] p-2 hover:bg-[#F2F1EE] rounded-lg transition-colors bg-white/50 backdrop-blur-sm md:bg-transparent">
                    <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" className="w-6 h-6 text-[#393939]">
                        <path strokeLinecap="round" strokeLinejoin="round" d="M3.75 6.75h16.5M3.75 12h16.5m-16.5 5.25h16.5" />
                    </svg>
                </button>
            )}

            {/* [SIDEBAR CONTAINER] md:relative로 변경하여 Flex 밀어내기 지원 */}
            <div className={`fixed top-[56px] sm:top-[64px] bottom-0 left-0 z-[40] w-[248px] max-[360px]:w-[232px] md:w-64 bg-white border-r border-[#E5E4DE] transition-transform duration-300 transform 
                ${isOpen ? "translate-x-0" : "-translate-x-full"} 
                md:relative md:top-0 md:translate-x-0 md:z-0 md:h-full`}>
                <div className="flex h-full flex-col p-4 pt-4">
                    <div className="flex justify-between items-center mb-6 px-2">
                        <span className="text-[10px] font-bold tracking-widest text-[#8E8E8E]">RECENT HISTORY</span>
                        {/* [수정] 중복 X 버튼 제거 (비상식적 UI 개선) */}
                    </div>

                    <button onClick={onNewChat} disabled={loading} className="group flex items-center justify-center gap-2 rounded-xl border border-[#E5E4DE] bg-[#FAF8F5] py-3 text-sm font-medium text-[#393939] transition-all hover:bg-[#F2F1EE] disabled:opacity-50">
                        <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" className="h-5 w-5 transition-transform group-hover:rotate-180"><path strokeLinecap="round" strokeLinejoin="round" d="M16 9h5M3 19v-5m0 0h5m-5 0l3 3a8 8 0 0013-3M4 10a8 8 0 0113-3l3 3m0-5v5" /></svg>
                        새로운 대화 시작
                    </button>

                    {/* ✅ 실제 대화 목록 렌더링 영역 */}
                    <div className="mt-8 -mr-4 pr-2 flex-1 overflow-y-auto overflow-x-visible custom-scrollbar space-y-1">
                        {chatRooms.length > 0 ? (
                            chatRooms.map((room) => (
                                <div key={room.thread_id} className="group relative">
                                    <button
                                        onClick={() => {
                                            setOpenMenuThreadId(null);
                                            onSelectThread(room.thread_id);
                                        }}
                                        // [수정] 클릭 후 회색 음영 남지 않도록 active active highlight 제거. 호버 시에만 반응.
                                        className={`w-full text-left px-3 py-3 pr-14 rounded-xl transition-colors hover:bg-[#FAF8F5] ${activeThreadId === room.thread_id ? "font-semibold text-[#393939]" : ""}`}
                                    >
                                        <p className="text-sm text-[#393939] truncate">{room.title || "이전 대화"}</p>
                                        <p className="text-[10px] text-[#BCBCBC] mt-1">{new Date(room.last_chat_dt).toLocaleDateString()}</p>
                                    </button>

                                    <button
                                        type="button"
                                        onMouseDown={(event) => event.stopPropagation()}
                                        onClick={(event) => handleMenuButtonClick(event, room.thread_id)}
                                        aria-label="대화 메뉴"
                                        aria-expanded={openMenuThreadId === room.thread_id}
                                        data-history-menu-trigger="true"
                                        className={`absolute right-3 top-1/2 -translate-y-1/2 h-7 w-7 rounded-md text-[#8E8E8E] hover:bg-[#F2F1EE] hover:text-[#393939] transition ${
                                            openMenuThreadId === room.thread_id
                                                ? "opacity-100"
                                                : "opacity-100 md:opacity-0 md:group-hover:opacity-100 md:group-focus-within:opacity-100"
                                        }`}
                                    >
                                        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" className="mx-auto h-4 w-4">
                                            <circle cx="12" cy="5" r="2" />
                                            <circle cx="12" cy="12" r="2" />
                                            <circle cx="12" cy="19" r="2" />
                                        </svg>
                                    </button>

                                    {openMenuThreadId === room.thread_id && (
                                        <div
                                            ref={menuRef}
                                            className="absolute right-3 top-[calc(100%-2px)] z-20 w-28 rounded-lg border border-[#E5E4DE] bg-white shadow-[0_8px_20px_rgba(0,0,0,0.08)] py-1"
                                        >
                                            <button
                                                type="button"
                                                onClick={(event) => {
                                                    event.preventDefault();
                                                    event.stopPropagation();
                                                    handleShareRoom(room);
                                                }}
                                                className="w-full px-3 py-2 text-left text-sm text-[#393939] hover:bg-[#FAF8F5]"
                                            >
                                                공유
                                            </button>
                                            <button
                                                type="button"
                                                onClick={(event) => {
                                                    event.preventDefault();
                                                    event.stopPropagation();
                                                    openDeleteModal(room);
                                                }}
                                                className="w-full px-3 py-2 text-left text-sm text-[#B33A3A] hover:bg-[#FAF8F5]"
                                            >
                                                삭제
                                            </button>
                                        </div>
                                    )}
                                </div>
                            ))
                        ) : (
                            <p className="px-2 text-xs text-[#BCBCBC]">이전 대화가 없습니다.</p>
                        )}
                    </div>
                </div>
            </div>

            {pendingDeleteRoom && (
                <div
                    className="fixed inset-0 z-[80] flex items-center justify-center bg-black/35 backdrop-blur-[1px] p-4"
                    onClick={() => {
                        if (!isDeletingRoom) setPendingDeleteRoom(null);
                    }}
                >
                    <div
                        className="w-full max-w-sm rounded-2xl border border-[#E5E4DE] bg-white p-5 shadow-[0_20px_50px_rgba(0,0,0,0.2)]"
                        onClick={(event) => event.stopPropagation()}
                    >
                        <h3 className="text-[17px] font-semibold text-[#393939]">대화 삭제</h3>
                        <p className="mt-2 text-sm leading-relaxed text-[#6F6A62]">
                            &quot;{pendingDeleteRoom.title?.trim() || "이전 대화"}&quot; 대화를 삭제할까요?
                        </p>
                        <p className="mt-1 text-xs text-[#9A958E]">삭제 후 복구할 수 없습니다.</p>

                        <div className="mt-5 flex items-center justify-end gap-2">
                            <button
                                type="button"
                                disabled={isDeletingRoom}
                                onClick={() => setPendingDeleteRoom(null)}
                                className="rounded-lg border border-[#E5E4DE] px-4 py-2 text-sm font-medium text-[#6F6A62] hover:bg-[#FAF8F5] disabled:opacity-50"
                            >
                                취소
                            </button>
                            <button
                                type="button"
                                disabled={isDeletingRoom}
                                onClick={handleDeleteRoom}
                                className="rounded-lg bg-[#B33A3A] px-4 py-2 text-sm font-semibold text-white hover:bg-[#9f3333] disabled:opacity-50"
                            >
                                {isDeletingRoom ? "삭제 중..." : "삭제"}
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </>
    );
};

export default Sidebar;
