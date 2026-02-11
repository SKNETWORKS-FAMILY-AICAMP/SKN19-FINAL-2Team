'use client';

import { useEffect } from "react";
import { signIn } from "next-auth/react";

export default function KakaoLoginPage() {
  useEffect(() => {
    signIn("kakao", { callbackUrl: "/kakao-login/callback" });
  }, []);

  return (
    <div className="min-h-screen flex items-center justify-center bg-white text-black">
      <p className="text-sm text-[#555]">카카오 로그인으로 이동 중입니다...</p>
    </div>
  );
}
