'use client';

import { useEffect, useState, Suspense } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import PageLayout from "@/components/common/PageLayout";

function RecoverPageContent() {
  const searchParams = useSearchParams();
  const memberId = searchParams.get("memberId");
  const [nickname, setNickname] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [isRecovering, setIsRecovering] = useState(false);
  const apiBaseUrl = "/api";

  useEffect(() => {
    if (!memberId) return;
    fetch(`${apiBaseUrl}/users/profile/${memberId}`)
      .then((res) => (res.ok ? res.json() : null))
      .then((data) => {
        setNickname(data?.nickname || "회원");
      })
      .catch(() => setNickname("회원"));
  }, [apiBaseUrl, memberId]);

  const handleRecover = async () => {
    if (!memberId) return;
    setIsRecovering(true);
    setMessage(null);
    try {
      const response = await fetch(`${apiBaseUrl}/users/recover?member_id=${memberId}`, {
        method: "POST",
      });
      if (!response.ok) {
        const data = await response.json().catch(() => null);
        setMessage(data?.detail || "계정 복구에 실패했습니다.");
        return;
      }
      // 로컬 스토리지에 저장하는 로직은 제거
      // if (typeof window !== "undefined") {
      //   localStorage.setItem(
      //     "localAuth",
      //     JSON.stringify({
      //       memberId,
      //       nickname,
      //       loggedInAt: new Date().toISOString(),
      //     })
      //   );
      // }
      window.location.href = "/login";
    } catch (error) {
      setMessage("계정 복구에 실패했습니다.");
    } finally {
      setIsRecovering(false);
    }
  };

  return (
    <PageLayout className="min-h-screen bg-white text-black flex flex-col">

      <main className="flex-1 px-5 py-8 w-full max-w-md mx-auto pt-[72px] space-y-6">
        <div>
          <h2 className="text-2xl font-bold">계정 복구</h2>
          <p className="text-sm text-[#666]">현재 {nickname ?? "회원"}님은 탈퇴 요청 상태입니다.</p>
          <p className="text-sm text-[#666]">계정을 복구하시겠습니까?</p>
        </div>

        {message && <p className="text-sm text-red-600">{message}</p>}

        <button
          type="button"
          disabled={isRecovering}
          onClick={handleRecover}
          className={`w-full py-3 rounded-xl font-bold transition ${isRecovering
            ? "bg-gray-300 text-gray-500 cursor-not-allowed"
            : "bg-black text-white hover:opacity-90"
            }`}
        >
          계정 복구
        </button>
      </main>
    </PageLayout>
  );
}

export default function RecoverPage() {
  return (
    <Suspense fallback={<div className="min-h-screen flex items-center justify-center">로딩 중...</div>}>
      <RecoverPageContent />
    </Suspense>
  );
}
