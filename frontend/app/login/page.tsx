'use client';

import { FormEvent, useState } from "react";
import Link from "next/link";
import Sidebar from "@/components/common/sidebar";

export default function LoginPage() {
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);
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
            roleType: roleType,
            user_mode: userMode, // [추가]
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
    <div className="h-screen bg-[#FDFBF8] text-black font-sans overflow-hidden flex flex-col">
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

      {/* [STANDARD HEADER] 표준 디자인 */}
      <header className="fixed top-0 left-0 right-0 flex items-center justify-between px-6 md:px-10 py-5 bg-[#FDFBF8]/95 backdrop-blur-sm border-b border-[#F0F0F0] z-50 transition-all">
        <Link href="/" className="text-lg font-bold text-black tracking-[0.15em] uppercase hover:opacity-70 transition">
          SCENTENCE
        </Link>

        {/* 우측 상단 UI */}
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2 text-sm font-medium text-gray-400">
            <Link href="/login" className="text-black pointer-events-none">Sign in</Link>
            <span className="text-gray-300">|</span>
            <Link href="/signup" className="hover:text-black transition-colors">Sign up</Link>
          </div>
          <button
            onClick={() => setIsSidebarOpen(true)}
            className="w-9 h-9 flex items-center justify-center rounded-full hover:bg-gray-100 transition-colors"
          >
            <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" className="w-6 h-6 text-[#333]">
              <path strokeLinecap="round" strokeLinejoin="round" d="M3.75 9h16.5m-16.5 6.75h16.5" />
            </svg>
          </button>
        </div>
      </header>

      {/* [MAIN CONTENT] Split View (Gallery Look) */}
      <main className="flex-1 flex w-full h-full pt-[76px]">

        {/* [LEFT] Image Section (Desktop Only) */}
        <section className="hidden md:block w-1/2 h-full relative overflow-hidden bg-gray-100 border-r border-[#F0F0F0]">
          <div className="absolute inset-0">
            {/* 
                 랜덤 이미지 혹은 고정 이미지 사용.
                 'archive_s1.png' 같은 감성적인 컷도 좋고, 'news1.png' 같은 화보 컷도 좋음.
                 여기서는 제안드린 'news1.png' 사용.
             */}
            <img
              src="/perfumes/news1.png"
              alt="Login Visual"
              className="w-full h-full object-cover grayscale-[20%] hover:grayscale-0 transition-all duration-1000 ease-in-out scale-105 hover:scale-100"
            />
            {/* Overlay for mood */}
            <div className="absolute inset-0 bg-black/5" />
          </div>
          <div className="absolute bottom-10 left-10 text-white z-10 drop-shadow-md">
            <p className="text-3xl font-bold tracking-widest uppercase mb-2">Archive</p>
            <p className="text-sm font-light tracking-wider opacity-90">당신의 향기를 기록하고 발견하세요.</p>
          </div>
        </section>

        {/* [RIGHT] Login Form Section */}
        <section className="w-full md:w-1/2 h-full flex items-center justify-center overflow-y-auto bg-white">
          <div className="w-full max-w-[420px] px-6 py-10 fade-in-up">

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
    </div>
  );
}
