"use client";

/**
 * 향수 백과 메인 페이지
 * 각 시즌의 대표 시리즈를 카드 형태로 렌더링
 */
import Link from "next/link";
import { useState, useEffect } from "react";
import { useSession } from "next-auth/react";
import SeriesGrid from "@/components/perfume-wiki/SeriesGrid";
import perfumeWikiData from "./_data/perfumeWiki.json";
import type { PerfumeWikiData } from "./types";
import Sidebar from "@/components/common/sidebar";
import UserProfileMenu from "@/components/common/UserProfileMenu";

const data = perfumeWikiData as PerfumeWikiData;

/**
 * 시즌 데이터에서 각 시즌의 첫 번째 시리즈를 추출하여
 * 메인 페이지에 표시할 카드 목록 데이터 생성
 */
const seriesList = data.seasons.flatMap((season, index) => {
  const [primarySeries] = season.series;
  if (!primarySeries) {
    return [];
  }

  return [
    {
      ...primarySeries,
      seriesLabel: `Series ${index + 1}`,
      seasonTitle: season.title,
    },
  ];
});

export default function PerfumeWikiPage() {
  const { data: session } = useSession();
  const [isNavOpen, setIsNavOpen] = useState(false);
  const [isProfileMenuOpen, setIsProfileMenuOpen] = useState(false);
  const [localUser, setLocalUser] = useState<any>(null);
  const [profileImageUrl, setProfileImageUrl] = useState<string | null>(null);

  useEffect(() => {
    // 1. 로컬 스토리지 데이터 확인
    const authData = localStorage.getItem("localAuth");
    if (authData) {
      try {
        const parsed = JSON.parse(authData);
        setLocalUser(parsed);
      } catch (e) {
        console.error("Local auth parse error", e);
      }
    }

    // 2. 세션(카카오) 기반 프로필 이미지 가져오기
    if (session?.user?.id) {
      fetch(`/api/users/profile/${session.user.id}`)
        .then((res) => res.json())
        .then((data) => {
          if (data.profile_image_url) {
            setProfileImageUrl(data.profile_image_url);
          }
        })
        .catch((err) => console.error("Profile image fetch error", err));
    }
    // 3. 로컬 사용자 기반 프로필 이미지 가져오기
    else if (localUser?.memberId) {
      fetch(`/api/users/profile/${localUser.memberId}`)
        .then((res) => res.json())
        .then((data) => {
          if (data.profile_image_url) {
            setProfileImageUrl(data.profile_image_url);
          }
        })
        .catch((err) => console.error("Local profile image fetch error", err));
    }
  }, [session, localUser?.memberId]);

  const isLoggedIn = !!(session || localUser);

  return (
    <div className="min-h-screen bg-[#FDFBF8] text-[#2B2B2B] font-sans">
      <Sidebar
        isOpen={isNavOpen}
        onClose={() => setIsNavOpen(false)}
        context="home"
      />
      {isNavOpen && (
        <div
          className="fixed inset-0 bg-transparent z-40"
          onClick={() => setIsNavOpen(false)}
        />
      )}

      <header className="fixed top-0 left-0 right-0 z-30 flex items-center justify-between px-6 md:px-10 py-5 bg-[#FDFBF8] border-b border-[#F0F0F0]">
        <div className="flex items-center gap-4">
          <Link
            href="/"
            className="text-lg font-bold text-black tracking-[0.15em] uppercase hover:opacity-70 transition"
          >
            SCENTENCE
          </Link>
          <span className="text-xs font-semibold text-[#8C6A1D] tracking-[0.3em] uppercase border-l border-gray-300 pl-4 hidden sm:block">
            Perfume Wiki
          </span>
        </div>

        {/* 우측 상단 UI */}
        <div className="flex items-center gap-4">
          {!isLoggedIn ? (
            <div className="flex items-center gap-2 text-sm font-medium text-gray-400">
              <Link href="/login" className="hover:text-black transition-colors">Sign in</Link>
              <span className="text-gray-300">|</span>
              <Link href="/signup" className="hover:text-black transition-colors">Sign up</Link>
            </div>
          ) : (
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

      <main className="pt-[120px] pb-24 px-6 md:px-10 max-w-6xl mx-auto space-y-16">
        <section className="space-y-3">
          <h1 className="text-3xl md:text-4xl font-bold text-[#1F1F1F]">
            향수 백과
          </h1>
          <p className="text-sm md:text-base text-[#777]">
            향수에 대해 더 알아보고 싶다면 시리즈를 따라 향의 흐름을 배워보세요.
          </p>
        </section>

        <SeriesGrid series={seriesList} />
      </main>
    </div>
  );
}
