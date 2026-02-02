"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { useSession } from "next-auth/react"; // [Login Check]
import MaximumCounter from "@/components/perfume-wiki/MaximumCounter"; // (만약 사용하는 경우 유지, 없으면 삭제 가능하지만 기존 import 유지)
import Sidebar from "@/components/common/sidebar";
import UserProfileMenu from "@/components/common/UserProfileMenu";

export default function LandingPage() {
  const router = useRouter();
  const { data: session } = useSession(); // [Login Check]
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);
  const [isProfileMenuOpen, setIsProfileMenuOpen] = useState(false);

  // [Profile Logic] 로그인 사용자 정보 확인
  const [localUser, setLocalUser] = useState<{ memberId?: string | null; email?: string | null; nickname?: string | null; roleType?: string | null; isAdmin?: boolean } | null>(null);
  const [profileImageUrl, setProfileImageUrl] = useState<string | null>(null);

  // 최신 닉네임을 저장할 State 추가
  const [profileNickname, setProfileNickname] = useState<string | null>(null);

  useEffect(() => {
    if (typeof window === "undefined") return;
    const stored = localStorage.getItem("localAuth");
    if (stored) {
      try {
        setLocalUser(JSON.parse(stored));
      } catch (error) {
        setLocalUser(null);
      }
    }
  }, []);

  useEffect(() => {
    if (typeof window === "undefined") return;
    const apiBaseUrl = process.env.NEXT_PUBLIC_API_URL || "";
    const memberId = session?.user?.id || localUser?.memberId;

    if (!memberId) {
      setProfileImageUrl(null);
      return;
    }

    fetch(`${apiBaseUrl}/users/profile/${memberId}`)
      .then((res) => (res.ok ? res.json() : null))
      .then((data) => {
        // 가져온 데이터에 닉네임이 있으면 저장하기
        if (data?.nickname) {
          setProfileNickname(data.nickname);
        }
        if (data?.profile_image_url) {
          const url = data.profile_image_url.startsWith("http")
            ? data.profile_image_url
            : `${apiBaseUrl}${data.profile_image_url}`;
          setProfileImageUrl(url);
        }
      })
      .catch(() => setProfileImageUrl(null));
  }, [localUser, session]);

  // [Display Name Logic]
  const displayName = profileNickname || session?.user?.name || localUser?.nickname || localUser?.email?.split('@')[0] || "Guest";
  const isLoggedIn = Boolean(session || localUser);

  const handleNewChat = () => {
    router.push("/chat");
  };

  const handleCreateScentCard = () => {
    router.push("/scent-card");
  };

  return (
    <div className="flex h-screen bg-[#FDFBF8] overflow-hidden text-black relative font-sans">

      {/* 1. 스마트 사이드바 (context="home") -> 이제 팝오버 메뉴 역할 */}
      <Sidebar
        isOpen={isSidebarOpen}
        onClose={() => setIsSidebarOpen(false)}
        context="home"
      />

      <main className="flex-1 flex flex-col relative w-full h-full overflow-y-auto no-scrollbar pb-8 pt-[72px]">
        {/* 사이드바 열렸을 때 배경 어둡게 처리 -> 팝오버로 변경되므로 제거할 수도 있지만, 모바일 고려해 투명 오버레이는 Sidebar 내부에서 처리하는 게 나을 수도 있음. 
            기존 코드는 유지하되 Sidebar 컴포넌트가 알아서 처리하도록 둠. 
            여기선 '모바일용 배경'은 팝오버 스타일엔 굳이 필요 없거나 투명하게 처리. 
            일단 기존 배경 어둡게 처리는 유지 (Overlay 역할) 하거나, 
            팝오버 스타일(모달성 아님)을 원하면 제거. 
            사용자 요청 "팝오버"는 보통 모달 오버레이가 진하지 않음. 
            여기서는 `z-40` 오버레이를 제거하고 Sidebar 컴포넌트 내부에서 처리하게 변경 권장.
            하지만 안전하게 기존 코드 유지.
        */}


        <header className="fixed top-0 left-0 right-0 z-30 flex items-center justify-between px-6 md:px-10 py-5 bg-[#FDFBF8] border-b border-[#F0F0F0]">
          {/* 로고 영역: Wiki와 동일하게 div로 감싸 구조 통일 */}
          <div className="flex items-center gap-4">
            <Link href="/" className="text-lg font-bold text-black tracking-[0.15em] uppercase hover:opacity-70 transition">
              SCENTENCE
            </Link>
          </div>

          {/* 우측 상단 UI: Perfume Wiki와 동일하게 통일 (Welcome Msg 제거하여 위치 통일) */}
          <div className="flex items-center gap-4">
            {!isLoggedIn ? (
              <div className="flex items-center gap-2 text-sm font-medium text-gray-400">
                <Link href="/login" className="hover:text-black transition-colors">Sign in</Link>
                <span className="text-gray-300">|</span>
                <Link href="/signup" className="hover:text-black transition-colors">Sign up</Link>
              </div>
            ) : (
              <div className="flex items-center gap-3">
                <span className="hidden md:inline-block text-sm font-medium text-gray-600 mr-2">
                  <strong className="font-bold text-gray-900">{displayName}</strong>님 반가워요!
                </span>
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

        <div className="px-5 space-y-8 mt-6 w-full max-w-3xl mx-auto">
          {/* 3. HERO CAROUSEL */}
          <section className="relative w-full aspect-[4/3.5] bg-[#E0E0E0] rounded-2xl overflow-hidden group">
            <div
              className="flex w-full h-full overflow-x-auto snap-x snap-mandatory no-scrollbar"
              id="hero-carousel"
              style={{ scrollBehavior: 'smooth' }}
            >
              {[1, 2, 3].map((num) => (
                <div key={num} className="snap-center shrink-0 w-full h-full relative">
                  <img
                    src={`/perfumes/news${num}.png`}
                    alt={`News ${num}`}
                    className="w-full h-full object-cover"
                  />
                  <div className="absolute inset-0 bg-gradient-to-t from-black/50 via-transparent to-transparent opacity-60" />
                </div>
              ))}
            </div>
            <div className="absolute bottom-4 right-4 bg-black/60 backdrop-blur-sm text-white text-xs px-3 py-1 rounded-full font-medium z-10">
              News
            </div>
          </section>

          {/* 자동 스크롤 스크립트 실행 */}
          <AutoScrollScript />

          {/* 4. QUICK MENU BUTTONS */}
          {/* 버튼 반응 추가 */}
          <section className="flex gap-4">
            <button className="flex-1 bg-[#C8A24D] py-4 rounded-xl text-center text-sm font-bold text-white transition-transform active:scale-95 duration-200 shadow-[0_6px_16px_rgba(200,162,77,0.35)] hover:bg-[#B89138]">
              향수 백과
            </button>
            <button
              onClick={handleNewChat}
              className="flex-1 bg-[#C8A24D] py-4 rounded-xl text-center text-sm font-bold text-white transition-transform active:scale-95 duration-200 shadow-[0_6px_16px_rgba(200,162,77,0.35)] hover:bg-[#B89138]"
            >
              향수 추천
            </button>
          </section>

          {/* 5. SCENTENCE PICK */}
          <section className="space-y-4">
            <h3 className="text-lg font-bold text-black">Scentence Pick</h3>
            <div className="flex gap-4 overflow-x-auto no-scrollbar pb-2">
              {[
                { file: "Angels Share Paradis By Kilian (unisex).png", name: "Angels' Share", brand: "By Kilian" },
                { file: "Angham Lattafa Perfumes (unisex).png", name: "Angham", brand: "Lattafa Perfumes" },
                { file: "BaldAfrique Absolu Byredo (unisex).png", name: "Bal d'Afrique Absolu", brand: "Byredo" },
                { file: "Fleur de Peau Eau de Toilette Diptyque (unisex).png", name: "Fleur de Peau", brand: "Diptyque" },
                { file: "Guidance 46 Amouage (unisex).png", name: "Guidance 46", brand: "Amouage" },
                { file: "Shalimar_L_Essence Guerlain (female).png", name: "Shalimar L'Essence", brand: "Guerlain" },
                { file: "Tilia Marc-Antoine Barrois (unisex).png", name: "Tilia", brand: "Marc-Antoine Barrois" },
                { file: "Valaya Exclusif Parfums de Marly (female).png", name: "Valaya Exclusif", brand: "Parfums de Marly" },
                { file: "Yum Boujee Marshmallow_81 Kayali Fragrances (female).png", name: "Yum Boujee Marshmallow", brand: "Kayali" }
              ].map((item, idx) => (
                <div key={idx} className="shrink-0 w-32 flex flex-col gap-2">
                  <div className="w-32 h-32 bg-[#E0E0E0] rounded-2xl overflow-hidden">
                    <img src={`/perfumes/${item.file}`} alt={item.name} className="w-full h-full object-cover" />
                  </div>
                  <div className="text-xs text-center">
                    <p className="font-bold text-[#333] truncate">{item.name}</p>
                    <p className="text-[#666] truncate">{item.brand}</p>
                  </div>
                </div>
              ))}
            </div>
          </section>

          {/* 6. SCENTENCE 어떠신가요? --> 나만의 향기 카드 */}
          <section className="space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="text-lg font-bold text-black">나만의 향기 카드</h3>
                <p className="text-xs text-[#666]">사용자들이 공유한 향기 카드를 둘러보세요</p>
              </div>
              {/* <button className="hidden sm:inline-flex items-center gap-2 px-3 py-2 rounded-full border border-[#D9B45A] text-[#8C6A1D] bg-[#FFF7E1] text-xs font-semibold hover:bg-[#FFEFC3] transition">
                공유 피드
              </button> */}
            </div>

            <div className="flex gap-4 overflow-x-auto no-scrollbar snap-x snap-mandatory pb-2">
              {[
                {
                  serial: "SC-001",
                  imageLabel: "향 캐릭터 이름",
                  mood: "#데이트 #무드",
                  title: "비 오는 날의 홍차",
                  user: "@minji"
                },
                {
                  serial: "SC-GUEST",
                  imageLabel: "향 캐릭터 이름",
                  mood: "#랜덤 #체험",
                  title: "어코드 표현 문장",
                  user: "@GUEST"
                },
                {
                  serial: "SC-026",
                  imageLabel: "향 캐릭터 이름",
                  mood: "#휴일 #산책",
                  title: "어코드 표현 문장",
                  user: "@yuna"
                },
                {
                  serial: "SC-041",
                  imageLabel: "향 캐릭터 이름",
                  mood: "#집중 #야간",
                  title: "어코드 표현 문장",
                  user: "@junseo"
                },

              ].map((card, idx) => (
                <article
                  key={idx}
                  className="snap-start shrink-0 w-[240px] rounded-2xl bg-white border border-[#EAD7A1] shadow-[0_6px_18px_rgba(140,106,29,0.12)]"
                >
                  <div className="relative m-3 rounded-xl overflow-hidden aspect-[4/5] bg-gradient-to-br from-[#FFF0C7] via-[#F6D88C] to-[#D7B05E]">
                    <div className="absolute inset-0 bg-black/10" />
                    <div className="absolute top-3 left-3 right-3 flex items-center justify-between text-[10px] font-semibold text-[#8C6A1D]">
                      <span className="px-2 py-1 rounded-full bg-white/85">SCENTENCE CARD</span>
                      {/* serial: 카드드생성번호 */}
                      <span className="px-2 py-1 rounded-full bg-white/85">{card.serial}</span>
                    </div>
                    <div className="absolute inset-0">
                      <div className="absolute -top-6 -right-4 w-24 h-24 rounded-full bg-white/25 blur-[2px]" />
                      <div className="absolute bottom-6 left-3 w-16 h-16 rounded-full bg-white/25 blur-[1px]" />
                      <div className="absolute bottom-16 right-6 w-10 h-10 rounded-full bg-white/35" />
                    </div>
                    <div className="absolute bottom-4 left-4 right-4 text-white">
                      {/* imageLabel: 카드 이미지 라벨=향 캐릭터 이름 */}
                      <p className="text-base font-bold leading-snug">{card.imageLabel}</p>
                      {/* mood: 카드 무드=향 캐릭터 무드 */}
                      <p className="text-[11px] opacity-90 mt-1">{card.mood}</p>
                    </div>
                  </div>

                  <div className="px-4 pb-4 space-y-3">
                    <div>
                      {/* title: 카드 제목=대표 어코드 표현 문장 */}
                      <p className="text-sm font-bold text-[#2B2B2B]">“{card.title}”</p>
                    </div>

                    <div className="flex items-center gap-2">
                      <div className="w-6 h-6 rounded-full bg-[#F1E3C2] text-[#8C6A1D] text-[10px] font-bold flex items-center justify-center">
                        {card.user[1]}
                      </div>
                      <div className="text-xs">
                        {/* handle: 카드 생성자 닉네임 */}
                        <p className="text-[#777]">{card.user}</p>
                      </div>
                    </div>

                  </div>
                </article>
              ))}
            </div>

            <button
              onClick={handleCreateScentCard}
              className="w-full py-3 rounded-xl bg-[#C8A24D] text-white font-bold shadow-[0_6px_16px_rgba(200,162,77,0.35)] hover:bg-[#B89138] transition"
            >
              나도 향수 카드 만들러가기
            </button>
          </section>
        </div>

      </main>

    </div>
  );
}

// 자동 스크롤 기능 컴포넌트 (그대로 유지)
function AutoScrollScript() {
  useEffect(() => {
    const carousel = document.getElementById('hero-carousel');
    if (!carousel) return;

    let interval: NodeJS.Timeout; // https://developers.kakao.com/docs/latest/ko/getting-started/app#test-app
    const startAutoScroll = () => {
      interval = setInterval(() => {
        const nextScroll = carousel.scrollLeft + carousel.clientWidth;
        if (nextScroll >= carousel.scrollWidth) {
          carousel.scrollTo({ left: 0, behavior: 'smooth' });
        } else {
          carousel.scrollTo({ left: nextScroll, behavior: 'smooth' });
        }
      }, 4000);
    };

    const stopAutoScroll = () => clearInterval(interval);

    carousel.addEventListener('touchstart', stopAutoScroll);
    carousel.addEventListener('touchend', startAutoScroll);
    carousel.addEventListener('mouseenter', stopAutoScroll);
    carousel.addEventListener('mouseleave', startAutoScroll);

    startAutoScroll();

    return () => {
      stopAutoScroll();
      carousel.removeEventListener('touchstart', stopAutoScroll);
      carousel.removeEventListener('touchend', startAutoScroll);
      carousel.removeEventListener('mouseenter', stopAutoScroll);
      carousel.removeEventListener('mouseleave', startAutoScroll);
    };
  }, []);

  return null;
}