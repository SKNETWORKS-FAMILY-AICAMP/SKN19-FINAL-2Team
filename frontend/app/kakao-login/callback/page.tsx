'use client';

import { useEffect } from "react";

export default function KakaoLoginCallbackPage() {
  useEffect(() => {
    if (typeof window === "undefined") return;
    if (window.opener && !window.opener.closed) {
      window.opener.location.href = "/";
      window.close();
    } else {
      window.location.href = "/";
    }
  }, []);

  return (
    <div className="min-h-screen flex items-center justify-center bg-white text-black">
      <p className="text-sm text-[#555]">로그인 처리 중입니다...</p>
    </div>
  );
}
