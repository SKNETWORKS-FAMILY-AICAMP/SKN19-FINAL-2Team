'use client';

import { FormEvent, useMemo, useState } from "react";
import Link from "next/link";
import PageLayout from "@/components/common/PageLayout";
import ImageCropperModal from "@/components/common/ImageCropperModal";
import { useRouter } from "next/navigation";
import { motion } from "framer-motion";

const AgreementPopup = ({ title, content, onAgree, onClose }: { title: string; content: string; onAgree: () => void; onClose: () => void; }) => (
  <div className="fixed inset-0 z-[100] flex items-center justify-center bg-black/60 p-4" onClick={onClose}>
    <div className="flex max-h-[80vh] w-full max-w-lg flex-col rounded-xl bg-white" onClick={e => e.stopPropagation()}>
      <div className="border-b p-6">
        <h3 className="text-xl font-bold">{title}</h3>
      </div>
      <div className="overflow-y-auto p-6 text-sm text-gray-700">
        <pre className="font-sans whitespace-pre-wrap">{content}</pre>
      </div>
      <div className="mt-auto border-t p-6">
        <button
          onClick={() => {
            onAgree();
            onClose();
          }}
          className="w-full rounded-lg bg-black py-3 font-bold text-white transition hover:opacity-90"
        >
          상기 내용을 숙지하였으며 이에 동의합니다.
        </button>
      </div>
    </div>
  </div>
);

// 약관 내용 정의 (향후 실제 내용으로 교체 필요)
const TERMS_CONTENT = `
제1조 (목적)
이 약관은 Scentence(이하 "회사")가 제공하는 Scentence 서비스 및 관련 제반 서비스(이하 "서비스")의 이용과 관련하여 회사와 회원과의 권리, 의무 및 책임사항, 기타 필요한 사항을 규정함을 목적으로 합니다.

제2조 (정의)
이 약관에서 사용하는 용어의 정의는 다음과 같습니다.
1. "서비스"라 함은 구현되는 단말기(PC, TV, 휴대형단말기 등의 각종 유무선 장치를 포함)와 상관없이 "회원"이 이용할 수 있는 Scentence 및 관련 제반 서비스를 의미합니다.
2. "회원"이라 함은 회사의 "서비스"에 접속하여 이 약관에 따라 "회사"와 이용계약을 체결하고 "회사"가 제공하는 "서비스"를 이용하는 고객을 말합니다.

(이하 약관의 상세 내용은 여기에 추가해주세요.)
`;

const PRIVACY_CONTENT = `
Scentence(이하 "회사")는 개인정보보호법, 정보통신망 이용촉진 및 정보보호 등에 관한 법률 등 관련 법령상의 개인정보보호 규정을 준수하며, 관련 법령에 의거한 개인정보처리방침을 정하여 이용자 권익 보호에 최선을 다하고 있습니다.

1. 수집하는 개인정보의 항목
회사는 회원가입, 원활한 고객상담, 각종 서비스의 제공을 위해 아래와 같은 최소한의 개인정보를 필수항목으로 수집하고 있습니다.
- 필수항목 : 이메일, 비밀번호, 닉네임, 향수 지식
- 선택항목 : 이름, 성별, 주소, 핸드폰번호, 마케팅 정보 수신 동의(이메일, SMS)

2. 개인정보의 수집 및 이용목적
회사는 수집한 개인정보를 다음의 목적을 위해 활용합니다.
- 서비스 제공에 관한 계약 이행 및 서비스 제공에 따른 요금정산
- 회원 관리
- 신규 서비스 개발 및 마케팅, 광고에의 활용

(이하 개인정보 처리방침의 상세 내용은 여기에 추가해주세요.)
`;

const EMAIL_AGREEMENT_CONTENT = `
Scentence에서 제공하는 이벤트, 신규 서비스, 프로모션 등 다양한 마케팅 정보를 이메일로 받아보실 수 있습니다.

- 수신 동의 철회: 동의하신 이후라도 언제든지 '마이페이지 > 회원정보 수정'에서 수신 거부로 변경하실 수 있습니다.
- 수신 동의를 거부하시더라도, 회원가입, 거래정보 등과 관련된 주요 정책 및 공지사항은 발송될 수 있습니다.
`;

