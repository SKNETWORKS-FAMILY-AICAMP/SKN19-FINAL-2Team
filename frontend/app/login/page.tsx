'use client';

import { FormEvent, useState } from "react";
import Link from "next/link";
import PageLayout from "@/components/common/PageLayout";
import { signIn } from "next-auth/react";
import { useRouter } from "next/navigation";
import { motion } from "framer-motion";

export default function LoginPage() {
  const [loginId, setLoginId] = useState("");
  const [password, setPassword] = useState("");
  const [submitMessage, setSubmitMessage] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const router = useRouter();

  const handleKakaoPopup = () => {
    if (typeof window === "undefined") return;
    const width = 420;
    const height = 640;
    const left = window.screenX + (window.outerWidth - width) / 2;
    const top = window.screenY + (window.outerHeight - height) / 2;
    window.open(
      "/kakao-login",
      "kakao-login",
      `width=${width},height=${height},left=${left},top=${top},resizable=yes,scrollbars=yes`
    );
  };

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setSubmitMessage(null);

    if (!loginId.trim() || !password) {
      setSubmitMessage("아이디와 비밀번호를 입력해주세요.");
      return;
    }

    setIsSubmitting(true);

    try {
      const result = await signIn("credentials", {
        redirect: false,
        email: loginId.trim(),
        password,
      });

      if (result?.error?.startsWith("WITHDRAW_PENDING:")) {
        const memberId = result.error.split(":")[1];
        router.push(`/recover?memberId=${memberId}`);
        return;
      }

      if (!result?.ok) {
        setSubmitMessage("로그인에 실패했습니다. 아이디와 비밀번호를 확인해주세요.");
        return;
      }

      router.push("/");
    } catch {
      setSubmitMessage("로그인 중 오류가 발생했습니다.");
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <PageLayout disableContentPadding className="min-h-screen bg-[#FDFBF8] text-black font-sans flex flex-col">
      <main className="flex-1 flex flex-col items-center pt-[56px] sm:pt-[64px] md:pt-[72px] pb-6 md:pb-20 animate-fade-in-up">
        {/* Full-width Marquee Section - Top of Page */}
        <div className="w-full overflow-hidden border-b border-gray-100 py-3 md:py-6 bg-white/50 select-none mb-6 md:mb-12">
          <motion.div
            className="flex whitespace-nowrap"
            animate={{ x: [0, "-50%"] }}
            transition={{
              duration: 25,
              repeat: Infinity,
              ease: "linear"
            }}
          >
            {[1, 2].map((i) => (
              <div key={i} className="flex items-center gap-12 px-6">
                <span className="text-2xl md:text-5xl font-black font-serif italic text-black tracking-tighter uppercase">Welcome Back •</span>
                <span className="text-2xl md:text-5xl font-black font-serif italic text-transparent tracking-tighter uppercase" style={{ WebkitTextStroke: "1px black" }}>Scentence •</span>
                <span className="text-2xl md:text-5xl font-black font-serif italic text-black tracking-tighter uppercase">Welcome Back •</span>
                <span className="text-2xl md:text-5xl font-black font-serif italic text-transparent tracking-tighter uppercase" style={{ WebkitTextStroke: "1px black" }}>Scentence •</span>
              </div>
            ))}
          </motion.div>
        </div>

        <div className="w-full max-w-xl px-4">
          <div className="mb-6 md:mb-12 text-center animate-fade-in">
            <p className="text-xs md:text-sm text-gray-600 font-medium tracking-[0.2em]">
              당신의 취향, 그 이상의 발견
            </p>
          </div>

          <form onSubmit={handleSubmit} className="space-y-4 md:space-y-12">

            {/* Inputs Section */}
            <div className="space-y-3 md:space-y-8">
              {/* ID Input */}
              <div className="space-y-2 group">
                <label htmlFor="loginId" className="block text-xs font-bold text-gray-600 uppercase tracking-wider group-focus-within:text-black transition-colors">
                  ID (Email)
                </label>
                <input
                  id="loginId"
                  name="loginId"
                  type="text"
                  placeholder="아이디(이메일)를 입력하세요"
                  value={loginId}
                  onChange={(event) => setLoginId(event.target.value)}
                  className="w-full border-b border-gray-200 py-2 md:py-3 text-base focus:border-black focus:outline-none transition-colors bg-transparent placeholder-gray-400"
                />
              </div>

              {/* Password Input */}
              <div className="space-y-2 group">
                <div className="flex justify-between items-center">
                  <label htmlFor="password" className="block text-xs font-bold text-gray-600 uppercase tracking-wider group-focus-within:text-black transition-colors">
                    Password
                  </label>
                </div>
                <input
                  id="password"
                  name="password"
                  type="password"
                  placeholder="비밀번호를 입력하세요"
                  value={password}
                  onChange={(event) => setPassword(event.target.value)}
                  className="w-full border-b border-gray-200 py-2 md:py-3 text-base focus:border-black focus:outline-none transition-colors bg-transparent placeholder-gray-400"
                />
              </div>
            </div>

            {/* Error Message */}
            {submitMessage && (
              <div className="p-3 bg-red-50 text-red-600 text-xs rounded-lg text-center font-medium animate-pulse">
                {submitMessage}
              </div>
            )}

            {/* Buttons Section */}
            <div className="space-y-4 md:space-y-5 pt-2 md:pt-4">
              <button
                type="submit"
                disabled={isSubmitting}
                className={`w-full py-3 md:py-4 rounded-full font-bold text-lg transition-all shadow-md ${isSubmitting
                  ? "bg-gray-200 text-gray-400 cursor-not-allowed"
                  : "bg-black text-white hover:bg-gray-900 active:scale-[0.99]"
                  }`}
              >
                {isSubmitting ? "로그인 중..." : "로그인"}
              </button>

              <div className="relative flex py-2 items-center">
                <div className="flex-grow border-t border-gray-100"></div>
                <span className="flex-shrink-0 mx-4 text-[10px] text-gray-300 font-medium tracking-widest uppercase">OR</span>
                <div className="flex-grow border-t border-gray-100"></div>
              </div>

              <button
                type="button"
                onClick={handleKakaoPopup}
                className="w-full bg-[#FEE500] text-[#3c1e1e] py-3 md:py-4 rounded-full font-bold text-lg flex items-center justify-center gap-2.5 hover:bg-[#ffe812] transition-colors active:scale-[0.99] shadow-md"
              >
                <svg viewBox="0 0 24 24" fill="currentColor" className="w-5 h-5">
                  <path d="M12 3C5.373 3 0 7.373 0 12.768c0 3.657 2.456 6.829 6.138 8.49L4.2 24l5.414-3.606c.767.098 1.556.15 2.386.15 6.627 0 12-4.373 12-9.768C24 7.373 18.627 3 12 3z" />
                </svg>
                <span>카카오 로그인</span>
              </button>
            </div>

            {/* Footer Links - Signup CTA */}
            <div className="mt-4 md:mt-12 pt-4 md:pt-8 border-t border-gray-100 flex flex-col items-center">
              <p className="text-xs md:text-sm text-gray-500 mb-2 md:mb-4">아직 계정이 없으신가요?</p>
              <Link
                href="/signup"
                className="w-full py-3 md:py-4 rounded-xl border border-gray-200 text-black font-bold text-center hover:bg-gray-50 hover:border-black transition-all"
              >
                회원가입
              </Link>
            </div>

          </form>
        </div>
      </main>
    </PageLayout>
  );
}
