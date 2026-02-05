"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import Sidebar from "@/components/Chat/Sidebar"; // 경로 수정: app/_backups에서는 @/components로 접근해야 빌드가 깨지지 않음
import Link from "next/link";

export default function LandingPage() {
  const router = useRouter();
  const [isSidebarOpen, setIsSidebarOpen] = useState(false); // 사이드바 상태 (랜딩에서는 기본 닫힘)
  const [loading, setLoading] = useState(false);
  const [heroLoaded, setHeroLoaded] = useState(false); // 애니메이션 트리거용

  // 1. 초기 렌더링 시에는 애니메이션 시작 전이라도 일단 true로 두지 않고,
  //    Drop 애니메이션이 끝난 후 true로 변경하여 이미지가 나타나게 함.
  //    (단, 빠른 개발 확인을 위해 자동 타임아웃도 고려 가능)

  const handleNewChat = () => {
    // 메인에서 새 대화 -> 채팅 페이지로 이동
    setLoading(true);
    router.push("/chat");
  };

  return (
    <div className="flex h-screen bg-[#FAF8F5] overflow-hidden text-[#393939] relative">
      <Sidebar
        isOpen={isSidebarOpen}
        onToggle={() => setIsSidebarOpen(!isSidebarOpen)}
        onNewChat={handleNewChat}
        loading={loading}
        showToggleButton={false} // 메인에서는 고정 버튼 숨김 (헤더와 겹침 방지)
      />

      <main className="flex-1 flex flex-col relative w-full h-full overflow-y-auto no-scrollbar">
        {/* 모바일 뒷배경 (사이드바 열렸을 때) */}
        {isSidebarOpen && (
          <div className="fixed inset-0 bg-black/20 z-40 md:hidden" onClick={() => setIsSidebarOpen(false)} />
        )}

        {/* 2. HEADER: SCENTENCE 로고 (좌측) + 햄버거 버튼 (우측) */}
        <header className="absolute top-0 left-0 right-0 z-30 flex items-center justify-between px-6 py-6">
          {/* 좌측 로고 */}
          <h1 className={`text-xl font-bold tracking-widest text-[#111] drop-shadow-md transition-opacity duration-1000 ${heroLoaded ? 'opacity-100' : 'opacity-0'}`}> {/* [Mobile Polish] 로고 색상 진하게 (#393939 -> #111), 그림자 추가 */}
            SCENTENCE
          </h1>

          {/* 우측 햄버거 버튼 */}
          <button onClick={() => setIsSidebarOpen(true)} className="p-2">
            <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" className="w-8 h-8 text-[#111] drop-shadow-sm"> {/* [Mobile Polish] 버튼 색상 진하게, 그림자 추가 */}
              <path strokeLinecap="round" strokeLinejoin="round" d="M3.75 6.75h16.5M3.75 12h16.5m-16.5 5.25h16.5" />
            </svg>
          </button>
        </header>

        {/* 3. HERO SECTION (Fluid Smoke & Input) */}
        <section className="relative w-full h-[85vh] flex flex-col items-center justify-center px-6 overflow-hidden">

          {/* A. Liquid Drop Animation (CSS-only) */}
          {/* heroLoaded가 false일 때만 Drop 애니메이션 렌더링 */}
          {!heroLoaded && (
            <div className="absolute inset-0 flex items-center justify-center z-20 pointer-events-none">
              <div className="w-3 h-3 bg-[#d8b4fe] rounded-full drop-anim"
                onAnimationEnd={() => setHeroLoaded(true)}
              />
              <style jsx>{`
                 .drop-anim {
                   animation: drop 1.8s cubic-bezier(0.5, 0, 0.5, 1) forwards;
                 }
                 @keyframes drop {
                   0% { transform: translateY(-50vh) scale(1); opacity: 0; }
                   20% { opacity: 1; }
                   80% { transform: translateY(0) scale(1.2); opacity: 1; }
                   100% { transform: translateY(10px) scale(0); opacity: 0; }
                 }
               `}</style>
            </div>
          )}

          {/* B. 배경 이미지 (Nanobanana Generated) */}
          <div className={`absolute inset-0 z-0 transition-all duration-[3000ms] ease-out ${heroLoaded ? 'opacity-100 scale-100 blur-0' : 'opacity-0 scale-110 blur-sm'}`}>
            {/* 이미지 파일이 없으면 그라데이션이 대신 보여짐 */}
            <div className="absolute inset-0 bg-gradient-to-b from-[#e0c3fc] to-[#8ec5fc] opacity-10 mix-blend-multiply transition-opacity" />
            <img
              src="/hero_smoke.png"
              alt="Scentenc Fluid Smoke"
              className="w-full h-full object-cover opacity-80 mix-blend-multiply"
            />
          </div>

          {/* 텍스트 & 입력창 컨테이너 (Reverse Reveal 후 등장) */}
          <div className="z-10 w-full max-w-md space-y-8 text-center mt-12">

            {/* 메인 카피 */}
            <div className={`transition-all duration-[1500ms] delay-500 transform ${heroLoaded ? 'translate-y-0 opacity-100' : 'translate-y-10 opacity-0'}`}>
              <h2 className="text-2xl md:text-5xl font-medium text-[#111] mb-2 drop-shadow-sm" style={{ fontFamily: 'serif' }}> {/* [Mobile Polish] 폰트 사이즈 축소 (3xl -> 2xl), 색상 진하게 (#393939 -> #111), 그림자 추가 */}
                Your Scent, <br /> Your Sentence.
              </h2>
              <p className="text-xs md:text-sm text-[#333] tracking-wide font-medium drop-shadow-[0_1px_1px_rgba(255,255,255,0.8)]"> {/* [Mobile Polish] 서브텍스트 진하게, 흰색 그림자로 가독성 확보 */}
                당신만의 분위기를 찾아드리는 AI 퍼퓸 큐레이터
              </p>
            </div>

            {/* 검색 입력창 (Hero 중앙) */}
            <div className={`relative transition-all duration-[1500ms] delay-1000 transform ${heroLoaded ? 'translate-y-0 opacity-100' : 'translate-y-10 opacity-0'}`}>
              <input
                type="text"
                placeholder="어떤 향기를 찾고 계신가요?"
                className="w-full bg-white/60 backdrop-blur-md border border-white/50 rounded-full py-4 px-6 text-center text-[#393939] placeholder:text-[#8E8E8E] shadow-lg outline-none focus:ring-2 focus:ring-purple-300/50 transition-all"
                onKeyDown={(e) => {
                  if (e.key === 'Enter') handleNewChat();
                }}
              />
              <button onClick={handleNewChat} className="absolute right-3 top-1/2 -translate-y-1/2 p-2 bg-[#393939] rounded-full text-white hover:bg-black transition-colors">
                <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" className="w-4 h-4">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M13.5 4.5 21 12m0 0-7.5 7.5M21 12H3" />
                </svg>
              </button>
            </div>

          </div>
        </section>

        {/* 4. SCENTENCE PICK (가로 스크롤) - Real Data */}
        <section className="py-6 md:py-10 px-6 space-y-4 md:space-y-6 bg-white rounded-t-[2rem] md:rounded-t-[3rem] shadow-[0_-10px_40px_rgba(0,0,0,0.05)] -mt-10 relative z-20"> {/* [Mobile Polish] 여백 축소 (py-10 -> py-6), 둥근 모서리 조정 */}
          <div className="flex justify-between items-end">
            <h3 className="text-lg md:text-xl font-bold text-[#111] tracking-tight">SCENTENCE PICK</h3> {/* [Mobile Polish] 폰트 사이즈 최적화 (text-xl -> text-lg), 색상 진하게 */}
            <span className="text-xs text-[#8E8E8E] underline cursor-pointer">전체보기</span>
          </div>

          {/* 카드 리스트 */}
          <div className="flex gap-4 overflow-x-auto no-scrollbar pb-6 snap-x">
            {[
              { file: "Angels Share Paradis By Kilian (unisex).png", name: "Angels' Share", brand: "By Kilian", type: "Unisex" },
              { file: "Angham Lattafa Perfumes (unisex).png", name: "Angham", brand: "Lattafa Perfumes", type: "Unisex" },
              { file: "BaldAfrique Absolu Byredo (unisex).png", name: "Bal d'Afrique Absolu", brand: "Byredo", type: "Unisex" },
              { file: "Fleur de Peau Eau de Toilette Diptyque (unisex).png", name: "Fleur de Peau", brand: "Diptyque", type: "Unisex" },
              { file: "Guidance 46 Amouage (unisex).png", name: "Guidance 46", brand: "Amouage", type: "Unisex" },
              { file: "Shalimar_L_Essence Guerlain (female).png", name: "Shalimar L'Essence", brand: "Guerlain", type: "Female" },
              { file: "Tilia Marc-Antoine Barrois (unisex).png", name: "Tilia", brand: "Marc-Antoine Barrois", type: "Unisex" },
              { file: "Valaya Exclusif Parfums de Marly (female).png", name: "Valaya Exclusif", brand: "Parfums de Marly", type: "Female" },
              { file: "Yum Boujee Marshmallow_81 Kayali Fragrances (female).png", name: "Yum Boujee Marshmallow", brand: "Kayali", type: "Female" }
            ].map((item, idx) => (
              <div key={idx} className="snap-center shrink-0 w-36 md:w-40 flex flex-col gap-3 group cursor-pointer"> {/* [Mobile Polish] 카드 너비 조정 (w-40 -> w-36) */}
                {/* 이미지 영역 */}
                <div className="w-full h-48 md:h-52 bg-[#F2F1EE] rounded-2xl overflow-hidden relative shadow-sm group-hover:shadow-md transition-shadow">
                  <img
                    src={`/perfumes/${item.file}`}
                    alt={item.name}
                    className="w-full h-full object-cover transform group-hover:scale-105 transition-transform duration-500"
                  />
                  {/* 타입 배지 */}
                  <div className="absolute top-2 right-2 bg-white/80 backdrop-blur-sm px-2 py-0.5 rounded-full text-[10px] uppercase font-medium text-[#555]">
                    {item.type}
                  </div>
                </div>
                {/* 정보 영역 */}
                <div className="text-center">
                  <h4 className="text-sm font-bold text-[#222] truncate leading-tight">{item.name}</h4> {/* [Mobile Polish] 텍스트 색상 진하게 */}
                  <p className="text-[10px] md:text-xs text-[#666] mt-0.5 truncate">{item.brand}</p>
                </div>
              </div>
            ))}
          </div>
        </section>

        <section className="h-24" /> {/* Bottom Nav 공간 확보 */}

      </main>

      {/* 5. BOTTOM NAVIGATION (Fixed) */}
      <nav className="fixed bottom-0 left-0 right-0 bg-white/90 backdrop-blur-lg border-t border-[#E5E4DE] px-8 py-4 flex justify-between items-center z-50 text-[10px] font-medium text-[#8E8E8E]">
        <button className="flex flex-col items-center gap-1 text-[#393939]">
          <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" className="w-6 h-6"><path strokeLinecap="round" strokeLinejoin="round" d="m2.25 12 8.954-8.955c.44-.439 1.152-.439 1.591 0L21.75 12M4.5 9.75v10.125c0 .621.504 1.125 1.125 1.125H9.75v-4.875c0-.621.504-1.125 1.125-1.125h2.25c.621 0 1.125.504 1.125 1.125V21h4.125c.621 0 1.125-.504 1.125-1.125V9.75M8.25 21h8.25" /></svg>
          홈
        </button>
        <button className="flex flex-col items-center gap-1 hover:text-[#393939] transition-colors">
          <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" className="w-6 h-6"><path strokeLinecap="round" strokeLinejoin="round" d="m21 21-5.197-5.197m0 0A7.5 7.5 0 1 0 5.196 5.196a7.5 7.5 0 0 0 10.607 10.607Z" /></svg>
          검색
        </button>
        <button onClick={() => router.push("/chat")} className="flex flex-col items-center gap-1 hover:text-[#393939] transition-colors relative">
          <div className="absolute -top-8 bg-[#393939] rounded-full p-3 shadow-lg border-4 border-[#FAF8F5]">
            <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" className="w-6 h-6 text-white"><path strokeLinecap="round" strokeLinejoin="round" d="M8.625 12a.375.375 0 1 1-.75 0 .375.375 0 0 1 .75 0Zm0 0H8.25m4.125 0a.375.375 0 1 1-.75 0 .375.375 0 0 1 .75 0Zm0 0H12m4.125 0a.375.375 0 1 1-.75 0 .375.375 0 0 1 .75 0Zm0 0h-.375M21 12c0 4.556-4.03 8.25-9 8.25a9.764 9.764 0 0 1-2.555-.337A5.972 5.972 0 0 1 5.41 20.97a5.969 5.969 0 0 1-.474-.065 4.48 4.48 0 0 0 .978-2.025c.09-.457-.133-.901-.467-1.226C3.93 16.178 3 14.189 3 12c0-4.556 4.03-8.25 9-8.25s9 3.694 9 8.25Z" /></svg>
          </div>
          <span className="mt-6">챗봇</span>
        </button>
        <button className="flex flex-col items-center gap-1 hover:text-[#393939] transition-colors">
          <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" className="w-6 h-6"><path strokeLinecap="round" strokeLinejoin="round" d="M15.75 6a3.75 3.75 0 1 1-7.5 0 3.75 3.75 0 0 1 7.5 0ZM4.501 20.118a7.5 7.5 0 0 1 14.998 0A17.933 17.933 0 0 1 12 21.75c-2.676 0-5.216-.584-7.499-1.632Z" /></svg>
          프로필
        </button>
      </nav>
    </div>
  );
}
