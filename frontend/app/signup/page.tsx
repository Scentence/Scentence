'use client';

import { FormEvent, useMemo, useState } from "react";
import Link from "next/link";
import PageLayout from "@/components/common/PageLayout";
import { useRouter } from "next/navigation";

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
- 필수항목 : 이메일, 비밀번호, 이름, 성별
- 선택항목 : 마케팅 정보 수신 동의(이메일, SMS)

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
  const [currentStep, setCurrentStep] = useState(1);
  const [termsAgree, setTermsAgree] = useState(false);
  const [privacyAgree, setPrivacyAgree] = useState(false);
  const [emailAlarmAgree, setEmailAlarmAgree] = useState(false);
  const [snsAlarmAgree, setSnsAlarmAgree] = useState(false);
  const [email, setEmail] = useState("");
  const [name, setName] = useState("");
  const [sex, setSex] = useState<"M" | "F" | "">("");
  const [phoneNo, setPhoneNo] = useState("");
  const [address, setAddress] = useState("");
  const [nickname, setNickname] = useState("");
  const [userMode, setUserMode] = useState<"BEGINNER" | "EXPERT" | "">("");
  const [profileImageFile, setProfileImageFile] = useState<File | null>(null);
  const [profileImageUrl, setProfileImageUrl] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [isPasswordVisible, setIsPasswordVisible] = useState(false);
  const [isConfirmVisible, setIsConfirmVisible] = useState(false);
  const [hasTypedConfirm, setHasTypedConfirm] = useState(false);
  const [emailCheckStatus, setEmailCheckStatus] = useState<"idle" | "checking" | "available" | "unavailable">("idle");
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
    // eslint-disable-next-line react-hooks/exhaustive-deps
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

  const handleImageUpload = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (file) {
      setProfileImageFile(file);
      const url = URL.createObjectURL(file);
      setProfileImageUrl(url);
    }
  };

  const nextStep = () => {
    if (currentStep < 4) setCurrentStep(currentStep + 1);
  };

  const prevStep = () => {
    if (currentStep > 1) setCurrentStep(currentStep - 1);
  };

  const canProceedStep1 = email.trim() && emailCheckStatus === "available" && passwordRules.minLength && passwordRules.hasRequiredSets && passwordRules.allowedSpecialsOnly && password === confirmPassword;
  const canProceedStep2 = name.trim() && sex && phoneNo.trim() && address.trim();
  const canProceedStep3 = termsAgree && privacyAgree;
  const canProceedStep4 = nickname.trim() && userMode;

  const handleSubmit = async () => {
    setIsSubmitting(true);
    setSubmitMessage(null);

    try {
      const response = await fetch(`${apiBaseUrl}/users/register`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          email: email.trim(),
          password,
          name: name.trim(),
          sex: sex || null,
          phone_no: phoneNo.trim() || null,
          address: address.trim() || null,
          nickname: nickname.trim() || null,
          user_mode: userMode || null,
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

      // Upload profile image if exists
      if (profileImageFile && memberId) {
        const formData = new FormData();
        formData.append("file", profileImageFile);
        await fetch(`${apiBaseUrl}/users/profile/${memberId}/image`, {
          method: "POST",
          body: formData,
        });
        // Ignore errors for image upload
      }

      router.push("/login");
    } catch (error) {
      setSubmitMessage("회원가입에 실패했습니다.");
    } finally {
      setIsSubmitting(false);
    }
  };

  const renderStep1 = () => (
    <div className="space-y-5">
      <div className="space-y-2">
        <label htmlFor="email" className="text-sm font-medium text-[#333]">이메일</label>
        <div className="flex gap-2">
          <input
            id="email"
            name="email"
            type="email"
            placeholder="example@email.com"
            value={email}
            onChange={(event) => {
              setEmail(event.target.value);
              setEmailCheckStatus("idle");
            }}
            className="flex-1 rounded-xl border border-[#DDD] px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-black/20"
          />
          <button
            type="button"
            onClick={handleEmailCheck}
            disabled={!email.trim() || emailCheckStatus === "checking"}
            className="rounded-xl bg-black px-4 py-3 text-sm font-bold text-white disabled:bg-gray-300"
          >
            {emailCheckStatus === "checking" ? "확인중..." : "중복확인"}
          </button>
        </div>
        {emailCheckStatus === "available" && <p className="text-xs text-green-600">사용 가능한 이메일입니다.</p>}
        {emailCheckStatus === "unavailable" && <p className="text-xs text-red-600">이미 사용중인 이메일입니다.</p>}
      </div>

      <div className="space-y-2">
        <label htmlFor="password" className="text-sm font-medium text-[#333]">비밀번호</label>
        <div className="relative">
          <input
            id="password"
            name="password"
            type={isPasswordVisible ? "text" : "password"}
            placeholder="비밀번호를 입력하세요"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            className="w-full rounded-xl border border-[#DDD] px-4 py-3 pr-12 text-sm focus:outline-none focus:ring-2 focus:ring-black/20"
          />
          <button
            type="button"
            className="absolute right-3 top-1/2 -translate-y-1/2 p-1"
            onMouseDown={() => setIsPasswordVisible(true)}
            onMouseUp={() => setIsPasswordVisible(false)}
            onMouseLeave={() => setIsPasswordVisible(false)}
            onTouchStart={() => setIsPasswordVisible(true)}
            onTouchEnd={() => setIsPasswordVisible(false)}
            aria-label="비밀번호 보기"
          >
            <img src="/eye.svg" alt="비밀번호 보기" className="w-5 h-5" />
          </button>
        </div>
        <div className="space-y-2 text-xs">
          <div className="flex items-start gap-2">
            <span className={`mt-1 inline-block w-2 h-2 rounded-full ${passwordRules.minLength ? "bg-green-500" : "bg-red-500"}`} />
            <p className={`${passwordRules.minLength ? "text-green-600" : "text-red-600"}`}>비밀번호는 8자리 이상이어야 합니다.</p>
          </div>
          <div className="flex items-start gap-2">
            <span className={`mt-1 inline-block w-2 h-2 rounded-full ${passwordRules.hasRequiredSets ? "bg-green-500" : "bg-red-500"}`} />
            <p className={`${passwordRules.hasRequiredSets ? "text-green-600" : "text-red-600"}`}>대소문자, 숫자, 특수문자를 각각 하나 이상 포함해야 합니다.</p>
          </div>
          <div className="flex items-start gap-2">
            <span className={`mt-1 inline-block w-2 h-2 rounded-full ${passwordRules.allowedSpecialsOnly ? "bg-green-500" : "bg-red-500"}`} />
            <p className={`${passwordRules.allowedSpecialsOnly ? "text-green-600" : "text-red-600"}`}>특수문자는 !, @, #, $, %만 사용 가능합니다.</p>
          </div>
        </div>
      </div>

      <div className="space-y-2">
        <label htmlFor="confirmPassword" className="text-sm font-medium text-[#333]">비밀번호 확인</label>
        <div className="relative">
          <input
            id="confirmPassword"
            name="confirmPassword"
            type={isConfirmVisible ? "text" : "password"}
            placeholder="비밀번호를 다시 입력하세요"
            value={confirmPassword}
            onChange={(event) => {
              setConfirmPassword(event.target.value);
              if (!hasTypedConfirm) {
                setHasTypedConfirm(true);
              }
            }}
            className="w-full rounded-xl border border-[#DDD] px-4 py-3 pr-12 text-sm focus:outline-none focus:ring-2 focus:ring-black/20"
          />
          <button
            type="button"
            className="absolute right-3 top-1/2 -translate-y-1/2 p-1"
            onMouseDown={() => setIsConfirmVisible(true)}
            onMouseUp={() => setIsConfirmVisible(false)}
            onMouseLeave={() => setIsConfirmVisible(false)}
            onTouchStart={() => setIsConfirmVisible(true)}
            onTouchEnd={() => setIsConfirmVisible(false)}
            aria-label="비밀번호 확인 보기"
          >
            <img src="/eye.svg" alt="비밀번호 확인 보기" className="w-5 h-5" />
          </button>
        </div>
        {confirmMessage && (
          <p className={`text-xs ${confirmMessage.isMatch ? "text-green-600" : "text-red-600"}`}>
            {confirmMessage.text}
          </p>
        )}
      </div>
    </div>
  );

  const renderStep2 = () => (
    <div className="space-y-5">
      <div className="space-y-2">
        <label htmlFor="name" className="text-sm font-medium text-[#333]">이름</label>
        <input
          id="name"
          name="name"
          type="text"
          placeholder="이름을 입력하세요"
          value={name}
          onChange={(event) => setName(event.target.value)}
          className="w-full rounded-xl border border-[#DDD] px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-black/20"
        />
      </div>

      <div className="space-y-2">
        <span className="text-sm font-medium text-[#333]">성별</span>
        <div className="flex gap-4">
          <label className="flex items-center gap-2 text-sm">
            <input
              type="radio"
              name="gender"
              value="M"
              checked={sex === "M"}
              onChange={() => setSex("M")}
              className="accent-black"
            />
            남자
          </label>
          <label className="flex items-center gap-2 text-sm">
            <input
              type="radio"
              name="gender"
              value="F"
              checked={sex === "F"}
              onChange={() => setSex("F")}
              className="accent-black"
            />
            여자
          </label>
        </div>
      </div>

      <div className="space-y-2">
        <label htmlFor="phoneNo" className="text-sm font-medium text-[#333]">핸드폰번호</label>
        <input
          id="phoneNo"
          name="phoneNo"
          type="tel"
          placeholder="010-1234-5678"
          value={phoneNo}
          onChange={(event) => setPhoneNo(event.target.value)}
          className="w-full rounded-xl border border-[#DDD] px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-black/20"
        />
      </div>

      <div className="space-y-2">
        <label htmlFor="address" className="text-sm font-medium text-[#333]">주소</label>
        <input
          id="address"
          name="address"
          type="text"
          placeholder="주소를 입력하세요"
          value={address}
          onChange={(event) => setAddress(event.target.value)}
          className="w-full rounded-xl border border-[#DDD] px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-black/20"
        />
      </div>
    </div>
  );

  const renderStep3 = () => (
    <div className="space-y-5">
      <div className="rounded-xl border border-[#EEE] p-4">
        <label className="flex items-center gap-3 text-sm font-semibold">
          <input
            type="checkbox"
            className="accent-black h-5 w-5"
            checked={allAgree}
            onChange={(event) => handleAllAgreeChange(event.target.checked)}
          />
          약관 전체동의
        </label>
        <hr className="my-3" />
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <label className="flex cursor-pointer items-center gap-3 text-sm">
              <input
                type="checkbox"
                className="accent-black h-4 w-4"
                checked={termsAgree}
                onChange={(event) => handleTermsChange(event.target.checked)}
              />
              <span><span className="text-red-500">(필수)</span> 이용약관 동의</span>
            </label>
            <button type="button" onClick={() => handleShowPopup('terms')} className="p-1 transition-transform hover:scale-125">
              <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor" className="h-5 w-5 text-gray-400">
                <path strokeLinecap="round" strokeLinejoin="round" d="M8.25 4.5l7.5 7.5-7.5 7.5" />
              </svg>
            </button>
          </div>
          <div className="flex items-center justify-between">
            <label className="flex cursor-pointer items-center gap-3 text-sm">
              <input
                type="checkbox"
                className="accent-black h-4 w-4"
                checked={privacyAgree}
                onChange={(event) => handlePrivacyChange(event.target.checked)}
              />
              <span><span className="text-red-500">(필수)</span> 개인정보 수집 및 이용 동의</span>
            </label>
            <button type="button" onClick={() => handleShowPopup('privacy')} className="p-1 transition-transform hover:scale-125">
              <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor" className="h-5 w-5 text-gray-400">
                <path strokeLinecap="round" strokeLinejoin="round" d="M8.25 4.5l7.5 7.5-7.5 7.5" />
              </svg>
            </button>
          </div>
          <div className="flex items-center justify-between">
            <label className="flex cursor-pointer items-center gap-3 text-sm">
              <input
                type="checkbox"
                className="accent-black h-4 w-4"
                checked={emailAlarmAgree}
                onChange={(event) => setEmailAlarmAgree(event.target.checked)}
              />
              <span>(선택) E-mail 정보 수신 동의</span>
            </label>
            <button type="button" onClick={() => handleShowPopup('email')} className="p-1 transition-transform hover:scale-125">
              <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor" className="h-5 w-5 text-gray-400">
                <path strokeLinecap="round" strokeLinejoin="round" d="M8.25 4.5l7.5 7.5-7.5 7.5" />
              </svg>
            </button>
          </div>
          <div className="flex items-center justify-between">
            <label className="flex cursor-pointer items-center gap-3 text-sm">
              <input
                type="checkbox"
                className="accent-black h-4 w-4"
                checked={snsAlarmAgree}
                onChange={(event) => setSnsAlarmAgree(event.target.checked)}
              />
              <span>(선택) SMS 정보 수신 동의</span>
            </label>
            <button type="button" onClick={() => handleShowPopup('sns')} className="p-1 transition-transform hover:scale-125">
              <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor" className="h-5 w-5 text-gray-400">
                <path strokeLinecap="round" strokeLinejoin="round" d="M8.25 4.5l7.5 7.5-7.5 7.5" />
              </svg>
            </button>
          </div>
        </div>
      </div>
    </div>
  );

  const renderStep4 = () => (
    <div className="space-y-5">
      <div className="space-y-2">
        <label htmlFor="profileImage" className="text-sm font-medium text-[#333]">프로필 이미지</label>
        <div className="flex items-center gap-6">
          <div className="w-28 h-28 rounded-full bg-[#F2F2F2] overflow-hidden">
            <img
              src={profileImageUrl || "/default_profile.png"}
              alt="프로필"
              className="w-full h-full object-cover"
              onError={(event) => {
                event.currentTarget.src = "/default_profile.png";
              }}
            />
          </div>
          <div className="flex-1">
            <input
              id="profileImage"
              name="profileImage"
              type="file"
              accept="image/*"
              className="hidden"
              onChange={handleImageUpload}
            />
            <label
              htmlFor="profileImage"
              className="inline-flex items-center gap-2 rounded-xl border border-[#DDD] px-4 py-2 text-sm cursor-pointer hover:bg-[#F7F7F7]"
            >
              <img src="/upload.svg" alt="업로드" className="w-4 h-4" />
              이미지 업로드
            </label>
          </div>
        </div>
      </div>

      <div className="space-y-2">
        <label htmlFor="nickname" className="text-sm font-medium text-[#333]">별명</label>
        <input
          id="nickname"
          name="nickname"
          type="text"
          placeholder="별명을 입력하세요"
          value={nickname}
          onChange={(event) => setNickname(event.target.value)}
          className="w-full rounded-xl border border-[#DDD] px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-black/20"
        />
      </div>

      <div className="space-y-2">
        <span className="text-sm font-medium text-[#333]">향수 관련 지식</span>
        <div className="flex gap-4">
          <button
            type="button"
            onClick={() => setUserMode("BEGINNER")}
            className={`flex-1 rounded-xl py-3 text-sm font-bold transition ${userMode === "BEGINNER" ? "bg-black text-white" : "bg-gray-200 text-gray-700"}`}
          >
            초보에요
          </button>
          <button
            type="button"
            onClick={() => setUserMode("EXPERT")}
            className={`flex-1 rounded-xl py-3 text-sm font-bold transition ${userMode === "EXPERT" ? "bg-black text-white" : "bg-gray-200 text-gray-700"}`}
          >
            경험자에요
          </button>
        </div>
      </div>
    </div>
  );

  return (
    <PageLayout className="h-screen bg-[#FDFBF8] text-black font-sans overflow-hidden flex flex-col">
      {popupContent && (
        <AgreementPopup
          title={popupContent.title}
          content={popupContent.content}
          onAgree={popupContent.onAgree}
          onClose={() => setPopupContent(null)}
        />
      )}

      <main className="flex-1 flex w-full h-full pt-[76px] items-center justify-center bg-[#FDFBF8] overflow-y-auto">
        <section className="w-full max-w-[480px] h-auto my-10 flex flex-col items-center justify-center bg-white rounded-2xl shadow-sm border border-gray-100 p-8 md:p-10 fade-in-up">
          <div className="w-full">
            <div className="space-y-2 mb-8 text-center md:text-left">
              <h2 className="text-2xl font-bold">회원가입</h2>
              <p className="text-sm text-[#666]">필수 정보를 입력해주세요.</p>
            </div>

            {/* Progress Bar */}
            <div className="w-full bg-gray-100 rounded-full h-2 mb-8">
              <div className="bg-black h-2 rounded-full transition-all duration-300" style={{ width: `${(currentStep / 4) * 100}%` }}></div>
            </div>

            <div className="space-y-5">
              {currentStep === 1 && renderStep1()}
              {currentStep === 2 && renderStep2()}
              {currentStep === 3 && renderStep3()}
              {currentStep === 4 && renderStep4()}
            </div>

            {submitMessage && (
              <p className="text-xs text-red-600 mt-4 text-center">{submitMessage}</p>
            )}

            <div className="flex gap-4 mt-8">
              {currentStep > 1 && (
                <button
                  type="button"
                  onClick={prevStep}
                  className="flex-1 py-3.5 rounded-xl font-bold bg-gray-100 text-gray-700 transition hover:bg-gray-200 text-sm"
                >
                  이전
                </button>
              )}
              {currentStep < 4 ? (
                <button
                  type="button"
                  onClick={nextStep}
                  disabled={
                    (currentStep === 1 && !canProceedStep1) ||
                    (currentStep === 2 && !canProceedStep2) ||
                    (currentStep === 3 && !canProceedStep3)
                  }
                  className={`flex-1 py-3.5 rounded-xl font-bold transition text-sm ${((currentStep === 1 && canProceedStep1) ||
                    (currentStep === 2 && canProceedStep2) ||
                    (currentStep === 3 && canProceedStep3))
                    ? "bg-black text-white hover:bg-gray-800 hover:shadow-lg hover:-translate-y-0.5"
                    : "bg-gray-200 text-gray-400 cursor-not-allowed"
                    }`}
                >
                  다음
                </button>
              ) : (
                <button
                  type="button"
                  onClick={handleSubmit}
                  disabled={!canProceedStep4 || isSubmitting}
                  className={`flex-1 py-3.5 rounded-xl font-bold transition text-sm ${canProceedStep4 && !isSubmitting
                    ? "bg-black text-white hover:bg-gray-800 hover:shadow-lg hover:-translate-y-0.5"
                    : "bg-gray-200 text-gray-400 cursor-not-allowed"
                    }`}
                >
                  {isSubmitting ? "가입중..." : "가입 완료"}
                </button>
              )}
            </div>

            <p className="text-center mt-6 text-xs text-gray-400">
              이미 계정이 있으신가요? <Link href="/login" className="text-black font-bold underline ml-1 hover:text-gray-700">로그인</Link>
            </p>
          </div>
        </section>
      </main>
    </PageLayout>
  );
}
