/* page.tsx (3-State Tabs: All / HAVE / HAD / WISH) */
"use client";

import { useState, useEffect } from "react";
import { useSession } from "next-auth/react"; // 카카오 로그인 세션
import Link from "next/link";
import ArchiveSidebar from "@/components/archives/ArchiveSidebar";
import CabinetShelf from "@/components/archives/CabinetShelf";
import PerfumeSearchModal from "@/components/archives/PerfumeSearchModal";
import PerfumeDetailModal from "@/components/archives/PerfumeDetailModal";
import HistoryModal from '@/components/archives/HistoryModal';
import ArchiveGlobeView from "@/components/archives/ArchiveGlobeView";
import PageLayout from "@/components/common/PageLayout";
import { SavedPerfumesProvider } from "@/contexts/SavedPerfumesContext";

const API_URL = "/api";
// const MEMBER_ID = 1;

interface MyPerfume {
    my_perfume_id: number;
    perfume_id: number;
    name: string;
    name_en?: string; // 추가
    name_kr?: string; // 추가
    brand: string;
    brand_kr?: string; // 추가
    image_url: string | null;
    register_status: string; // HAVE, HAD, RECOMMENDED
    preference?: string;
    // 프론트 UI용 status 매핑
    status: string;
}

type TabType = 'ALL' | 'HAVE' | 'HAD' | 'WISH';

