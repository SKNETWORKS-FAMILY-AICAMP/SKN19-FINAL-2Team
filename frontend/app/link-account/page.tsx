"use client";

import { useState, useEffect, Suspense } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import { signIn } from "next-auth/react";
import Link from "next/link";

const API_URL = "/api";

function LinkAccountContent() {
    const searchParams = useSearchParams();
    const router = useRouter();

    const [email, setEmail] = useState("");
    const [kakaoId, setKakaoId] = useState("");
    const [kakaoNickname, setKakaoNickname] = useState("");
    const [kakaoProfileImage, setKakaoProfileImage] = useState("");
    const [password, setPassword] = useState("");
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState("");
    const [success, setSuccess] = useState(false);

    useEffect(() => {
        setEmail(searchParams.get("email") || "");
        setKakaoId(searchParams.get("kakao_id") || "");
        setKakaoNickname(searchParams.get("kakao_nickname") || "");
        setKakaoProfileImage(searchParams.get("kakao_profile_image") || "");
    }, [searchParams]);

    const handleLink = async (e: React.FormEvent) => {
        e.preventDefault();
        setLoading(true);
        setError("");

        try {
            const response = await fetch(`${API_URL}/users/link-account`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    email,
                    password,
                    kakao_id: kakaoId,
                    kakao_nickname: kakaoNickname,
                    kakao_profile_image: kakaoProfileImage
                })
            });

            const data = await response.json();

            if (!response.ok) {
                setError(data.detail || "계정 연결에 실패했습니다.");
                setLoading(false);
                return;
            }

            // 성공 시
            setSuccess(true);

            // 잠시 후 카카오 로그인으로 리다이렉트 (이제 연결되었으므로 정상 로그인됨)
            setTimeout(() => {
                signIn("kakao", { callbackUrl: "/" });
            }, 2000);

        } catch (err) {
            setError("서버 연결에 실패했습니다.");
            setLoading(false);
        }
    };

    const handleSkip = () => {
        // 연결하지 않고 새 계정으로 진행하려면 별도 처리 필요
        // 현재는 홈으로 이동
        router.push("/");
    };

    if (success) {
        return (
            <div className="min-h-screen bg-[#FDFBF8] flex items-center justify-center p-6">
                <div className="bg-white rounded-3xl shadow-xl p-10 max-w-md w-full text-center">
                    <div className="text-6xl mb-6">✅</div>
                    <h1 className="text-2xl font-bold text-[#333] mb-4">계정 연결 완료!</h1>
                    <p className="text-gray-600 mb-6">
                        카카오 계정이 기존 계정과 연결되었습니다.<br />
                        잠시 후 자동으로 로그인됩니다.
                    </p>
                    <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-[#C5A55D] mx-auto"></div>
                </div>
            </div>
        );
    }

    return (
        <div className="min-h-screen bg-[#FDFBF8] flex items-center justify-center p-6">
            <div className="bg-white rounded-3xl shadow-xl p-10 max-w-md w-full">
                <Link href="/" className="text-xl font-bold tracking-tight text-[#333] hover:opacity-70 transition block text-center mb-8">
                    Scentence
                </Link>

                <div className="text-center mb-8">
                    <div className="text-5xl mb-4">🔗</div>
                    <h1 className="text-2xl font-bold text-[#333] mb-3">계정 연결</h1>
                    <p className="text-gray-600 text-sm">
                        동일한 이메일로 가입된 계정이 있습니다.<br />
                        비밀번호를 입력하여 카카오 계정을 연결하세요.
                    </p>
                </div>

                {/* 연결할 계정 정보 */}
                <div className="bg-[#FAF8F5] rounded-2xl p-5 mb-6">
                    <div className="flex items-center gap-4">
                        {kakaoProfileImage ? (
                            <img
                                src={kakaoProfileImage}
                                alt="프로필"
                                className="w-14 h-14 rounded-full object-cover"
                            />
                        ) : (
                            <div className="w-14 h-14 rounded-full bg-gradient-to-tr from-yellow-400 to-yellow-500 flex items-center justify-center text-white text-2xl">
                                K
                            </div>
                        )}
                        <div className="flex-1">
                            <p className="font-bold text-[#333]">{kakaoNickname || "카카오 사용자"}</p>
                            <p className="text-sm text-gray-500">{email}</p>
                        </div>
                    </div>
                </div>

                <form onSubmit={handleLink} className="space-y-5">
                    <div>
                        <label className="block text-sm font-medium text-gray-700 mb-2">
                            기존 계정 비밀번호
                        </label>
                        <input
                            type="password"
                            value={password}
                            onChange={(e) => setPassword(e.target.value)}
                            placeholder="비밀번호를 입력하세요"
                            className="w-full px-4 py-3 border border-gray-200 rounded-xl focus:ring-2 focus:ring-[#C5A55D] focus:border-transparent outline-none transition"
                            required
                        />
                    </div>

                    {error && (
                        <div className="bg-red-50 border border-red-200 text-red-600 px-4 py-3 rounded-xl text-sm">
                            {error}
                        </div>
                    )}

                    <button
                        type="submit"
                        disabled={loading || !password}
                        className="w-full py-3 bg-[#C5A55D] text-white font-bold rounded-xl hover:bg-[#B09045] transition disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                        {loading ? "연결 중..." : "계정 연결하기"}
                    </button>
                </form>

                <div className="mt-6 text-center">
                    <button
                        onClick={handleSkip}
                        className="text-sm text-gray-500 hover:text-gray-700 underline"
                    >
                        연결하지 않고 홈으로 돌아가기
                    </button>
                </div>

                <div className="mt-8 pt-6 border-t border-gray-100 text-center">
                    <p className="text-xs text-gray-400">
                        계정을 연결하면 하나의 계정으로<br />
                        카카오 로그인과 이메일 로그인을 모두 사용할 수 있습니다.
                    </p>
                </div>
            </div>
        </div>
    );
}

export default function LinkAccountPage() {
    return (
        <Suspense fallback={
            <div className="min-h-screen bg-[#FDFBF8] flex items-center justify-center">
                <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-[#C5A55D]"></div>
            </div>
        }>
            <LinkAccountContent />
        </Suspense>
    );
}
