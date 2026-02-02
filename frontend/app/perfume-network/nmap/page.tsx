"use client";

import React, { useEffect, useState } from 'react';
import { useSession } from 'next-auth/react';
import Link from "next/link";
import Sidebar from "@/components/common/sidebar";
import UserProfileMenu from "@/components/common/UserProfileMenu";
import NMapView from './NMapView';

/**
 * 향수 맵(NMap) 결과 페이지
 * 세션 정보를 관리하고 메인 뷰(NMapView)를 렌더링합니다.
 */
export default function NMapPage() {
  const { data: session } = useSession();
  const [sessionUserId, setSessionUserId] = useState<string | number | undefined>(undefined);

  // ==================== [NEW] 전역 헤더 및 프로필 상태 ====================
  const [isNavOpen, setIsNavOpen] = useState(false);
  const [isProfileMenuOpen, setIsProfileMenuOpen] = useState(false);
  const [localUser, setLocalUser] = useState<any>(null);
  const [profileImageUrl, setProfileImageUrl] = useState<string | null>(null);
  const [isMounted, setIsMounted] = useState(false);

  // API 호출 경로 설정
  const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

  useEffect(() => {
    setIsMounted(true);
  }, []);

  useEffect(() => {
    // 1. Next-Auth 세션에서 ID 확인
    if (session?.user) {
      const id = (session.user as any).id;
      if (id) {
        setSessionUserId(id);
        return;
      }
    }

    // 2. 로컬 스토리지에서 인증 정보 확인
    const storedAuth = localStorage.getItem('localAuth');
    if (storedAuth) {
      try {
        const parsed = JSON.parse(storedAuth);
        if (parsed.memberId) {
          setSessionUserId(parsed.memberId);
        }
      } catch (e) {
        console.error('Failed to parse localAuth:', e);
      }
    }
  }, [session]);

  // [Profile Logic] 로그인 사용자 정보 및 이미지 연동
  useEffect(() => {
    const authData = localStorage.getItem("localAuth");
    if (authData) {
      try {
        setLocalUser(JSON.parse(authData));
      } catch (e) {
        console.error("Local auth parse error", e);
      }
    }

    const memberId = session?.user?.id || (localUser?.memberId);
    if (memberId) {
      fetch(`${API_URL}/users/profile/${memberId}`)
        .then((res) => res.json())
        .then((data) => {
          if (data.profile_image_url) {
            setProfileImageUrl(data.profile_image_url);
          }
        })
        .catch((err) => console.error("Profile image fetch error", err));
    }
  }, [session, localUser?.memberId]);

  const displayName = session?.user?.name || localUser?.userName || "사용자";
  const isLoggedIn = !!(session || localUser);

  return (
    <div className="relative font-sans text-black">
      {/* ==================== [NEW] Sidebar ==================== */}
      <Sidebar
        isOpen={isNavOpen}
        onClose={() => setIsNavOpen(false)}
        context="home"
      />

      {/* [STANDARD HEADER] 메인 페이지(app/page.tsx)와 100% 동일한 구조 및 디자인 적용 */}
      <header className="fixed top-0 left-0 right-0 z-50 flex items-center justify-between px-6 md:px-10 py-5 bg-[#FDFBF8] border-b border-[#F0F0F0]">
        {/* 로고 영역: font-bold, text-black, tracking-tight (표준) */}
        <Link href="/" className="text-lg font-bold text-black tracking-[0.15em] uppercase">
          SCENTENCE
        </Link>

        {/* 우측 상단 UI: 로그인 상태 및 사이드바 토글 버튼 (표준) */}
        <div className="flex items-center gap-4">
          {!isLoggedIn ? (
            // 비로그인 상태 UI
            <div className="flex items-center gap-2 text-sm font-medium text-gray-400">
              <Link href="/login" className="hover:text-black transition-colors">Sign in</Link>
              <span className="text-gray-300">|</span>
              <Link href="/signup" className="hover:text-black transition-colors">Sign up</Link>
            </div>
          ) : (
            // 로그인 상태 UI: 이름과 프로필 이미지
            <div className="flex items-center gap-3">
              <button
                id="profile-menu-toggle"
                onClick={() => setIsProfileMenuOpen(!isProfileMenuOpen)}
                className="block w-9 h-9 rounded-full overflow-hidden border border-gray-100 shadow-sm hover:opacity-80 transition-opacity"
              >
                <img
                  src={profileImageUrl || "/default_profile.png"}
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
          )}

          {/* 글로벌 내비게이션 토글 버튼 (px-5 py-4 패딩 및 w-8 h-8 규격 준수) */}
          {/* 글로벌 내비게이션 토글 버튼 (px-5 py-4 패딩 및 w-8 h-8 규격 준수) */}
          <button
            id="global-menu-toggle"
            onClick={() => setIsNavOpen(!isNavOpen)}
            className="w-9 h-9 flex items-center justify-center rounded-full hover:bg-gray-100 transition-colors"
          >
            {isNavOpen ? (
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

      <main className="pt-[72px]">
        <NMapView sessionUserId={sessionUserId} />
      </main>
    </div>
  );
}