const SNS_AGREEMENT_CONTENT = `
Scentence에서 제공하는 이벤트, 신규 서비스, 프로모션 등 다양한 마케팅 정보를 SMS(문자메시지) 또는 카카오톡 알림톡으로 받아보실 수 있습니다.

- 수신 동의 철회: 동의하신 이후라도 언제든지 '마이페이지 > 회원정보 수정'에서 수신 거부로 변경하실 수 있습니다.
- 수신 동의를 거부하시더라도, 회원가입, 거래정보 등과 관련된 주요 정책 및 공지사항은 발송될 수 있습니다.
`;

export default function SignupPage() {
  const router = useRouter();

  // -- Form States --
  const [email, setEmail] = useState("");
  const [nickname, setNickname] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [userMode, setUserMode] = useState<"BEGINNER" | "EXPERT" | "">(""); // Essential

  const [name, setName] = useState("");
  const [sex, setSex] = useState<"M" | "F" | "">("");
  const [phoneNo, setPhoneNo] = useState("");
  const [address, setAddress] = useState("");
  const [profileImageFile, setProfileImageFile] = useState<File | null>(null);
  const [profileImageUrl, setProfileImageUrl] = useState("");
  const [selectedFile, setSelectedFile] = useState<string | null>(null);
  const [isCropperOpen, setIsCropperOpen] = useState(false);

  // -- Checkbox States --
  const [termsAgree, setTermsAgree] = useState(false);
  const [privacyAgree, setPrivacyAgree] = useState(false);
  const [emailAlarmAgree, setEmailAlarmAgree] = useState(false);
  const [snsAlarmAgree, setSnsAlarmAgree] = useState(false);

  // -- UI States --
  const [isPasswordVisible, setIsPasswordVisible] = useState(false);
  const [isConfirmVisible, setIsConfirmVisible] = useState(false);
  const [hasTypedConfirm, setHasTypedConfirm] = useState(false);

  const [emailCheckStatus, setEmailCheckStatus] = useState<"idle" | "checking" | "available" | "unavailable">("idle");
  const [nicknameCheckStatus, setNicknameCheckStatus] = useState<"idle" | "checking" | "available" | "unavailable">("idle");

  const [submitMessage, setSubmitMessage] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [popupContent, setPopupContent] = useState<{ title: string; content: string; onAgree: () => void } | null>(null);

  const apiBaseUrl = "/api";

  const allAgree = termsAgree && privacyAgree && emailAlarmAgree && snsAlarmAgree;

  const handleAllAgreeChange = (checked: boolean) => {
    setTermsAgree(checked);
    setPrivacyAgree(checked);
    setEmailAlarmAgree(checked);
    setSnsAlarmAgree(checked);
  };

  const handleTermsChange = (checked: boolean) => {
    setTermsAgree(checked);
  };

  const handlePrivacyChange = (checked: boolean) => {
    setPrivacyAgree(checked);
  };

  const agreementDetails = useMemo(() => ({
    terms: { title: '이용약관 동의', content: TERMS_CONTENT, onAgree: () => setTermsAgree(true) },
    privacy: { title: '개인정보 수집 및 이용 동의', content: PRIVACY_CONTENT, onAgree: () => setPrivacyAgree(true) },
    email: { title: 'E-mail 정보 수신 동의', content: EMAIL_AGREEMENT_CONTENT, onAgree: () => setEmailAlarmAgree(true) },
    sns: { title: 'SMS 정보 수신 동의', content: SNS_AGREEMENT_CONTENT, onAgree: () => setSnsAlarmAgree(true) },
  }), []);

  const handleShowPopup = (type: keyof typeof agreementDetails) => {
    setPopupContent(agreementDetails[type]);
  };

  const passwordRules = useMemo(() => {
    const minLength = password.length >= 8;
    const allowedSpecialsOnly = password.length > 0 && /^[A-Za-z\d!@#$%]*$/.test(password);
    const hasLower = /[a-z]/.test(password);
    const hasUpper = /[A-Z]/.test(password);
    const hasNumber = /\d/.test(password);
    const hasSpecial = /[!@#$%]/.test(password);
    const hasRequiredSets = hasLower && hasUpper && hasNumber && hasSpecial;

    return {
      minLength,
      hasRequiredSets,
      allowedSpecialsOnly,
    };
  }, [password]);

  const confirmMessage = useMemo(() => {
    if (!hasTypedConfirm) return null;
    if (confirmPassword.length === 0) {
      return { text: "비밀번호가 일치하지 않습니다.", isMatch: false };
    }
    if (password === confirmPassword) {
      return { text: "비밀번호가 일치합니다.", isMatch: true };
    }
    return { text: "비밀번호가 일치하지 않습니다.", isMatch: false };
  }, [confirmPassword, hasTypedConfirm, password]);

  const handleEmailCheck = async () => {
    if (!email.trim()) return;
    setEmailCheckStatus("checking");
    try {
      const response = await fetch(`${apiBaseUrl}/users/check-email?email=${encodeURIComponent(email.trim())}`);
      if (!response.ok) {
        setEmailCheckStatus("unavailable");
        return;
      }
      const data = await response.json();
      setEmailCheckStatus(data.available ? "available" : "unavailable");
    } catch (error) {
      setEmailCheckStatus("unavailable");
    }
  };

  const handleNicknameCheck = async () => {
    if (!nickname.trim()) return;
    setNicknameCheckStatus("checking");
    try {
      const response = await fetch(`${apiBaseUrl}/users/check-nickname?nickname=${encodeURIComponent(nickname.trim())}`);
      if (!response.ok) {
        setNicknameCheckStatus("unavailable");
        return;
      }
      const data = await response.json();
      setNicknameCheckStatus(data.available ? "available" : "unavailable");
    } catch (error) {
      setNicknameCheckStatus("unavailable");
    }
  };

  const handleImageUpload = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (file) {
      // 1. 파일을 읽어 URL로 변환 (크롭퍼용)
      const reader = new FileReader();
      reader.addEventListener("load", () => {
        setSelectedFile(reader.result?.toString() || null);
        setIsCropperOpen(true); // 크롭 모달 열기
      });
      reader.readAsDataURL(file);

      // 동일 파일 다시 선택 가능하도록 초기화
      event.target.value = "";
    }
  };

  const handleCropComplete = async (croppedBlob: Blob) => {
    // 2. 크롭 완료된 이미지를 파일로 변환하여 상태 저장
    const file = new File([croppedBlob], "profile_cropped.jpg", { type: "image/jpeg" });
    setProfileImageFile(file);

    // 미리보기 URL 생성
    const url = URL.createObjectURL(file);
    setProfileImageUrl(url);

    setIsCropperOpen(false); // 모달 닫기
    setSelectedFile(null);    // 원본 선택 초기화
  };


  /* Single Page Signup Implementation */
  const handleSubmit = async (e?: FormEvent) => {
    if (e) e.preventDefault();
    if (!canSubmit) return;

    setIsSubmitting(true);
    setSubmitMessage(null);

    try {
      const response = await fetch(`${apiBaseUrl}/users/register`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          email: email.trim(),
          password,
          name: name.trim() || null,
          sex: sex || null,
          phone_no: phoneNo.trim() || null,
          address: address.trim() || null,
          nickname: nickname.trim() || null,
          user_mode: userMode || null, // Essential now
          req_agr_yn: termsAgree && privacyAgree ? "Y" : "N",
          email_alarm_yn: emailAlarmAgree ? "Y" : "N",
          sns_alarm_yn: snsAlarmAgree ? "Y" : "N",
        }),
      });

      if (!response.ok) {
        const data = await response.json().catch(() => null);
        const detail = data?.detail || "회원가입에 실패했습니다.";
        setSubmitMessage(detail);
        return;
      }

      const data = await response.json();
      const memberId = data.member_id;

      if (profileImageFile && memberId) {
        const formData = new FormData();
        formData.append("file", profileImageFile);
        await fetch(`${apiBaseUrl}/users/profile/${memberId}/image`, {
          method: "POST",
          body: formData,
        });
      }

      router.push("/login");
    } catch (error) {
      setSubmitMessage("회원가입에 실패했습니다.");
    } finally {
      setIsSubmitting(false);
    }
  };

  // Validation for submit button
  const isEssentialValid =
    email.trim() &&
    emailCheckStatus === "available" &&
    passwordRules.minLength &&
    passwordRules.hasRequiredSets &&
    passwordRules.allowedSpecialsOnly &&
    password === confirmPassword &&
    nickname.trim() &&
    nicknameCheckStatus === "available" &&
    userMode; // Knowledge is essential

  const isAgreementsValid = termsAgree && privacyAgree;
  const canSubmit = isEssentialValid && isAgreementsValid;

  const validationGuide = useMemo(() => {
    if (canSubmit) return null;
    const missing = [];
    if (!email.trim()) missing.push("이메일을 입력해주세요.");
    else if (emailCheckStatus !== "available") missing.push("이메일 중복확인이 필요합니다.");

    if (!password) missing.push("비밀번호를 입력해주세요.");
    else if (!passwordRules.minLength || !passwordRules.hasRequiredSets || !passwordRules.allowedSpecialsOnly) missing.push("비밀번호 규칙을 확인해주세요.");

    if (password !== confirmPassword) missing.push("비밀번호가 일치하지 않습니다.");

    if (!nickname.trim()) missing.push("별명을 입력해주세요.");
    else if (nicknameCheckStatus !== "available") missing.push("별명 중복확인이 필요합니다.");

    if (!userMode) missing.push("지식 수준을 선택해주세요.");
    if (!isAgreementsValid) missing.push("필수 약관에 동의해주세요.");

    return missing[0]; // Show first missing requirement
  }, [canSubmit, email, emailCheckStatus, password, passwordRules, confirmPassword, nickname, nicknameCheckStatus, userMode, isAgreementsValid]);

  return (
    <PageLayout>
      <div className="flex min-h-screen flex-col items-center justify-center py-10 md:py-20 px-4 bg-[#FDFBF8]">
        <div className="w-full max-w-xl">
          <div className="mb-12 text-center">
            <h1 className="flex flex-col items-center leading-none select-none -translate-x-3">
              <motion.span
                className="text-3xl md:text-5xl font-black tracking-tighter text-black uppercase -rotate-2 -translate-x-6 mb-[-5px] inline-block"
                animate={{ y: [0, -8, 0] }}
                transition={{ duration: 3, repeat: Infinity, ease: "easeInOut" }}
              >
                Join
              </motion.span>
              <motion.span
                className="text-4xl md:text-7xl font-black tracking-tighter text-transparent uppercase rotate-1 translate-x-2 inline-block"
                style={{ WebkitTextStroke: "1.5px black" }}
                animate={{ y: [0, 8, 0] }}
                transition={{ duration: 4, repeat: Infinity, ease: "easeInOut", delay: 0.5 }}
              >
                Scentence
              </motion.span>
            </h1>
            <p className="mt-6 text-xs text-gray-600 font-medium tracking-[0.2em]">
              나만의 향기를 찾는 여정의 시작
            </p>
          </div>

          <form onSubmit={handleSubmit} className="space-y-12 md:space-y-16">

            {/* 1. Essential Information Section */}
            <section className="space-y-6">
              <div className="border-b border-gray-100 pb-3 mb-8">
                <h2 className="text-lg font-bold text-black tracking-tight">필수 정보</h2>
                <p className="text-[10px] text-gray-400 uppercase tracking-widest mt-1">Essential Information</p>
              </div>

              {/* Email */}
              <div className="space-y-2">
                <label htmlFor="email" className="block text-xs font-bold text-gray-500 uppercase tracking-wider">Email</label>
                <div className="flex gap-2">
                  <input
                    id="email"
                    type="email"
                    placeholder="example@email.com"
                    value={email}
                    onChange={(e) => { setEmail(e.target.value); setEmailCheckStatus("idle"); }}
                    className="flex-1 border-b border-gray-300 py-2 text-base focus:border-black focus:outline-none transition-colors bg-transparent placeholder-gray-300"
                  />
                  <button
                    type="button"
                    onClick={handleEmailCheck}
                    disabled={!email.trim() || emailCheckStatus === "checking"}
                    className="whitespace-nowrap px-4 py-1 text-xs font-medium text-gray-500 hover:text-black disabled:opacity-30 underline decoration-1 underline-offset-4"
                  >
                    {emailCheckStatus === "checking" ? "Checking..." : "중복확인"}
                  </button>
                </div>
                {emailCheckStatus === "available" && <p className="text-xs text-green-600 mt-1">✓ 사용 가능한 이메일입니다.</p>}
                {emailCheckStatus === "unavailable" && <p className="text-xs text-red-600 mt-1">✗ 이미 사용중인 이메일입니다.</p>}
              </div>

              {/* Nickname */}
              <div className="space-y-2">
                <label htmlFor="nickname" className="block text-xs font-bold text-gray-500 uppercase tracking-wider">Nickname</label>
                <div className="flex gap-2">
                  <input
                    id="nickname"
                    type="text"
                    placeholder="별명을 입력하세요"
                    value={nickname}
                    onChange={(e) => { setNickname(e.target.value); setNicknameCheckStatus("idle"); }}
                    className="flex-1 border-b border-gray-300 py-2 text-base focus:border-black focus:outline-none transition-colors bg-transparent placeholder-gray-300"
                  />
                  <button
                    type="button"
                    onClick={handleNicknameCheck}
                    disabled={!nickname.trim() || nicknameCheckStatus === "checking"}
                    className="whitespace-nowrap px-4 py-1 text-xs font-medium text-gray-500 hover:text-black disabled:opacity-30 underline decoration-1 underline-offset-4"
                  >
                    {nicknameCheckStatus === "checking" ? "Checking..." : "중복확인"}
                  </button>
                </div>
                {nicknameCheckStatus === "available" && <p className="text-[10px] text-green-600 mt-1 font-medium">✓ 사용 가능한 별명입니다.</p>}
                {nicknameCheckStatus === "unavailable" && <p className="text-[10px] text-red-600 mt-1 font-medium">✗ 이미 사용중인 별명입니다.</p>}
              </div>

              {/* Password */}
              <div className="grid grid-cols-1 gap-6 sm:grid-cols-2">
                <div className="space-y-2">
                  <label htmlFor="password" className="block text-xs font-bold text-gray-500 uppercase tracking-wider">Password</label>
                  <div className="relative">
                    <input
                      id="password"
                      type={isPasswordVisible ? "text" : "password"}
                      value={password}
                      onChange={(e) => setPassword(e.target.value)}
                      className="w-full border-b border-gray-300 py-2 text-base focus:border-black focus:outline-none transition-colors bg-transparent"
                    />
                    <button
                      type="button"
                      className="absolute right-0 top-1/2 -translate-y-1/2 p-2 opacity-50 hover:opacity-100"
                      onClick={() => setIsPasswordVisible(!isPasswordVisible)}
                    >
                      <img src="/eye.svg" alt="toggle" className="w-4 h-4" />
                    </button>
                  </div>
                </div>

                <div className="space-y-2">
                  <label htmlFor="confirmPassword" className="block text-xs font-bold text-gray-500 uppercase tracking-wider">Confirm Password</label>
                  <div className="relative">
                    <input
                      id="confirmPassword"
                      type={isConfirmVisible ? "text" : "password"}
                      value={confirmPassword}
                      onChange={(e) => {
                        setConfirmPassword(e.target.value);
                        if (!hasTypedConfirm) setHasTypedConfirm(true);
                      }}
                      className="w-full border-b border-gray-300 py-2 text-base focus:border-black focus:outline-none transition-colors bg-transparent"
                    />
                    <button
                      type="button"
                      className="absolute right-0 top-1/2 -translate-y-1/2 p-2 opacity-50 hover:opacity-100"
                      onClick={() => setIsConfirmVisible(!isConfirmVisible)}
                    >
                      <img src="/eye.svg" alt="toggle" className="w-4 h-4" />
                    </button>
                  </div>
                  {confirmMessage && (
                    <p className={`text-xs mt-1 ${confirmMessage.isMatch ? "text-green-600" : "text-red-600"}`}>
                      {confirmMessage.text}
                    </p>
                  )}
                </div>
              </div>

              {/* Password Rules */}
              <div className="space-y-1">
                <div className={`flex items-center gap-2 text-xs ${passwordRules.minLength ? "text-green-600" : "text-gray-400"}`}>
                  <span className={`block w-1.5 h-1.5 rounded-full ${passwordRules.minLength ? "bg-green-600" : "bg-gray-300"}`} />
                  비밀번호는 8자리 이상이어야 합니다.
                </div>
                <div className={`flex items-center gap-2 text-xs ${passwordRules.hasRequiredSets ? "text-green-600" : "text-gray-400"}`}>
                  <span className={`block w-1.5 h-1.5 rounded-full ${passwordRules.hasRequiredSets ? "bg-green-600" : "bg-gray-300"}`} />
                  대소문자, 숫자, 특수문자를 각각 하나 이상 포함해야 합니다.
                </div>
                <div className={`flex items-center gap-2 text-xs ${passwordRules.allowedSpecialsOnly ? "text-green-600" : "text-gray-400"}`}>
                  <span className={`block w-1.5 h-1.5 rounded-full ${passwordRules.allowedSpecialsOnly ? "bg-green-600" : "bg-gray-300"}`} />
                  특수문자는 !, @, #, $, %만 사용 가능합니다.
                </div>
              </div>


              {/* Perfume Knowledge (Essential) */}
              <div className="space-y-4 pt-4">
                <label className="block text-xs font-bold text-gray-500 uppercase tracking-wider">Perfume Knowledge</label>
                <div className="grid grid-cols-2 gap-4">
                  <button
                    type="button"
                    onClick={() => setUserMode("BEGINNER")}
                    className={`group relative overflow-hidden rounded-full border py-3.5 text-center transition-all shadow-sm ${userMode === "BEGINNER" ? "border-black bg-black text-white" : "border-gray-200 hover:border-black"}`}
                  >
                    <span className="relative z-10 text-sm font-bold">입문자</span>
                  </button>
                  <button
                    type="button"
                    onClick={() => setUserMode("EXPERT")}
                    className={`group relative overflow-hidden rounded-full border py-3.5 text-center transition-all shadow-sm ${userMode === "EXPERT" ? "border-black bg-black text-white" : "border-gray-200 hover:border-black"}`}
                  >
                    <span className="relative z-10 text-sm font-bold">경험자</span>
                  </button>
                </div>
              </div>
            </section>


            {/* 2. Optional Information Section */}
            <section className="space-y-8">
              <div className="border-b border-gray-100 pb-3 mb-8">
                <h2 className="text-lg font-bold text-black tracking-tight">선택 정보</h2>
                <p className="text-[10px] text-gray-400 uppercase tracking-widest mt-1">Optional Details</p>
              </div>

              {/* Profile Image (Moved to Optional) */}
              <div className="flex items-center gap-6">
                <div className="relative h-20 w-20 flex-shrink-0 overflow-hidden rounded-full bg-gray-100 border border-gray-200">
                  <img
                    src={profileImageUrl || "/default_profile.png"}
                    alt="Profile"
                    className="h-full w-full object-cover"
                    onError={(e) => e.currentTarget.src = "/default_profile.png"}
                  />
                </div>
                <div>
                  <input
                    id="profileImage"
                    type="file"
                    accept="image/*"
                    className="hidden"
                    onChange={handleImageUpload}
                  />
                  <label
                    htmlFor="profileImage"
                    className="cursor-pointer inline-flex items-center gap-2 rounded-full border border-gray-300 px-4 py-2 text-xs font-medium transition hover:bg-black hover:text-white"
                  >
                    이미지 변경
                  </label>
                  <p className="mt-2 text-[10px] text-gray-400">프로필 이미지는 언제든 변경 가능합니다.</p>
                </div>
              </div>

              <div className="grid grid-cols-1 gap-6 sm:grid-cols-2">
                {/* Name */}
                <div className="space-y-2">
                  <label htmlFor="name" className="block text-xs font-bold text-gray-500 uppercase tracking-wider">Name</label>
                  <input
                    id="name"
                    type="text"
                    placeholder="이름"
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    className="w-full border-b border-gray-300 py-2 text-base focus:border-black focus:outline-none transition-colors bg-transparent placeholder-gray-300"
                  />
                </div>

                {/* Phone */}
                <div className="space-y-2">
                  <label htmlFor="phoneNo" className="block text-xs font-bold text-gray-500 uppercase tracking-wider">Phone</label>
                  <input
                    id="phoneNo"
                    type="tel"
                    placeholder="010-0000-0000"
                    value={phoneNo}
                    onChange={(e) => setPhoneNo(e.target.value)}
                    className="w-full border-b border-gray-300 py-2 text-base focus:border-black focus:outline-none transition-colors bg-transparent placeholder-gray-300"
                  />
                </div>
              </div>

              {/* Address */}
              <div className="space-y-2">
                <label htmlFor="address" className="block text-xs font-bold text-gray-500 uppercase tracking-wider">Address</label>
                <input
                  id="address"
                  type="text"
                  placeholder="주소"
                  value={address}
                  onChange={(e) => setAddress(e.target.value)}
                  className="w-full border-b border-gray-300 py-2 text-base focus:border-black focus:outline-none transition-colors bg-transparent placeholder-gray-300"
                />
              </div>

              {/* Gender (Now Optional) */}
              <div className="space-y-4">
                <label className="block text-xs font-bold text-gray-500 uppercase tracking-wider">Gender</label>
                <div className="flex gap-4">
                  <label className="flex cursor-pointer items-center gap-2 text-sm text-gray-600 hover:text-black">
                    <input
                      type="radio"
                      name="gender"
                      value="M"
                      checked={sex === "M"}
                      onChange={() => setSex("M")}
                      className="accent-black h-4 w-4"
                    />
                    Male
                  </label>
                  <label className="flex cursor-pointer items-center gap-2 text-sm text-gray-600 hover:text-black">
                    <input
                      type="radio"
                      name="gender"
                      value="F"
                      checked={sex === "F"}
                      onChange={() => setSex("F")}
                      className="accent-black h-4 w-4"
                    />
                    Female
                  </label>
                </div>
              </div>
            </section>

            {/* 3. Agreements Section */}
            <section className="space-y-6 pt-10 border-t border-gray-100">
              <div className="flex items-center justify-between bg-gray-50/50 p-4 rounded-2xl border border-gray-100">
                <h2 className="text-base font-bold text-black tracking-tight">서비스 이용 약관 전체 동의</h2>
                <label className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={allAgree}
                    onChange={(e) => handleAllAgreeChange(e.target.checked)}
                    className="accent-black h-5 w-5 rounded-md"
                  />
                </label>
              </div>

              <div className="space-y-3 pl-1">
                {/* Terms */}
                <div className="flex items-center justify-between group">
                  <label className="flex items-center gap-3 text-sm text-gray-600 cursor-pointer">
                    <input type="checkbox" checked={termsAgree} onChange={(e) => handleTermsChange(e.target.checked)} className="accent-black h-4 w-4" />
                    <span><span className="text-black font-semibold mx-1">[필수]</span> 이용약관 동의</span>
                  </label>
                  <button type="button" onClick={() => handleShowPopup('terms')} className="text-gray-400 hover:text-black p-1">
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 5l7 7-7 7"></path></svg>
                  </button>
                </div>
                {/* Privacy */}
                <div className="flex items-center justify-between group">
                  <label className="flex items-center gap-3 text-sm text-gray-600 cursor-pointer">
                    <input type="checkbox" checked={privacyAgree} onChange={(e) => handlePrivacyChange(e.target.checked)} className="accent-black h-4 w-4" />
                    <span><span className="text-black font-semibold mx-1">[필수]</span> 개인정보 수집 및 이용 동의</span>
                  </label>
                  <button type="button" onClick={() => handleShowPopup('privacy')} className="text-gray-400 hover:text-black p-1">
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 5l7 7-7 7"></path></svg>
                  </button>
                </div>
                {/* Email */}
                <div className="flex items-center justify-between group">
                  <label className="flex items-center gap-3 text-sm text-gray-600 cursor-pointer">
                    <input type="checkbox" checked={emailAlarmAgree} onChange={(e) => setEmailAlarmAgree(e.target.checked)} className="accent-black h-4 w-4" />
                    <span><span className="text-gray-400 mx-1">[선택]</span> 마케팅 정보 E-mail 수신 동의</span>
                  </label>
                  <button type="button" onClick={() => handleShowPopup('email')} className="text-gray-400 hover:text-black p-1">
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 5l7 7-7 7"></path></svg>
                  </button>
                </div>
                {/* SMS */}
                <div className="flex items-center justify-between group">
                  <label className="flex items-center gap-3 text-sm text-gray-600 cursor-pointer">
                    <input type="checkbox" checked={snsAlarmAgree} onChange={(e) => setSnsAlarmAgree(e.target.checked)} className="accent-black h-4 w-4" />
                    <span><span className="text-gray-400 mx-1">[선택]</span> 마케팅 정보 SMS 수신 동의</span>
                  </label>
                  <button type="button" onClick={() => handleShowPopup('sns')} className="text-gray-400 hover:text-black p-1">
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 5l7 7-7 7"></path></svg>
                  </button>
                </div>
              </div>
            </section>

            {/* Submit Area */}
            <div className="pt-8 pb-20">
              {submitMessage && (
                <div className="mb-4 rounded-lg bg-red-50 p-4 text-center text-sm text-red-600 animate-pulse">
                  {submitMessage}
                </div>
              )}
              <button
                type="submit"
                disabled={!canSubmit || isSubmitting}
                className="w-full rounded-full bg-black py-4.5 text-base font-bold text-white shadow-xl transition-all hover:bg-gray-900 active:scale-[0.98] disabled:bg-gray-200 disabled:shadow-none disabled:cursor-not-allowed"
              >
                {isSubmitting ? "가입 처리중..." : "Sign Up"}
              </button>

              {/* Validation Guide */}
              {!canSubmit && !isSubmitting && validationGuide && (
                <p className="mt-4 text-center text-[11px] text-red-400 font-medium animate-pulse">
                  {validationGuide}
                </p>
              )}
              <div className="mt-6 text-center text-sm">
                <Link href="/login" className="text-gray-500 underline decoration-gray-300 underline-offset-4 hover:text-black hover:decoration-black transition-all">
                  이미 계정이 있으신가요? 로그인하기
                </Link>
              </div>
            </div>

          </form>
        </div>
      </div>

      {/* 팝업 UI (유지) */}
      {popupContent && (
        <AgreementPopup
          title={popupContent.title}
          content={popupContent.content}
          onAgree={popupContent.onAgree}
          onClose={() => setPopupContent(null)}
        />
      )}
      {/* Image Cropper Modal */}
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
