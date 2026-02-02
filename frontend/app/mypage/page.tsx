'use client';

import { FormEvent, useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { useSession } from "next-auth/react";
import Sidebar from "@/components/common/sidebar";
import UserProfileMenu from "@/components/common/UserProfileMenu";
import ImageCropperModal from './ImageCropperModal';

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
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);
  const [isProfileMenuOpen, setIsProfileMenuOpen] = useState(false);
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

  const apiBaseUrl = process.env.NEXT_PUBLIC_API_URL || "";
  const resolvedProfileImageUrl = profileImageUrl
    ? profileImageUrl.startsWith("http")
      ? profileImageUrl
      : `${apiBaseUrl}${profileImageUrl}`
    : "/default_profile.png";
  const checkedSnsJoinYn = profile?.sns_join_yn; // existing logic check
  const showPasswordSection = profile?.sns_join_yn !== "Y";

  const displayName = session?.user?.name || profile?.nickname || profile?.name || profile?.email?.split('@')[0] || "User";

  useEffect(() => {
    if (session?.user?.id) {
      setMemberId(String(session.user.id));
      return;
    }
    if (typeof window === "undefined") return;
    const stored = localStorage.getItem("localAuth");
    if (!stored) return;
    try {
      const parsed = JSON.parse(stored);
      if (parsed?.memberId) {
        setMemberId(String(parsed.memberId));
      }
    } catch (error) {
      return;
    }
  }, [session]);





  useEffect(() => {
    if (!memberId) return;
    const controller = new AbortController();

    const loadProfile = async () => {
      try {
        const response = await fetch(`/api/users/profile/${memberId}`, {
          signal: controller.signal,
        });
        if (!response.ok) {
          if (response.status === 404) {
            setLoadMessage("회원 정보를 찾을 수 없습니다. 다시 로그인해주세요.");
            if (typeof window !== "undefined") {
              localStorage.removeItem("localAuth");
            }
          }
          return;
        }
        const data = (await response.json()) as ProfileData;
        setProfile(data);
        if (data?.member_id) {
          setMemberId(String(data.member_id));
        }
        setNickname(data.nickname || "");
        setProfileImageUrl(data.profile_image_url || "");
        setName(data.name || "");
        setSex((data.sex as "M" | "F" | "") || "");
        setPhoneNo(data.phone_no || "");
        setAddress(data.address || "");
        setEmail(data.email || "");
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
  }, [apiBaseUrl, memberId, nickname]);

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

      if (typeof window !== "undefined") {
        const stored = localStorage.getItem("localAuth");
        if (stored) {
          try {
            const parsed = JSON.parse(stored);
            localStorage.setItem(
              "localAuth",
              JSON.stringify({
                ...parsed,
                nickname: nickname.trim() || null,
                email: email.trim() || parsed.email || null,
              })
            );
          } catch (error) {
            // ignore
          }
        }
      }

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
      <div className="min-h-screen bg-[#FDFBF8] text-black flex flex-col">
        <Sidebar
          isOpen={isSidebarOpen}
          onClose={() => setIsSidebarOpen(false)}
          context="home"
        />

        {/* [STANDARD HEADER] 메인 페이지(app/page.tsx)와 100% 동일한 구조 및 디자인 적용 */}
        <header className="fixed top-0 left-0 right-0 flex items-center justify-between px-5 py-4 bg-[#FDFBF8] border-b border-[#F0F0F0] z-50">
          {/* 로고 영역: font-bold, text-black, tracking-tight (표준) */}
          <Link href="/" className="text-xl font-bold text-black tracking-tight">
            Scentence
          </Link>

          {/* 우측 상단 UI: 로그인 상태 및 사이드바 토글 버튼 (표준) */}
          <div className="flex items-center gap-4">
            {/* 비로그인 상태 UI (메인과 동일) */}
            <div className="flex items-center gap-2 text-sm font-medium text-gray-400">
              <Link href="/login" className="hover:text-black transition-colors">Sign in</Link>
              <span className="text-gray-300">|</span>
              <Link href="/signup" className="hover:text-black transition-colors">Sign up</Link>
            </div>
            {/* 마이페이지에서도 전역 내비게이션 사용을 위해 Sidebar 토글 버튼 유지 */}
            <button
              id="global-menu-toggle"
              onClick={() => setIsSidebarOpen(!isSidebarOpen)}
              className="p-1 rounded-md hover:bg-gray-100 transition-colors"
            >
              {isSidebarOpen ? (
                <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" className="w-8 h-8 text-[#555]">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
                </svg>
              ) : (
                <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" className="w-8 h-8 text-[#555]">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M3.75 9h16.5m-16.5 6.75h16.5" />
                </svg>
              )}
            </button>
          </div>
        </header>

        <main className="flex-1 px-5 py-8 w-full max-w-md mx-auto pt-[120px]">
          <h2 className="text-2xl font-bold mb-3">마이페이지</h2>
          <p className="text-sm text-[#666]">로그인이 필요합니다.</p>
        </main>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#FDFBF8] text-black flex flex-col font-sans">
      <Sidebar
        isOpen={isSidebarOpen}
        onClose={() => setIsSidebarOpen(false)}
        context="home"
      />

      {isSidebarOpen && (
        <div
          className="fixed inset-0 bg-transparent z-40 md:hidden"
          onClick={() => setIsSidebarOpen(false)}
        />
      )}

      {/* [STANDARD HEADER] 메인 페이지(app/page.tsx)와 100% 동일한 구조 및 디자인 적용 */}
      <header className="fixed top-0 left-0 right-0 flex items-center justify-between px-6 md:px-10 py-5 bg-[#FDFBF8] border-b border-[#F0F0F0] z-50">
        {/* 로고 영역: font-bold, text-black, tracking-tight (표준) */}
        <Link href="/" className="text-lg font-bold text-black tracking-[0.15em] uppercase">
          SCENTENCE
        </Link>

        {/* 우측 상단 UI: 로그인 상태 및 사이드바 토글 버튼 (표준) */}
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-3">
            {/* 프로필 이미지 Link: 표준 크기(w-9 h-9) 및 스타일 적용 */}
            <button
              id="profile-menu-toggle"
              onClick={() => setIsProfileMenuOpen(!isProfileMenuOpen)}
              className="block w-9 h-9 rounded-full overflow-hidden border border-gray-100 shadow-sm hover:opacity-80 transition-opacity"
            >
              <img
                src={resolvedProfileImageUrl}
                alt="Profile"
                className="w-full h-full object-cover"
                onError={(e) => { e.currentTarget.src = "/default_profile.png"; }}
              />
            </button>
            <UserProfileMenu
              isOpen={isProfileMenuOpen}
              onClose={() => setIsProfileMenuOpen(false)}
            />
          </div>
          {/* 글로벌 내비게이션 토글 버튼 (px-5 py-4 패딩 및 w-8 h-8 규격 준수) */}
          <button
            id="global-menu-toggle"
            onClick={() => setIsSidebarOpen(!isSidebarOpen)}
            className="w-9 h-9 flex items-center justify-center rounded-full hover:bg-gray-100 transition-colors"
          >
            {isSidebarOpen ? (
              <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" className="w-8 h-8 text-[#555]">
                <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
              </svg>
            ) : (
              <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" className="w-8 h-8 text-[#555]">
                <path strokeLinecap="round" strokeLinejoin="round" d="M3.75 9h16.5m-16.5 6.75h16.5" />
              </svg>
            )}
          </button>
        </div>
      </header>

      <main className="flex-1 px-5 py-8 w-full max-w-2xl mx-auto pt-[120px] space-y-10">
        <div>
          <h2 className="text-3xl font-bold tracking-tight">마이페이지</h2>
          <p className="text-sm text-[#666] mt-2">회원정보를 관리할 수 있어요.</p>
          {loadMessage && (
            <p className="text-sm text-red-600 mt-2">{loadMessage}</p>
          )}
        </div>

        <form className="space-y-6 rounded-2xl border border-gray-100 bg-white p-8 shadow-sm" onSubmit={handleProfileSubmit}>
          <h3 className="text-xl font-bold">프로필</h3>

          <div className="flex items-center gap-8 py-2">
            <div className="w-28 h-28 rounded-full bg-gray-50 overflow-hidden border border-gray-100 shadow-inner">
              <img
                src={resolvedProfileImageUrl}
                alt="프로필"
                className="w-full h-full object-cover"
                onError={(event) => {
                  event.currentTarget.src = "/default_profile.png";
                }}
              />
            </div>
            <div className="flex-1 space-y-3">
              <input
                id="profileImage"
                name="profileImage"
                type="file"
                accept="image/*"
                className="hidden"
                onChange={(event) => {
                  const file = event.target.files?.[0];
                  if (file) {
                    // 파일을 읽어서 URL로 변환 후 모달 열기
                    const reader = new FileReader();
                    reader.addEventListener("load", () => {
                      setSelectedFile(reader.result?.toString() || null);
                      setIsCropperOpen(true);
                    });
                    reader.readAsDataURL(file);
                    // 동일 파일 다시 선택 가능하도록 초기화
                    event.target.value = "";
                  }
                }}
              />
              <label
                htmlFor="profileImage"
                className="inline-flex items-center gap-2 rounded-xl border border-gray-200 px-4 py-2.5 text-sm font-medium cursor-pointer hover:bg-gray-50 transition-colors"
              >
                <img src="/upload.svg" alt="업로드" className="w-4 h-4 opacity-60" />
                이미지 변경
              </label>
              {isUploadingImage && (
                <p className="text-xs text-[#666] ml-2 animate-pulse">업로드 중...</p>
              )}
            </div>
          </div>

          <div className="space-y-2">
            <label htmlFor="nickname" className="text-sm font-bold text-gray-700">닉네임</label>
            <input
              id="nickname"
              name="nickname"
              type="text"
              value={nickname}
              onChange={(event) => setNickname(event.target.value)}
              placeholder="닉네임을 입력하세요"
              className="w-full rounded-xl border border-gray-200 px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-black/10 transition-shadow"
            />
            {nicknameHint && (
              <p className={`text-xs ${nicknameStatus === "available" ? "text-green-600" : "text-red-600"}`}>
                {nicknameHint}
              </p>
            )}
          </div>

          <div className="space-y-2">
            <label htmlFor="subEmail" className="text-sm font-bold text-gray-700">복구 이메일 (선택)</label>
            <input
              id="subEmail"
              name="subEmail"
              type="email"
              value={subEmail}
              onChange={(event) => setSubEmail(event.target.value)}
              placeholder="계정 복구용 이메일을 입력하세요"
              className="w-full rounded-xl border border-gray-200 px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-black/10 transition-shadow"
            />
          </div>

          <div className="pt-6 pb-2 border-t border-gray-100">
            <h3 className="text-lg font-bold mb-4">기본정보</h3>

            <div className="space-y-5">
              <div className="space-y-2">
                <label htmlFor="name" className="text-sm font-bold text-gray-700">이름</label>
                <input
                  id="name"
                  name="name"
                  type="text"
                  value={name}
                  onChange={(event) => setName(event.target.value)}
                  placeholder="이름을 입력하세요"
                  className="w-full rounded-xl border border-gray-200 px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-black/10 transition-shadow"
                />
              </div>

              <div className="space-y-2">
                <span className="text-sm font-bold text-gray-700">성별</span>
                <div className="flex gap-6 pt-1">
                  <label className="flex items-center gap-2 text-sm cursor-pointer group">
                    <input
                      type="radio"
                      name="sex"
                      value="M"
                      checked={sex === "M"}
                      onChange={() => setSex("M")}
                      className="accent-black w-4 h-4"
                    />
                    <span className="group-hover:text-black text-gray-600">남자</span>
                  </label>
                  <label className="flex items-center gap-2 text-sm cursor-pointer group">
                    <input
                      type="radio"
                      name="sex"
                      value="F"
                      checked={sex === "F"}
                      onChange={() => setSex("F")}
                      className="accent-black w-4 h-4"
                    />
                    <span className="group-hover:text-black text-gray-600">여자</span>
                  </label>
                </div>
              </div>

              <div className="space-y-2">
                <label htmlFor="phoneNo" className="text-sm font-bold text-gray-700">핸드폰번호</label>
                <input
                  id="phoneNo"
                  name="phoneNo"
                  type="text"
                  value={phoneNo}
                  onChange={(event) => setPhoneNo(event.target.value)}
                  placeholder="핸드폰번호를 입력하세요"
                  className="w-full rounded-xl border border-gray-200 px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-black/10 transition-shadow"
                />
              </div>

              <div className="space-y-2">
                <label htmlFor="address" className="text-sm font-bold text-gray-700">주소</label>
                <input
                  id="address"
                  name="address"
                  type="text"
                  value={address}
                  onChange={(event) => setAddress(event.target.value)}
                  placeholder="주소를 입력하세요"
                  className="w-full rounded-xl border border-gray-200 px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-black/10 transition-shadow"
                />
              </div>

              <div className="space-y-2">
                <label htmlFor="email" className="text-sm font-bold text-gray-700">이메일</label>
                <input
                  id="email"
                  name="email"
                  type="email"
                  value={email}
                  onChange={(event) => setEmail(event.target.value)}
                  placeholder="이메일을 입력하세요"
                  className="w-full rounded-xl border border-gray-200 px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-black/10 transition-shadow"
                />
              </div>
            </div>
          </div>

          <div className="pt-4 border-t border-gray-100">
            <h3 className="text-lg font-bold mb-4">알림설정</h3>

            <div className="space-y-3">
              <label className="flex items-center gap-3 text-sm cursor-pointer p-3 rounded-xl border border-gray-100 bg-gray-50 hover:bg-white hover:border-black/10 transition-all">
                <input
                  type="checkbox"
                  className="accent-black w-4 h-4"
                  checked={emailMarketing}
                  onChange={(event) => setEmailMarketing(event.target.checked)}
                />
                <span className="font-medium">이메일 알림 수신</span>
              </label>
              <label className="flex items-center gap-3 text-sm cursor-pointer p-3 rounded-xl border border-gray-100 bg-gray-50 hover:bg-white hover:border-black/10 transition-all">
                <input
                  type="checkbox"
                  className="accent-black w-4 h-4"
                  checked={snsMarketing}
                  onChange={(event) => setSnsMarketing(event.target.checked)}
                />
                <span className="font-medium">SNS 알림 수신</span>
              </label>
            </div>
          </div>

          {profileMessage && (
            <div className="p-3 bg-gray-50 rounded-lg text-center">
              <p className="text-sm font-medium text-black">{profileMessage}</p>
            </div>
          )}

          <button
            type="submit"
            disabled={isSubmittingProfile}
            className={`w-full py-4 rounded-xl font-bold text-lg transition shadow-md ${isSubmittingProfile
              ? "bg-gray-300 text-gray-500 cursor-not-allowed"
              : "bg-black text-white hover:bg-gray-900 active:scale-[0.99]"
              }`}
          >
            저장하기
          </button>
        </form>

        {showPasswordSection && (
          <form className="space-y-6 rounded-2xl border border-gray-100 bg-white p-8 shadow-sm" onSubmit={handlePasswordSubmit}>
            <h3 className="text-xl font-bold">비밀번호 변경</h3>

            <div className="space-y-2">
              <label htmlFor="currentPassword" className="text-sm font-bold text-gray-700">현재 비밀번호</label>
              <input
                id="currentPassword"
                name="currentPassword"
                type="password"
                value={currentPassword}
                onChange={(event) => setCurrentPassword(event.target.value)}
                placeholder="현재 비밀번호를 입력하세요"
                className="w-full rounded-xl border border-gray-200 px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-black/10 transition-shadow"
              />
            </div>

            <div className="space-y-2">
              <label htmlFor="newPassword" className="text-sm font-bold text-gray-700">새 비밀번호</label>
              <input
                id="newPassword"
                name="newPassword"
                type="password"
                value={newPassword}
                onChange={(event) => setNewPassword(event.target.value)}
                placeholder="새 비밀번호를 입력하세요"
                className="w-full rounded-xl border border-gray-200 px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-black/10 transition-shadow"
              />
            </div>

            <div className="space-y-2">
              <label htmlFor="confirmPassword" className="text-sm font-bold text-gray-700">새 비밀번호 확인</label>
              <input
                id="confirmPassword"
                name="confirmPassword"
                type="password"
                value={confirmPassword}
                onChange={(event) => setConfirmPassword(event.target.value)}
                placeholder="새 비밀번호를 다시 입력하세요"
                className="w-full rounded-xl border border-gray-200 px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-black/10 transition-shadow"
              />
            </div>

            {passwordMessage && (
              <div className="p-3 bg-gray-50 rounded-lg text-center">
                <p className="text-sm font-medium text-black">{passwordMessage}</p>
              </div>
            )}

            <button
              type="submit"
              disabled={isSubmittingPassword}
              className={`w-full py-4 rounded-xl font-bold text-lg transition shadow-md ${isSubmittingPassword
                ? "bg-gray-300 text-gray-500 cursor-not-allowed"
                : "bg-black text-white hover:bg-gray-900 active:scale-[0.99]"
                }`}
            >
              비밀번호 변경
            </button>
          </form>
        )}

        <section className="space-y-4 rounded-2xl border border-red-100 bg-red-50/50 p-8">
          <div>
            <h3 className="text-lg font-bold text-red-600">회원탈퇴</h3>
            <p className="text-sm text-red-400 mt-1">탈퇴 요청 시 계정은 탈퇴 요청 상태로 전환됩니다.</p>
          </div>

          <button
            type="button"
            onClick={async () => {
              if (!memberId) return;
              if (!window.confirm("탈퇴 요청일로부터 7일까지는 데이터가 유지됩니다. 정말 탈퇴처리하시겠습니까?")) return;
              try {
                const response = await fetch(`/api/users/profile/${memberId}/withdraw`, {
                  method: "POST",
                });
                if (!response.ok) {
                  const data = await response.json().catch(() => null);
                  setProfileMessage(data?.detail || "탈퇴 요청에 실패했습니다.");
                  return;
                }
                setProfileMessage("탈퇴 요청이 완료되었습니다.");
                if (typeof window !== "undefined") {
                  localStorage.removeItem("localAuth");
                  window.location.href = "/";
                }
              } catch (error) {
                setProfileMessage("탈퇴 요청에 실패했습니다.");
              }
            }}
            className="w-full py-3 rounded-xl font-bold text-red-600 border border-red-200 bg-white hover:bg-red-50 transition"
          >
            회원탈퇴
          </button>
        </section>
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
    </div>
  );
}
