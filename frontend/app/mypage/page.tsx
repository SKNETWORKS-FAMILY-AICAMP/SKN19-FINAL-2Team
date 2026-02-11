'use client';

import { FormEvent, useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { useSession } from "next-auth/react";
import PageLayout from "@/components/common/PageLayout";
import ImageCropperModal from '@/components/common/ImageCropperModal';
import { motion, AnimatePresence } from "framer-motion";

interface ProfileData {
  member_id: string;
  role_type: string | null;
  join_channel: string | null;
  sns_join_yn: string | null;
  email_alarm_yn: string | null;
  sns_alarm_yn: string | null;
  name: string | null;
  nickname: string | null;
  sex: string | null;
  phone_no: string | null;
  address: string | null;
  email: string | null;
  sub_email: string | null;
  profile_image_url: string | null;
}

export default function MyPage() {
  const { data: session, update } = useSession();

  const [memberId, setMemberId] = useState<string | null>(null);
  const [profile, setProfile] = useState<ProfileData | null>(null);
  const [nickname, setNickname] = useState("");
  const [profileImageUrl, setProfileImageUrl] = useState("");
  const [name, setName] = useState("");
  const [sex, setSex] = useState<"M" | "F" | "">("");
  const [phoneNo, setPhoneNo] = useState("");
  const [address, setAddress] = useState("");
  const [email, setEmail] = useState("");
  const [subEmail, setSubEmail] = useState("");
  const [emailMarketing, setEmailMarketing] = useState(false);
  const [snsMarketing, setSnsMarketing] = useState(false);
  const [nicknameStatus, setNicknameStatus] = useState<"idle" | "checking" | "available" | "unavailable" | "invalid">("idle");
  const [profileMessage, setProfileMessage] = useState<string | null>(null);
  const [passwordMessage, setPasswordMessage] = useState<string | null>(null);
  const [isSubmittingProfile, setIsSubmittingProfile] = useState(false);
  const [isSubmittingPassword, setIsSubmittingPassword] = useState(false);
  const [loadMessage, setLoadMessage] = useState<string | null>(null);
  const [isUploadingImage, setIsUploadingImage] = useState(false);
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [selectedFile, setSelectedFile] = useState<string | null>(null); // 자르기 전 원본 이미지 URL
  const [isCropperOpen, setIsCropperOpen] = useState(false); // 모달 열림 여부

  // [기존 코드 주석 처리] 환경 변수에 의존하던 방식
  // const apiBaseUrl = process.env.NEXT_PUBLIC_API_URL || "";

  // [표준화] 이미지 경로 결정 로직 수정
  // 1. 이미 http로 시작하는 전체 경로(S3, 카카오 등)라면 그대로 사용합니다.
  // 2. /uploads/로 시작하는 상대 경로라면 그대로 사용합니다. (Next.js rewrites 활용)
  // 3. 사진이 없는 경우 기본 이미지를 보여줍니다.
  // 4. [변경점] apiBaseUrl 대신 /api 프록시를 사용하거나 상대 경로를 유지하여 호환성을 높입니다.
  const resolvedProfileImageUrl = profileImageUrl
    ? (profileImageUrl.startsWith("http") || profileImageUrl.startsWith("/uploads"))
      ? profileImageUrl
      : `/api${profileImageUrl}` // `${apiBaseUrl}${profileImageUrl}` 대신 사용
    : (session?.user?.image || "/default_profile.png"); // [추가] DB 이미지 없으면 세션/기본 이미지 폴백
  const checkedSnsJoinYn = profile?.sns_join_yn; // existing logic check
  const showPasswordSection = profile?.sns_join_yn !== "Y";

  const displayName = session?.user?.name || profile?.nickname || profile?.name || profile?.email?.split('@')[0] || "User";

  useEffect(() => {
    // localAuth 제거: 세션 id만 사용
    if (session?.user?.id) {
      setMemberId(String(session.user.id));
    } else {
      setMemberId(null);
    }
  }, [session]);





  useEffect(() => {
    if (!memberId) return;
    const controller = new AbortController();

    const loadProfile = async () => {
      try {
        /**
         * [수정 이유: 페이지별 통신 방식 표준화]
         * 메인 페이지와 동일하게 '/api' 프록시를 사용하여 
         * 로컬/배포 환경 구분 없이 안정적으로 프로필 정보를 가져오도록 수정합니다.
         */
        const response = await fetch(`/api/users/profile/${memberId}`, {
          signal: controller.signal,
        });
        if (!response.ok) {
          if (response.status === 404) {
            // [추가] DB에 정보가 없더라도 카카오 세션 정보로 폼을 채워주는 UX 개선
            if (session?.user) {
              setProfile(null);
              setNickname(session.user.name || "");
              setEmail(session.user.email || "");
              setProfileImageUrl(session.user.image || "");
            } else {
              setLoadMessage("회원 정보를 찾을 수 없습니다. 다시 로그인해주세요.");
            }
          }
          return;
        }
        const data = (await response.json()) as ProfileData;
        setProfile(data);
        if (data?.member_id) {
          setMemberId(String(data.member_id));
        }
        // [수정] DB 값이 없으면 세션 값이라도 보여주기 (nullish coalescing)
        setNickname(data.nickname || session?.user?.name || "");
        setProfileImageUrl(data.profile_image_url || session?.user?.image || "");
        setName(data.name || "");
        setSex((data.sex as "M" | "F" | "") || "");
        setPhoneNo(data.phone_no || "");
        setAddress(data.address || "");
        setEmail(data.email || session?.user?.email || "");
        setSubEmail(data.sub_email || "");
        setEmailMarketing(data.email_alarm_yn === "Y");
        setSnsMarketing(data.sns_alarm_yn === "Y");
      } catch (error) {
        return;
      }
    };

    loadProfile();

    return () => controller.abort();
  }, [memberId]);

  useEffect(() => {
    if (!nickname) {
      setNicknameStatus("idle");
      return;
    }

    const isValid = /^[A-Za-z0-9가-힣]{2,12}$/.test(nickname);
    if (!isValid) {
      setNicknameStatus("invalid");
      return;
    }

    const timeoutId = window.setTimeout(async () => {
      if (!memberId) return;
      setNicknameStatus("checking");
      try {
        const response = await fetch(
          `/api/users/nickname/check?nickname=${encodeURIComponent(nickname)}&member_id=${memberId}`
        );
        const data = await response.json();
        setNicknameStatus(data.available ? "available" : "unavailable");
      } catch (error) {
        setNicknameStatus("idle");
      }
    }, 350);

    return () => window.clearTimeout(timeoutId);
  }, [memberId, nickname]);

  const nicknameHint = useMemo(() => {
    if (nicknameStatus === "invalid") return "2~12자의 한글/영문/숫자만 가능합니다.";
    if (nicknameStatus === "available") return "사용 가능한 닉네임입니다.";
    if (nicknameStatus === "unavailable") return "이미 사용 중인 닉네임입니다.";
    if (nicknameStatus === "checking") return "중복 확인 중...";
    return null;
  }, [nicknameStatus]);

  const handleProfileSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!memberId) return;

    setIsSubmittingProfile(true);
    setProfileMessage(null);

    try {
      const response = await fetch(`/api/users/profile/${memberId}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          nickname: nickname.trim() || null,
          profile_image_url: profileImageUrl.trim() || null,
          name: name.trim() || null,
          sex: sex || null,
          phone_no: phoneNo.trim() || null,
          address: address.trim() || null,
          email: email.trim() || null,
          sub_email: subEmail.trim() || null,
          email_alarm_yn: emailMarketing ? "Y" : "N",
          sns_alarm_yn: snsMarketing ? "Y" : "N",
        }),
      });

      if (!response.ok) {
        const data = await response.json().catch(() => null);
        setProfileMessage(data?.detail || "회원정보 수정에 실패했습니다.");
        return;
      }

      // localAuth 제거: 세션 동기화는 NextAuth에서 처리

      await update({ name: nickname });
      setProfileMessage("회원정보가 저장되었습니다.");
    } catch (error) {
      setProfileMessage("회원정보 수정에 실패했습니다.");
    } finally {
      setIsSubmittingProfile(false);
    }
  };

  // 크롭 완료 후 실행될 함수 (실제 업로드 로직)
  const handleCropComplete = async (croppedBlob: Blob) => {
    if (!memberId) return;
    setIsUploadingImage(true);
    setIsCropperOpen(false); // 모달 닫기

    try {
      const formData = new FormData();
      // Blob을 File 객체로 변환해서 전송
      const file = new File([croppedBlob], "profile_cropped.jpg", { type: "image/jpeg" });
      formData.append("file", file);

      const response = await fetch(`/api/users/profile/${memberId}/image`, {
        method: "POST",
        body: formData,
      });

      if (!response.ok) {
        setProfileMessage("이미지 업로드에 실패했습니다.");
        return;
      }

      const data = await response.json();
      if (data?.profile_image_url) {
        setProfileImageUrl(data.profile_image_url);
        setProfileMessage("프로필 이미지가 변경되었습니다.");
      }
    } catch (error) {
      setProfileMessage("오류가 발생했습니다.");
    } finally {
      setIsUploadingImage(false);
      setSelectedFile(null); // 초기화
    }
  };

  const handlePasswordSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!memberId) return;

    setIsSubmittingPassword(true);
    setPasswordMessage(null);

    try {
      const response = await fetch(`/api/users/profile/${memberId}/password`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          current_password: currentPassword,
          new_password: newPassword,
          confirm_password: confirmPassword,
        }),
      });

      if (!response.ok) {
        const data = await response.json().catch(() => null);
        setPasswordMessage(data?.detail || "비밀번호 변경에 실패했습니다.");
        return;
      }

      setPasswordMessage("비밀번호가 변경되었습니다.");
      setCurrentPassword("");
      setNewPassword("");
      setConfirmPassword("");
    } catch (error) {
      setPasswordMessage("비밀번호 변경에 실패했습니다.");
    } finally {
      setIsSubmittingPassword(false);
    }
  };

  if (!memberId) {
    return (
      <PageLayout className="min-h-screen bg-[#FDFBF8] text-black flex flex-col">
        <main className="flex-1 px-5 py-8 w-full max-w-md mx-auto pt-[120px]">
          <h2 className="text-2xl font-bold mb-3">마이페이지</h2>
          <p className="text-sm text-[#666]">로그인이 필요합니다.</p>
        </main>
      </PageLayout>
    );
  }

  return (
    <PageLayout className="min-h-screen bg-[#FDFBF8] text-black flex flex-col font-sans overflow-x-hidden">
      {/* Background Aura Blobs */}
      <div className="fixed inset-0 pointer-events-none overflow-hidden z-0">
        <motion.div
          animate={{
            x: [0, 100, 0],
            y: [0, 50, 0],
            scale: [1, 1.2, 1],
          }}
          transition={{ duration: 20, repeat: Infinity, ease: "linear" }}
          className="absolute -top-[10%] -left-[10%] w-[50%] h-[50%] bg-[#FFD3B6]/20 rounded-full blur-[100px]"
        />
        <motion.div
          animate={{
            x: [0, -80, 0],
            y: [0, 100, 0],
            scale: [1, 1.3, 1],
          }}
          transition={{ duration: 25, repeat: Infinity, ease: "linear" }}
          className="absolute top-[20%] -right-[10%] w-[60%] h-[60%] bg-[#D4F0F0]/20 rounded-full blur-[120px]"
        />
        <motion.div
          animate={{
            x: [0, 50, 0],
            y: [0, -100, 0],
            scale: [1, 1.1, 1],
          }}
          transition={{ duration: 18, repeat: Infinity, ease: "linear" }}
          className="absolute -bottom-[10%] left-[20%] w-[40%] h-[40%] bg-[#A8E6CF]/20 rounded-full blur-[80px]"
        />
      </div>

      <main className="relative z-10 flex-1 px-5 py-8 w-full max-w-2xl mx-auto pt-[60px] pb-24 md:pt-[160px] space-y-8 md:space-y-20">
        {/* Header Section */}
        <div className="text-center md:text-left">
          <motion.h1
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="text-3xl md:text-5xl font-black tracking-tighter text-black uppercase select-none mb-2"
          >
            My Page
          </motion.h1>
          <motion.p
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.5 }}
            className="text-xs md:text-base text-gray-500 font-medium tracking-[0.2em] uppercase"
          >
            회원정보를 수정할 수 있어요.
          </motion.p>
        </div>

        <motion.form
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          className="space-y-6 md:space-y-12"
          onSubmit={handleProfileSubmit}
        >
          <div className="space-y-4 md:space-y-8">
            <h3 className="text-xs md:text-base font-black uppercase tracking-widest text-gray-400">프로필 설정</h3>

            {/* Profile Image Area */}
            <div className="flex flex-col md:flex-row items-center gap-6 md:gap-10">
              <div className="relative group">
                <motion.div
                  animate={{
                    scale: [1, 1.05, 1],
                    boxShadow: [
                      "0 0 0px rgba(0,0,0,0)",
                      "0 0 20px rgba(0,0,0,0.05)",
                      "0 0 0px rgba(0,0,0,0)"
                    ]
                  }}
                  transition={{ duration: 4, repeat: Infinity, ease: "easeInOut" }}
                  className="w-32 h-32 md:w-40 md:h-40 rounded-full bg-white overflow-hidden border border-gray-100 shadow-xl shrink-0"
                >
                  <img
                    src={resolvedProfileImageUrl}
                    alt="프로필"
                    className="w-full h-full object-cover transition-transform duration-700 group-hover:scale-110"
                    onError={(event) => {
                      const target = event.currentTarget;
                      if (session?.user?.image && target.src !== session.user.image) {
                        target.src = session.user.image;
                      } else {
                        target.src = "/default_profile.png";
                      }
                    }}
                  />
                </motion.div>
                <label
                  htmlFor="profileImage"
                  className="absolute bottom-1 right-1 w-10 h-10 bg-black text-white rounded-full flex items-center justify-center cursor-pointer hover:scale-110 transition-transform shadow-lg border-2 border-white"
                >
                  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M3 9a2 2 0 012-2h.93a2 2 0 001.664-.89l.812-1.22A2 2 0 0110.07 4h3.86a2 2 0 011.664.89l.812 1.22A2 2 0 0018.07 7H19a2 2 0 012 2v9a2 2 0 01-2 2H5a2 2 0 01-2-2V9z"></path><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M15 13a3 3 0 11-6 0 3 3 0 016 0z"></path></svg>
                </label>
              </div>
              <div className="flex flex-col items-center md:items-start">
                <h4 className="text-xl md:text-3xl font-bold text-black">{displayName}</h4>
                <p className="text-xs md:text-sm text-gray-400 mt-1 uppercase tracking-tighter">{profile?.email || "Member"}</p>
                {isUploadingImage && (
                  <p className="text-[10px] md:text-xs text-gray-400 mt-4 animate-pulse">이미지 업로드 중...</p>
                )}
              </div>
              <input
                id="profileImage"
                name="profileImage"
                type="file"
                accept="image/*"
                className="hidden"
                onChange={(event) => {
                  const file = event.target.files?.[0];
                  if (file) {
                    const reader = new FileReader();
                    reader.addEventListener("load", () => {
                      setSelectedFile(reader.result?.toString() || null);
                      setIsCropperOpen(true);
                    });
                    reader.readAsDataURL(file);
                    event.target.value = "";
                  }
                }}
              />
            </div>

            <div className="grid md:grid-cols-2 gap-x-12 gap-y-4 md:gap-y-10">
              <div className="space-y-2 group">
                <label htmlFor="nickname" className="text-[10px] md:text-xs font-black uppercase tracking-widest text-gray-400 group-focus-within:text-black transition-colors">닉네임</label>
                <input
                  id="nickname"
                  name="nickname"
                  type="text"
                  value={nickname}
                  onChange={(event) => setNickname(event.target.value)}
                  placeholder="닉네임을 입력하세요"
                  className="w-full bg-transparent border-b border-gray-200 py-2 text-base md:text-xl focus:border-black focus:outline-none transition-colors placeholder-gray-300"
                />
                {nicknameHint && (
                  <p className={`text-[10px] font-medium ${nicknameStatus === "available" ? "text-green-500" : "text-red-400"}`}>
                    {nicknameHint}
                  </p>
                )}
              </div>

              <div className="space-y-2 group">
                <label htmlFor="subEmail" className="text-[10px] md:text-xs font-black uppercase tracking-widest text-gray-400 group-focus-within:text-black transition-colors">복구 이메일 (선택)</label>
                <input
                  id="subEmail"
                  name="subEmail"
                  type="email"
                  value={subEmail}
                  onChange={(event) => setSubEmail(event.target.value)}
                  placeholder="계정 복구용 이메일을 입력하세요"
                  className="w-full bg-transparent border-b border-gray-200 py-2 text-base md:text-xl focus:border-black focus:outline-none transition-colors placeholder-gray-300"
                />
              </div>
            </div>
          </div>

          <div className="space-y-6 md:space-y-10 pt-6 md:pt-10 border-t border-gray-100">
            <h3 className="text-xs md:text-base font-black uppercase tracking-widest text-gray-400">기본 정보</h3>
            <div className="grid md:grid-cols-2 gap-x-12 gap-y-4 md:gap-y-10">
              <div className="space-y-2 group">
                <label htmlFor="name" className="text-[10px] md:text-xs font-black uppercase tracking-widest text-gray-400 group-focus-within:text-black transition-colors">이름</label>
                <input
                  id="name"
                  name="name"
                  type="text"
                  value={name}
                  onChange={(event) => setName(event.target.value)}
                  placeholder="성함을 입력하세요"
                  className="w-full bg-transparent border-b border-gray-200 py-2 text-base md:text-xl focus:border-black focus:outline-none transition-colors placeholder-gray-300"
                />
              </div>

              <div className="space-y-2 group">
                <label className="text-[10px] md:text-xs font-black uppercase tracking-widest text-gray-400 mb-2 block">성별</label>
                <div className="flex gap-8 pt-1">
                  <label className="flex items-center gap-2 text-sm cursor-pointer group/label">
                    <input
                      type="radio"
                      name="sex"
                      value="M"
                      checked={sex === "M"}
                      onChange={() => setSex("M")}
                      className="accent-black w-4 h-4"
                    />
                    <span className="font-bold text-gray-300 group-checked:text-black transition-colors text-sm md:text-base">남자</span>
                  </label>
                  <label className="flex items-center gap-2 text-sm md:text-base cursor-pointer group/label">
                    <input
                      type="radio"
                      name="sex"
                      value="F"
                      checked={sex === "F"}
                      onChange={() => setSex("F")}
                      className="accent-black w-4 h-4 md:w-5 md:h-5"
                    />
                    <span className="font-bold text-gray-300 group-checked:text-black transition-colors text-sm md:text-base">여자</span>
                  </label>
                </div>
              </div>

              <div className="space-y-2 group">
                <label htmlFor="phoneNo" className="text-[10px] md:text-xs font-black uppercase tracking-widest text-gray-400 group-focus-within:text-black transition-colors">휴대폰 번호</label>
                <input
                  id="phoneNo"
                  name="phoneNo"
                  type="text"
                  value={phoneNo}
                  onChange={(event) => setPhoneNo(event.target.value)}
                  placeholder="010-0000-0000"
                  className="w-full bg-transparent border-b border-gray-200 py-2 text-base md:text-xl focus:border-black focus:outline-none transition-colors placeholder-gray-300"
                />
              </div>

              <div className="space-y-2 group">
                <label htmlFor="address" className="text-[10px] md:text-xs font-black uppercase tracking-widest text-gray-400 group-focus-within:text-black transition-colors">주소</label>
                <input
                  id="address"
                  name="address"
                  type="text"
                  value={address}
                  onChange={(event) => setAddress(event.target.value)}
                  placeholder="주소를 입력하세요"
                  className="w-full bg-transparent border-b border-gray-200 py-2 text-base md:text-xl focus:border-black focus:outline-none transition-colors placeholder-gray-300"
                />
              </div>

              <div className="md:col-span-2 space-y-2 group">
                <label htmlFor="email" className="text-[10px] md:text-xs font-black uppercase tracking-widest text-gray-400 group-focus-within:text-black transition-colors">이메일 계정</label>
                <input
                  id="email"
                  name="email"
                  type="email"
                  value={email}
                  disabled
                  className="w-full bg-transparent border-b border-gray-100 py-2 text-base md:text-lg text-gray-400 focus:outline-none cursor-not-allowed opacity-50"
                />
              </div>
            </div>
          </div>

          <div className="space-y-6 pt-10 border-t border-gray-100 text-sm md:text-base">
            <h3 className="text-xs md:text-base font-black uppercase tracking-widest text-gray-400">알림 설정</h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <label className="flex items-center justify-between p-4 md:p-6 rounded-2xl border border-gray-100 bg-white/50 backdrop-blur-sm cursor-pointer hover:border-black transition-all">
                <span className="text-xs md:text-sm font-black uppercase tracking-tighter">이메일 알림 수신</span>
                <input
                  type="checkbox"
                  className="accent-black w-5 h-5"
                  checked={emailMarketing}
                  onChange={(event) => setEmailMarketing(event.target.checked)}
                />
              </label>
              <label className="flex items-center justify-between p-4 md:p-6 rounded-2xl border border-gray-100 bg-white/50 backdrop-blur-sm cursor-pointer hover:border-black transition-all">
                <span className="text-xs md:text-sm font-black uppercase tracking-tighter">SNS 알림 수신</span>
                <input
                  type="checkbox"
                  className="accent-black w-5 h-5"
                  checked={snsMarketing}
                  onChange={(event) => setSnsMarketing(event.target.checked)}
                />
              </label>
            </div>
          </div>

          {profileMessage && (
            <motion.p initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="text-center text-[11px] font-bold text-red-400 uppercase tracking-widest">
              {profileMessage}
            </motion.p>
          )}

          <div className="flex justify-center pt-2 md:pt-8">
            <motion.button
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.98 }}
              disabled={isSubmittingProfile}
              className="group relative px-12 py-4 md:px-16 md:py-6 rounded-full bg-black text-white text-xs md:text-base font-black uppercase tracking-[0.3em] overflow-hidden disabled:bg-gray-200"
            >
              <span className="relative z-10">{isSubmittingProfile ? "처리 중..." : "저장하기"}</span>
              <div className="absolute inset-x-0 bottom-0 h-0 bg-white/10 group-hover:h-full transition-all duration-300" />
            </motion.button>
          </div>
        </motion.form>

        {showPasswordSection && (
          <motion.form
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            className="space-y-6 md:space-y-12 pt-6 md:pt-12 border-t border-gray-200"
            onSubmit={handlePasswordSubmit}
          >
            <h3 className="text-xs md:text-base font-black uppercase tracking-widest text-gray-400">보안 설정</h3>
            <div className="grid grid-cols-1 gap-6 md:gap-10">
              <div className="space-y-2 group">
                <label htmlFor="currentPassword" title="Current Password" className="text-[10px] font-black uppercase tracking-widest text-gray-400 group-focus-within:text-black transition-colors">현재 비밀번호</label>
                <input
                  id="currentPassword"
                  name="currentPassword"
                  type="password"
                  value={currentPassword}
                  onChange={(event) => setCurrentPassword(event.target.value)}
                  placeholder="••••••••"
                  className="w-full bg-transparent border-b border-gray-200 py-2 text-base md:text-xl focus:border-black focus:outline-none transition-colors placeholder-gray-300"
                />
              </div>
              <div className="grid md:grid-cols-2 gap-4 md:gap-10">
                <div className="space-y-2 group">
                  <label htmlFor="newPassword" title="New Password" className="text-[10px] md:text-xs font-black uppercase tracking-widest text-gray-400 group-focus-within:text-black transition-colors">새 비밀번호</label>
                  <input
                    id="newPassword"
                    name="newPassword"
                    type="password"
                    value={newPassword}
                    onChange={(event) => setNewPassword(event.target.value)}
                    placeholder="••••••••"
                    className="w-full bg-transparent border-b border-gray-200 py-2 text-base focus:border-black focus:outline-none transition-colors placeholder-gray-300"
                  />
                </div>
                <div className="space-y-2 group">
                  <label htmlFor="confirmPassword" title="Confirm Password" className="text-[10px] md:text-xs font-black uppercase tracking-widest text-gray-400 group-focus-within:text-black transition-colors">새 비밀번호 확인</label>
                  <input
                    id="confirmPassword"
                    name="confirmPassword"
                    type="password"
                    value={confirmPassword}
                    onChange={(event) => setConfirmPassword(event.target.value)}
                    placeholder="••••••••"
                    className="w-full bg-transparent border-b border-gray-200 py-2 text-base focus:border-black focus:outline-none transition-colors placeholder-gray-300"
                  />
                </div>
              </div>
            </div>

            {passwordMessage && (
              <p className="text-center text-[11px] font-bold text-red-500 uppercase tracking-widest">{passwordMessage}</p>
            )}

            <div className="flex justify-center pt-4">
              <motion.button
                whileHover={{ scale: 1.02 }}
                whileTap={{ scale: 0.98 }}
                disabled={isSubmittingPassword}
                className="group relative px-12 py-4 md:px-16 md:py-6 rounded-full border-2 border-black text-black text-xs md:text-base font-black uppercase tracking-[0.3em] overflow-hidden hover:bg-black hover:text-white transition-all disabled:border-gray-200 disabled:text-gray-300"
              >
                비밀번호 변경
              </motion.button>
            </div>
          </motion.form>
        )}

        <motion.section
          initial={{ opacity: 0 }}
          whileInView={{ opacity: 1 }}
          viewport={{ once: true }}
          className="pt-8 md:pt-20 border-t border-gray-100 text-center"
        >
          <button
            type="button"
            onClick={async () => {
              if (!memberId) return;
              if (!window.confirm("정말 탈퇴처리하시겠습니까? 데이터는 7일간 유지됩니다.")) return;
              try {
                const response = await fetch(`/api/users/profile/${memberId}/withdraw`, { method: "POST" });
                if (!response.ok) return;
                window.location.href = "/";
              } catch (error) { }
            }}
            className="text-[10px] md:text-sm font-black text-red-300 uppercase tracking-[0.2em] hover:text-red-600 transition-colors"
          >
            회원 탈퇴
          </button>
        </motion.section>
      </main>
      {/* [MODAL] 이미지 크롭퍼 모달 */}
      {isCropperOpen && selectedFile && (
        <ImageCropperModal
          imageSrc={selectedFile}
          onClose={() => {
            setIsCropperOpen(false);
            setSelectedFile(null);
          }}
          onCropComplete={handleCropComplete}
        />
      )}
    </PageLayout>
  );
}