export default function ArchivesPage() {
    const { data: session } = useSession(); // 카카오 로그인 세션
    const [collection, setCollection] = useState<MyPerfume[]>([]);
    const [selectedPerfume, setSelectedPerfume] = useState<MyPerfume | null>(null);
    const [activeTab, setActiveTab] = useState<TabType>('ALL');
    const [isSidebarOpen, setIsSidebarOpen] = useState(false);
    const [isSearchOpen, setIsSearchOpen] = useState(false);
    const [isKorean, setIsKorean] = useState(true);
    const [isHistoryOpen, setIsHistoryOpen] = useState(false);
    const [memberId, setMemberId] = useState<number>(0);
    const [viewMode, setViewMode] = useState<'GRID' | 'GLOBE'>('GRID');
    const [isMounted, setIsMounted] = useState(false);

    useEffect(() => {
        setIsMounted(true);
    }, []);

    // [Profile Logic] 메인/채팅 페이지와 동일하게 이식
    const [localUser, setLocalUser] = useState<{ memberId?: string | null; email?: string | null; nickname?: string | null; roleType?: string | null; isAdmin?: boolean } | null>(null);


    const fetchPerfumes = async () => {
        if (memberId === 0) return;
        try {
            const res = await fetch(`${API_URL}/users/${memberId}/perfumes`);
            if (res.ok) {
                const data = await res.json();
                const mapped = data.map((item: any) => ({
                    my_perfume_id: item.perfume_id,
                    perfume_id: item.perfume_id,
                    name: item.perfume_name, // Fallback for legacy components
                    name_en: item.name_en || item.perfume_name,
                    name_kr: item.name_kr || item.perfume_name,
                    brand: item.brand || "Unknown",
                    brand_kr: item.brand_kr || item.brand, // 추가
                    image_url: item.image_url || null,
                    register_status: item.register_status,
                    register_dt: item.register_dt,
                    preference: item.preference,
                    status: item.register_status
                }));
                setCollection(mapped);
            }
        } catch (e) {
            console.error("Failed to fetch perfumes", e);
        }
    };

    useEffect(() => {
        if (typeof window === "undefined") return;
        const stored = localStorage.getItem("localAuth");
        if (stored) {
            try {
                const parsed = JSON.parse(stored);
                setLocalUser(parsed);
                if (parsed.memberId) setMemberId(Number(parsed.memberId));
            } catch (error) {
                setLocalUser(null);
            }
        }
    }, []);

    useEffect(() => {
        if (session?.user?.id) {
            setMemberId(Number(session.user.id));
        }
    }, [session]);

    // if (typeof window === "undefined") return; // <- [삭제] Hydration Mismatch의 주범

    // [기존 코드 주석 처리]
    // const apiBaseUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";



    const displayName = session?.user?.name || localUser?.nickname || localUser?.email?.split('@')[0] || "Guest";
    const isLoggedIn = Boolean(session || localUser);

    // 2. memberId가 설정되면 데이터 로드
    useEffect(() => {
        if (memberId > 0) {
            fetchPerfumes();
        }
    }, [memberId]);

    const handleAdd = async (perfume: any, status: string) => {
        if (memberId === 0) return;
        try {
            const payload = {
                perfume_id: perfume.perfume_id,
                perfume_name: perfume.name,
                register_status: status,
                register_reason: "USER",
                preference: "NEUTRAL"
            };
            await fetch(`${API_URL}/users/${memberId}/perfumes`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(payload)
            });
            fetchPerfumes();
            // setIsSearchOpen(false); <-모달 자동닫기
        } catch (e) { console.error("Add failed", e); }
    };

    const handleUpdateStatus = async (id: number, status: string) => {
        if (memberId === 0) return;
        try {
            await fetch(`${API_URL}/users/${memberId}/perfumes/${id}`, {
                method: "PATCH",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ register_status: status })
            });
            fetchPerfumes();
            if (selectedPerfume && selectedPerfume.my_perfume_id === id) {
                setSelectedPerfume({ ...selectedPerfume, register_status: status, status: status });
            }
        } catch (e) { console.error("Update failed", e); }
    };

    const handleDelete = async (id: number, rating?: number) => {
        if (memberId === 0) return;
        try {
            if (rating !== undefined) {
                let pref = "NEUTRAL";
                if (rating === 3) pref = "GOOD";
                if (rating === 1) pref = "BAD";

                await fetch(`${API_URL}/users/${memberId}/perfumes/${id}`, {
                    method: "PATCH",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ register_status: "HAD", preference: pref })
                });
            } else {
                await fetch(`${API_URL}/users/${memberId}/perfumes/${id}`, {
                    method: "DELETE"
                });
            }
            fetchPerfumes();
            setSelectedPerfume(null);
        } catch (e) { console.error("Delete failed", e); }
    };

    const handleUpdatePreference = async (id: number, preference: string) => {
        if (memberId === 0) return;
        try {
            await fetch(`${API_URL}/users/${memberId}/perfumes/${id}`, {
                method: "PATCH",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ register_status: "HAD", preference: preference })
            });
            fetchPerfumes();
            setSelectedPerfume(prev => prev ? { ...prev, register_status: 'HAD', status: 'HAD', preference: preference } : null);
        } catch (e) { console.error("Update preference failed", e); }
    };

    // 통계 계산
    const stats = {
        have: collection.filter(p => p.register_status === 'HAVE').length,
        had: collection.filter(p => p.register_status === 'HAD').length,
        wish: collection.filter(p => p.register_status === 'RECOMMENDED').length
    };

    // 필터링된 목록
    const filteredCollection = collection.filter(item => {
        if (activeTab === 'ALL') return item.register_status !== 'HAD'; // HAD 제외
        if (activeTab === 'HAVE') return item.register_status === 'HAVE';
        if (activeTab === 'HAD') return item.register_status === 'HAD';
        if (activeTab === 'WISH') return item.register_status === 'RECOMMENDED';
        return true;
    });

    if (!isMounted) return null; // [추가] 마운트 전에는 구조를 렌더링하지 않아 서버-클라이언트 불일치 방지

    return (
        <SavedPerfumesProvider memberId={memberId}>
            <PageLayout subTitle="My Gallery" className="min-h-screen bg-[#FDFBF8] text-gray-800 font-sans selection:bg-[#C5A55D] selection:text-white relative">

                {/* Main */}
                <main className="pt-[140px] md:pt-[160px] pb-24 px-4 md:px-10 max-w-7xl mx-auto min-h-[80vh]">

                    {/* Header Section: Title (Left) & Primary Actions (Right) */}
                    <section className="flex flex-col md:flex-row justify-between items-start gap-8 md:gap-0 mb-10 md:mb-14">
                        <div className="animate-fade-in">
                            <h1 className="text-3xl md:text-4xl font-bold text-[#222] mb-2 md:mb-3 tracking-tight">My Sent Gallery</h1>
                            <p className="text-[#888] text-xs md:text-sm font-medium">나만의 향기 컬렉션을 기록해보세요.</p>
                        </div>

                        <div className="flex flex-col items-stretch md:items-end gap-6 w-full md:w-auto">
                            {/* 1. Filter & History Row (Moved to First Row) */}
                            <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-3">
                                {/* Tabs Box */}
                                <div className="flex gap-2 sm:gap-4 bg-white px-2 sm:px-3 py-2 rounded-2xl shadow-sm border border-gray-100 items-center justify-between sm:justify-start">
                                    <TabItem
                                        label="전체 (ALL)"
                                        count={stats.have + stats.wish}
                                        isActive={activeTab === 'ALL'}
                                        onClick={() => setActiveTab('ALL')}
                                    />
                                    <div className="h-6 w-px bg-gray-100"></div>
                                    <TabItem
                                        label="보유 (HAVE)"
                                        count={stats.have}
                                        color="text-indigo-600"
                                        isActive={activeTab === 'HAVE'}
                                        onClick={() => setActiveTab('HAVE')}
                                    />
                                    <div className="h-6 w-px bg-gray-100"></div>
                                    <TabItem
                                        label="위시 (WISH)"
                                        count={stats.wish}
                                        color="text-rose-500"
                                        isActive={activeTab === 'WISH'}
                                        onClick={() => setActiveTab('WISH')}
                                    />
                                </div>

                                {/* History (Matching Tabs Height) */}
                                <div className="relative z-40 h-[64px]">
                                    <button
                                        onClick={() => setIsHistoryOpen(!isHistoryOpen)}
                                        className={`
                                        flex flex-col items-center justify-center gap-1 px-5 h-full rounded-2xl border transition-all shadow-sm
                                        ${isHistoryOpen
                                                ? 'bg-[#2da44e] text-white border-[#2da44e]'
                                                : 'bg-white text-gray-500 border-gray-100 hover:bg-green-50 hover:text-[#2da44e]'}
                                    `}
                                    >
                                        <span className="text-xs font-bold uppercase tracking-tighter">History</span>
                                        <span className={`text-base font-bold ${isHistoryOpen ? 'text-white' : 'text-gray-300'}`}>
                                            {stats.had}
                                        </span>
                                    </button>
                                    {isHistoryOpen && (
                                        <HistoryModal
                                            historyItems={collection.filter(p => p.register_status === 'HAD')}
                                            onClose={() => setIsHistoryOpen(false)}
                                            onSelect={setSelectedPerfume}
                                        />
                                    )}
                                </div>
                            </div>

                            {/* 2. Primary Actions (Moved to Second Row) */}
                            <div className="flex items-center justify-between md:justify-end gap-3">
                                <button
                                    onClick={() => setIsKorean(!isKorean)}
                                    className="px-4 py-2.5 rounded-xl border border-gray-200 text-xs font-bold text-gray-400 bg-white hover:bg-black hover:text-white transition-all shadow-sm"
                                    title={isKorean ? "Switch to English" : "한글로 전환"}
                                >
                                    {isKorean ? "KR" : "EN"}
                                </button>
                                <button
                                    onClick={() => setIsSearchOpen(true)}
                                    className="flex-1 md:flex-none flex items-center justify-center gap-2 px-6 py-2.5 bg-[#C5A55D] text-white rounded-xl hover:bg-[#B09045] transition shadow-lg shadow-[#C5A55D]/20 text-[11px] font-black tracking-widest"
                                >
                                    ＋ ADD PERFUME
                                </button>
                            </div>

                            {/* 3. View Switcher (Bottom Right of Controls) */}
                            <div className="bg-gray-100 p-1 rounded-xl flex gap-1 mt-2 md:mt-0">
                                <button
                                    onClick={() => setViewMode('GRID')}
                                    className={`flex-1 md:flex-none px-4 py-2 rounded-lg text-xs font-bold transition-all ${viewMode === 'GRID' ? 'bg-white text-black shadow-sm' : 'text-gray-400 hover:text-gray-600'}`}
                                >
                                    GALLERY 🏛️
                                </button>
                                <button
                                    onClick={() => setViewMode('GLOBE')}
                                    className={`flex-1 md:flex-none px-4 py-2 rounded-lg text-xs font-bold transition-all ${viewMode === 'GLOBE' ? 'bg-black text-white shadow-sm' : 'text-gray-400 hover:text-gray-600'}`}
                                >
                                    GALAXY 🌌
                                </button>
                            </div>
                        </div>
                    </section>

                    {viewMode === 'GLOBE' ? (
                        <div className="mb-12 animate-fade-in">
                            {/* TO-BE (데이터 주입) */}
                            <ArchiveGlobeView collection={filteredCollection} isKorean={isKorean} />
                        </div>
                    ) : (
                        <>
                            {filteredCollection.length === 0 ? (
                                <div className="flex flex-col items-center justify-center py-20 border border-[#C5A55D]/30 rounded-3xl bg-white/50">
                                    <p className="text-gray-400 font-medium mb-4">해당하는 향수가 없습니다.</p>
                                    <button onClick={() => setIsSearchOpen(true)} className="text-[#C5A55D] font-bold text-sm hover:underline">
                                        + 향수 추가하기
                                    </button>
                                </div>
                            ) : (
                                <section className="grid grid-cols-4 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6 gap-2 md:gap-6 animate-fade-in-up">
                                    {filteredCollection.map((item) => (
                                        <CabinetShelf
                                            key={item.my_perfume_id}
                                            perfume={item}
                                            onSelect={setSelectedPerfume}
                                            isKorean={isKorean}
                                        />
                                    ))}
                                </section>
                            )}
                        </>
                    )}
                </main>

                <Link href="/perfume-network/nmap" className="fixed bottom-6 right-6 md:bottom-10 md:right-10 z-30 shadow-xl rounded-full transition-transform hover:scale-105">
                    <div className="bg-[#C5A55D] text-white px-6 py-3 md:px-8 md:py-4 rounded-full flex items-center gap-3 font-bold text-xs md:text-sm shadow-[#C5A55D]/30 hover:bg-[#B09045] transition-colors">
                        <span>향수 관계 맵</span>
                    </div>
                </Link>

                {
                    isSearchOpen && (
                        <PerfumeSearchModal
                            memberId={String(memberId)}
                            onClose={() => setIsSearchOpen(false)}
                            onAdd={handleAdd}
                            isKorean={isKorean}
                            onToggleLanguage={() => setIsKorean(!isKorean)}
                            existingIds={collection.map(p => p.perfume_id)} // <--- 기존 등록된 ID 목록 전달
                        />
                    )
                }
                {selectedPerfume && <PerfumeDetailModal perfume={selectedPerfume} onClose={() => setSelectedPerfume(null)} onUpdateStatus={handleUpdateStatus} onDelete={handleDelete} onUpdatePreference={handleUpdatePreference} isKorean={isKorean} />}

                {/* NavSidebar Overlay Removed (Handled by PageLayout) */}
            </PageLayout>
        </SavedPerfumesProvider >
    );
}

function TabItem({ label, count, color = "text-[#555]", isActive, onClick }: { label: string; count: number; color?: string; isActive: boolean; onClick: () => void }) {
    return (
        <button
            onClick={onClick}
            className={`
                flex flex-col items-center min-w-[60px] sm:min-w-[70px] px-2 sm:px-3 py-1.5 sm:py-2 rounded-xl transition-all
                ${isActive ? 'bg-gray-50 ring-1 ring-gray-200 shadow-sm' : 'hover:bg-gray-50/50'}
            `}
        >
            <span className={`text-[9px] sm:text-[10px] font-bold uppercase tracking-wide mb-0.5 sm:mb-1 transition-colors ${isActive ? 'text-gray-800' : 'text-gray-400'}`}>{label.split(' ')[0]}</span>
            <span className={`text-lg sm:text-xl font-bold transition-all ${isActive ? color : 'text-gray-300'}`}>{count}</span>
        </button>
    );
}