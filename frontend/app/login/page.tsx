'use client';

import { FormEvent, useState } from "react";
import Link from "next/link";
import PageLayout from "@/components/common/PageLayout";

export default function LoginPage() {
  const [loginId, setLoginId] = useState("");
  const [password, setPassword] = useState("");
  const [submitMessage, setSubmitMessage] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const apiBaseUrl = "/api";

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
      const response = await fetch(`${apiBaseUrl}/users/login/local`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          email: loginId.trim(),
          password,
        }),
      });

      if (!response.ok) {
        const data = await response.json().catch(() => null);
        setSubmitMessage(data?.detail || "로그인에 실패했습니다.");
        return;
      }
      const data = await response.json().catch(() => null);
      if (data?.withdraw_pending && data?.member_id) {
        window.location.href = `/recover?memberId=${data.member_id}`;
        return;
      }
      let nickname = null;
      let roleType = data?.role_type ?? null;
      if (data?.member_id) {
        const profileResponse = await fetch(`/api/users/profile/${data.member_id}`);
        if (profileResponse.ok) {
          const profileData = await profileResponse.json().catch(() => null);
          nickname = profileData?.nickname ?? null;
          roleType = profileData?.role_type ?? roleType;
        }
      }
      if (typeof window !== "undefined") {
        const userMode = data?.user_mode || "BEGINNER"; // [추가]
        localStorage.setItem(
          "localAuth",
          JSON.stringify({
            memberId: data?.member_id ?? null,
            email: loginId.trim(),
            nickname,
            // roleType removed for security
            user_mode: userMode,
            loggedInAt: new Date().toISOString(),
          })
        );
      }
      window.location.href = "/";
    } catch (error) {
      setSubmitMessage("로그인에 실패했습니다.");
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <PageLayout className="h-screen bg-[#FDFBF8] text-black font-sans overflow-hidden flex flex-col">

      {/* [MAIN CONTENT] Split View (Gallery Look) */}
      <main className="flex-1 flex w-full h-full pt-[76px] items-center justify-center bg-[#FDFBF8]">
        <section className="w-full max-w-[420px] h-auto flex flex-col items-center justify-center bg-white rounded-2xl shadow-sm border border-gray-100 p-8 md:p-10 fade-in-up">
          <div className="w-full">

            <div className="mb-10 text-center md:text-left">
              <h2 className="text-3xl font-bold mb-3 tracking-tight text-gray-900">Welcome Back</h2>
              <p className="text-sm text-gray-500">
                오늘도 당신만의 향기를 찾아보세요.
              </p>
            </div>

            <form className="space-y-5" onSubmit={handleSubmit}>
              <div className="space-y-1.5">
                <label htmlFor="loginId" className="text-xs font-bold text-gray-500 uppercase tracking-wider ml-1">ID</label>
                <input
                  id="loginId"
                  name="loginId"
                  type="text"
                  placeholder="아이디를 입력하세요"
                  value={loginId}
                  onChange={(event) => setLoginId(event.target.value)}
                  className="w-full rounded-xl border border-gray-200 bg-gray-50 px-4 py-3.5 text-sm focus:bg-white focus:border-black focus:outline-none focus:ring-1 focus:ring-black transition-all"
                />
              </div>

              <div className="space-y-1.5">
                <div className="flex justify-between items-center ml-1">
                  <label htmlFor="password" className="text-xs font-bold text-gray-500 uppercase tracking-wider">Password</label>
                </div>
                <input
                  id="password"
                  name="password"
                  type="password"
                  placeholder="비밀번호를 입력하세요"
                  value={password}
                  onChange={(event) => setPassword(event.target.value)}
                  className="w-full rounded-xl border border-gray-200 bg-gray-50 px-4 py-3.5 text-sm focus:bg-white focus:border-black focus:outline-none focus:ring-1 focus:ring-black transition-all"
                />
              </div>

              <div className="flex justify-end pt-1">
                <button
                  type="button"
                  className="text-xs text-gray-400 hover:text-black transition-colors"
                >
                  비밀번호 찾기
                </button>
              </div>

              {submitMessage && (
                <div className="p-3 bg-red-50 text-red-600 text-xs rounded-lg text-center font-medium">
                  {submitMessage}
                </div>
              )}

              <button
                type="submit"
                disabled={isSubmitting}
                className={`w-full py-4 rounded-xl font-bold text-base transition-all shadow-lg shadow-gray-200 ${isSubmitting
                  ? "bg-gray-200 text-gray-400 cursor-not-allowed"
                  : "bg-black text-white hover:bg-gray-800 hover:shadow-xl hover:-translate-y-0.5"
                  }`}
              >
                로그인
              </button>

              <div className="relative flex py-2 items-center">
                <div className="flex-grow border-t border-gray-100"></div>
                <span className="flex-shrink-0 mx-4 text-xs text-gray-300 font-medium">OR</span>
                <div className="flex-grow border-t border-gray-100"></div>
              </div>

              <button
                type="button"
                onClick={handleKakaoPopup}
                className="w-full bg-[#FEE500] text-[#3c1e1e] py-3.5 rounded-xl font-bold flex items-center justify-center gap-2 hover:bg-[#ffe812] transition-colors"
              >
                <span className="inline-flex items-center justify-center w-5 h-5">
                  {/* 카카오 심볼 (SVG로 대체하거나 텍스트 유지) */}
                  <svg viewBox="0 0 24 24" fill="currentColor" className="w-full h-full"><path d="M12 3C5.373 3 0 7.373 0 12.768c0 3.657 2.456 6.829 6.138 8.49L4.2 24l5.414-3.606c.767.098 1.556.15 2.386.15 6.627 0 12-4.373 12-9.768C24 7.373 18.627 3 12 3z" /></svg>
                </span>
                카카오 로그인
              </button>
            </form>

            <p className="text-center mt-10 text-xs text-gray-400">
              아직 회원이 아니신가요? <Link href="/signup" className="text-black font-bold underline ml-1 hover:text-gray-700">회원가입</Link>
            </p>
          </div>
        </section>
      </main>
    </PageLayout>
  );
}
