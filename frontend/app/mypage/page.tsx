'use client';

import { FormEvent, useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { useSession } from "next-auth/react";
import PageLayout from "@/components/common/PageLayout";
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
              if (typeof window !== "undefined") {
                localStorage.removeItem("localAuth");
              }
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
      <PageLayout className="min-h-screen bg-[#FDFBF8] text-black flex flex-col">
        <main className="flex-1 px-5 py-8 w-full max-w-md mx-auto pt-[120px]">
          <h2 className="text-2xl font-bold mb-3">마이페이지</h2>
          <p className="text-sm text-[#666]">로그인이 필요합니다.</p>
        </main>
      </PageLayout>
    );
  }

  return (
    <PageLayout subTitle="MY PAGE" className="min-h-screen bg-[#FDFBF8] text-black flex flex-col font-sans">

      <main className="flex-1 px-5 py-8 w-full max-w-2xl mx-auto pt-[120px] space-y-10">
        <div>
          <h2 className="text-2xl md:text-3xl font-bold tracking-tight">마이페이지</h2>
          <p className="text-sm text-[#666] mt-1.5 md:mt-2">회원정보를 관리할 수 있어요.</p>
          {loadMessage && (
            <p className="text-sm text-red-600 mt-2">{loadMessage}</p>
          )}
        </div>

        <form className="space-y-6 rounded-2xl border border-gray-100 bg-white p-5 md:p-8 shadow-sm" onSubmit={handleProfileSubmit}>
          <h3 className="text-lg md:text-xl font-bold">프로필</h3>

          <div className="flex flex-col md:flex-row items-center gap-6 md:gap-8 py-2">
            <div className="w-32 h-32 md:w-36 md:h-36 rounded-full bg-gray-50 overflow-hidden border border-gray-100 shadow-inner shrink-0">
              <img
                src={resolvedProfileImageUrl}
                alt="프로필"
                className="w-full h-full object-cover"
                onError={(event) => {
                  const target = event.currentTarget;
                  // [추가] 이미지 로드 실패 시 세션 이미지가 있으면 시도, 없으면 기본 이미지
                  if (session?.user?.image && target.src !== session.user.image) {
                    target.src = session.user.image;
                  } else {
                    target.src = "/default_profile.png";
                  }
                }}
              />
            </div>
            <div className="flex flex-col items-center md:items-start space-y-3">
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

        <section className="space-y-4 rounded-2xl border border-red-100 bg-red-50/50 p-5 md:p-8">
          <div>
            <h3 className="text-lg font-bold text-red-600">회원탈퇴</h3>
            <p className="text-[11px] md:text-sm text-red-400 mt-1">탈퇴 요청 시 계정은 탈퇴 요청 상태로 전환됩니다.</p>
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
    </PageLayout>
  );
}
