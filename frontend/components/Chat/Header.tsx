"use client";

// ✅ 헤더 조각 (Header.tsx)
// 화면 상단의 서비스 이름과 모바일용 버튼을 담당합니다.

interface HeaderProps {
    onNewChat: () => void;
    loading: boolean;
}

const Header = ({ onNewChat, loading }: HeaderProps) => {
    return (
        <header className="flex items-center space-x-2 mb-4">

            {/* ✅ 4. 헤더의 왼쪽 부분 추가 */}
            <div className="flex-1">
                <div className="text-xs md:text-sm uppercase tracking-[0.1em] text-[#8E8E8E]">Scent + Sentence</div>
                <div className="flex items-center justify-between gap-2">
                    <h1 className="text-2xl md:text-3xl font-semibold text-[#393939]">SCENTENCE</h1>

                    {/* 📱 모바일에서만 보이는 '새 대화' 버튼 (md 이상에서는 숨김) */}
                    <button
                        onClick={onNewChat}
                        disabled={loading}
                        className="group flex md:hidden items-center gap-2 rounded-full border border-[#E5E4DE] bg-white px-4 py-2 text-xs font-medium text-[#575757] transition-all hover:bg-[#F2F1EE]"
                    >
                        <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" className="w-3 h-3"><path strokeLinecap="round" strokeLinejoin="round" d="M16 9h5M3 19v-5m0 0h5m-5 0l3 3a8 8 0 0013-3M4 10a8 8 0 0113-3l3 3m0-5v5" /></svg>
                        새 대화
                    </button>
                </div>
                <div className="text-[12px] md:text-[14px] text-[#8E8E8E]">AI 향수 큐레이션 플랫폼</div>
            </div>
        </header>
    );
};

export default Header;