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
import { motion, AnimatePresence } from "framer-motion";

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
    const [searchQuery, setSearchQuery] = useState("");

    useEffect(() => {
        setIsMounted(true);
    }, []);

    // localAuth 제거: 아카이브는 세션 id만 사용


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
        // localAuth 제거: 세션에서만 memberId 설정
        if (session?.user?.id) {
            setMemberId(Number(session.user.id));
        }
    }, [session]);



    const displayName = session?.user?.name || session?.user?.email?.split('@')[0] || "Guest";
    const isLoggedIn = Boolean(session);

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
        // 1. 탭 필터링
        let matchesTab = true;
        if (activeTab === 'ALL') matchesTab = item.register_status !== 'HAD';
        else if (activeTab === 'HAVE') matchesTab = item.register_status === 'HAVE';
        else if (activeTab === 'HAD') matchesTab = item.register_status === 'HAD';
        else if (activeTab === 'WISH') matchesTab = item.register_status === 'RECOMMENDED';

        if (!matchesTab) return false;

        // 2. 검색 필터링
        if (searchQuery.trim()) {
            const query = searchQuery.toLowerCase();
            const nameMatch =
                item.name_kr?.toLowerCase().includes(query) ||
                item.name_en?.toLowerCase().includes(query) ||
                item.name?.toLowerCase().includes(query);
            const brandMatch =
                item.brand_kr?.toLowerCase().includes(query) ||
                item.brand?.toLowerCase().includes(query);
            return nameMatch || brandMatch;
        }

        return true;
    });

    if (!isMounted) return null; // [추가] 마운트 전에는 구조를 렌더링하지 않아 서버-클라이언트 불일치 방지

    return (
        <SavedPerfumesProvider memberId={memberId}>
            <PageLayout className="min-h-screen bg-[#FDFBF8] text-black font-sans overflow-x-hidden relative">
                {/* Background Aura Blobs */}
                <div className="fixed inset-0 pointer-events-none overflow-hidden z-0">
                    <motion.div
                        animate={{
                            x: [0, 80, 0],
                            y: [0, 40, 0],
                            scale: [1, 1.1, 1],
                        }}
                        transition={{ duration: 20, repeat: Infinity, ease: "linear" }}
                        className="absolute -top-[5%] -right-[5%] w-[40%] h-[40%] bg-[#D4E6F1]/20 rounded-full blur-[100px]"
                    />
                    <motion.div
                        animate={{
                            x: [0, -60, 0],
                            y: [0, 80, 0],
                            scale: [1, 1.2, 1],
                        }}
                        transition={{ duration: 25, repeat: Infinity, ease: "linear" }}
                        className="absolute bottom-[10%] -left-[10%] w-[50%] h-[50%] bg-[#FADBD8]/20 rounded-full blur-[100px]"
                    />
                </div>

                {/* Main Content */}
                <main className="relative z-10 pt-[60px] md:pt-[140px] pb-32 px-4 md:px-10 max-w-7xl mx-auto min-h-screen">

                    {/* Header: Title & Description */}
                    <div className="mb-6 md:mb-10 text-center md:text-left">
                        <motion.h1
                            initial={{ opacity: 0, x: -20 }}
                            animate={{ opacity: 1, x: 0 }}
                            className="text-4xl md:text-6xl font-black tracking-tighter text-black uppercase mb-2"
                        >
                            MY Gallery
                        </motion.h1>
                        <motion.p
                            initial={{ opacity: 0 }}
                            animate={{ opacity: 1 }}
                            transition={{ delay: 0.3 }}
                            className="text-xs md:text-sm text-gray-400 font-bold uppercase tracking-[0.2em]"
                        >
                            나만의 향수 보관함
                        </motion.p>
                    </div>

                    {/* Stats & Toolbar Container */}
                    <div className="flex flex-col gap-6 mb-8 md:mb-12">
                        {/* 1. Integrated Stats Bar */}
                        <motion.div
                            initial={{ opacity: 0, y: 20 }}
                            animate={{ opacity: 1, y: 0 }}
                            className="flex flex-wrap items-center justify-center md:justify-start gap-3 md:gap-4 bg-white/40 backdrop-blur-md border border-white/60 p-3 md:p-3 rounded-[32px] shadow-sm"
                        >
                            <StatItem
                                label="Total"
                                count={stats.have + stats.wish}
                                isActive={activeTab === 'ALL'}
                                onClick={() => setActiveTab('ALL')}
                            />
                            <div className="w-px h-8 bg-gray-200/50 hidden sm:block" />
                            <StatItem
                                label="Have"
                                count={stats.have}
                                activeColor="text-indigo-500"
                                isActive={activeTab === 'HAVE'}
                                onClick={() => setActiveTab('HAVE')}
                            />
                            <div className="w-px h-8 bg-gray-200/50 hidden sm:block" />
                            <StatItem
                                label="Wish"
                                count={stats.wish}
                                activeColor="text-rose-400"
                                isActive={activeTab === 'WISH'}
                                onClick={() => setActiveTab('WISH')}
                            />

                            {/* [Quick Search] 오른쪽 여백을 채우는 검색 바 */}
                            <div className="flex-1 min-w-[200px] w-full md:w-auto md:ml-8 relative group">
                                <div className="absolute left-4 top-1/2 -translate-y-1/2 text-gray-300 group-focus-within:text-black transition-colors">
                                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2.5" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"></path></svg>
                                </div>
                                <input
                                    type="text"
                                    value={searchQuery}
                                    onChange={(e) => setSearchQuery(e.target.value)}
                                    placeholder="SEARCH YOUR SCENTS..."
                                    className="w-full bg-white/50 border border-transparent focus:border-black/10 focus:bg-white rounded-2xl py-3 pl-12 pr-4 text-[11px] font-black uppercase tracking-widest placeholder:text-gray-300 outline-none transition-all shadow-inner"
                                />
                                {searchQuery && (
                                    <button
                                        onClick={() => setSearchQuery("")}
                                        className="absolute right-4 top-1/2 -translate-y-1/2 text-gray-300 hover:text-black"
                                    >
                                        <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="3" d="M6 18L18 6M6 6l12 12"></path></svg>
                                    </button>
                                )}
                            </div>
                        </motion.div>

                        {/* 2. Action Toolbar */}
                        <div className="flex flex-col md:flex-row items-center justify-between gap-4 md:gap-6">
                            {/* View & Language Controls (Left Group) */}
                            <div className="flex items-center gap-3 w-full md:w-auto">
                                {/* View Switcher (Segmented Control) */}
                                <div className="relative flex p-1 bg-gray-100 rounded-full w-full md:w-[240px]">
                                    <div
                                        className="absolute top-1 bottom-1 bg-white rounded-full shadow-sm transition-all duration-300 ease-out"
                                        style={{
                                            left: viewMode === 'GRID' ? '4px' : '50%',
                                            width: 'calc(50% - 4px)'
                                        }}
                                    />
                                    <button
                                        onClick={() => setViewMode('GRID')}
                                        className={`relative z-10 flex-1 py-2 text-[10px] font-black uppercase tracking-widest transition-colors ${viewMode === 'GRID' ? 'text-black' : 'text-gray-400'}`}
                                    >
                                        GRID
                                    </button>
                                    <button
                                        onClick={() => setViewMode('GLOBE')}
                                        className={`relative z-10 flex-1 py-2 text-[10px] font-black uppercase tracking-widest transition-colors ${viewMode === 'GLOBE' ? 'text-black' : 'text-gray-400'}`}
                                    >
                                        GALAXY
                                    </button>
                                </div>

                                {/* Language Toggle */}
                                <button
                                    onClick={() => setIsKorean(!isKorean)}
                                    className="px-5 py-2.5 rounded-full border border-gray-200 bg-white hover:border-black text-[10px] font-black uppercase tracking-widest transition-all shadow-sm"
                                >
                                    {isKorean ? "KR" : "EN"}
                                </button>
                            </div>

                            {/* Action Buttons (Right Group) */}
                            <div className="flex items-center gap-3 w-full md:w-auto">
                                <div className="relative">
                                    <button
                                        onClick={() => setIsHistoryOpen(!isHistoryOpen)}
                                        className={`flex items-center gap-2 px-5 py-3 rounded-full border border-gray-100 bg-white/50 backdrop-blur-sm transition-all hover:border-gray-200 ${isHistoryOpen ? 'ring-2 ring-black bg-white shadow-md' : 'shadow-sm'}`}
                                    >
                                        <svg className="w-4 h-4 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg>
                                        <span className="text-[10px] font-black uppercase tracking-widest text-gray-500">History</span>
                                        <span className="text-xs font-black text-black ml-1">{stats.had}</span>
                                    </button>
                                    <AnimatePresence>
                                        {isHistoryOpen && (
                                            <HistoryModal
                                                historyItems={collection.filter(p => p.register_status === 'HAD')}
                                                onClose={() => setIsHistoryOpen(false)}
                                                onSelect={setSelectedPerfume}
                                            />
                                        )}
                                    </AnimatePresence>
                                </div>
                                <motion.button
                                    whileHover={{ scale: 1.02 }}
                                    whileTap={{ scale: 0.98 }}
                                    onClick={() => setIsSearchOpen(true)}
                                    className="flex-1 md:flex-none flex items-center justify-center gap-2 md:gap-3 px-6 py-2.5 md:px-8 md:py-3 bg-black text-white rounded-full text-[9px] md:text-[10px] font-black uppercase tracking-[0.1em] md:tracking-[0.2em] shadow-lg shadow-black/10"
                                >
                                    <span>Add Scent</span>
                                    <svg className="w-3 h-3 md:w-4 md:h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="3" d="M12 6v6m0 0v6m0-6h6m-6 0H6"></path></svg>
                                </motion.button>
                            </div>
                        </div>
                    </div>

                    {/* Content Section */}
                    <AnimatePresence mode="wait">
                        {viewMode === 'GLOBE' ? (
                            <motion.div
                                key="globe"
                                initial={{ opacity: 0, scale: 0.98 }}
                                animate={{ opacity: 1, scale: 1 }}
                                exit={{ opacity: 0, scale: 1.02 }}
                                className="animate-fade-in"
                            >
                                <ArchiveGlobeView collection={filteredCollection} isKorean={isKorean} />
                            </motion.div>
                        ) : (
                            <motion.div
                                key="grid"
                                initial={{ opacity: 0, y: 20 }}
                                animate={{ opacity: 1, y: 0 }}
                                exit={{ opacity: 0, y: -20 }}
                            >
                                {filteredCollection.length === 0 ? (
                                    <div className="flex flex-col items-center justify-center py-32 bg-white/30 backdrop-blur-sm rounded-[40px] border border-white/50">
                                        <p className="text-gray-400 font-bold uppercase tracking-widest mb-6">No scents found</p>
                                        <button
                                            onClick={() => setIsSearchOpen(true)}
                                            className="text-black font-black text-xs uppercase tracking-widest hover:underline decoration-2 underline-offset-8"
                                        >
                                            + Add Your First Perfume
                                        </button>
                                    </div>
                                ) : (
                                    <section className="grid grid-cols-3 sm:grid-cols-4 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6 gap-2 md:gap-8">
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
                            </motion.div>
                        )}
                    </AnimatePresence>
                </main>

                <Link href="/perfume-network/nmap" className="fixed bottom-6 right-6 md:bottom-8 md:right-8 z-40 group">
                    <motion.div
                        whileHover={{ scale: 1.05 }}
                        whileTap={{ scale: 0.95 }}
                        className="flex items-center gap-2 md:gap-3 px-4 py-2.5 md:px-8 md:py-4 bg-white/80 backdrop-blur-md border border-white/50 text-black rounded-full shadow-2xl shadow-black/5 font-black text-[8px] md:text-xs uppercase tracking-widest"
                    >
                        <div className="w-1.5 h-1.5 md:w-2 md:h-2 rounded-full bg-black animate-pulse" />
                        <span>Scent Map</span>
                    </motion.div>
                </Link>

                {isSearchOpen && (
                    <PerfumeSearchModal
                        memberId={String(memberId)}
                        onClose={() => setIsSearchOpen(false)}
                        onAdd={handleAdd}
                        isKorean={isKorean}
                        onToggleLanguage={() => setIsKorean(!isKorean)}
                        existingIds={collection.map(p => p.perfume_id)}
                    />
                )}
                {selectedPerfume && (
                    <PerfumeDetailModal
                        perfume={selectedPerfume}
                        onClose={() => setSelectedPerfume(null)}
                        onUpdateStatus={handleUpdateStatus}
                        onDelete={handleDelete}
                        onUpdatePreference={handleUpdatePreference}
                        isKorean={isKorean}
                    />
                )}
            </PageLayout>
        </SavedPerfumesProvider>
    );
}

function StatItem({
    label,
    count,
    activeColor = "text-black",
    isActive,
    onClick
}: {
    label: string;
    count: number;
    activeColor?: string;
    isActive: boolean;
    onClick: () => void
}) {
    return (
        <button
            onClick={onClick}
            className={`
                flex flex-col items-center min-w-[80px] md:min-w-[100px] px-4 py-3 rounded-[24px] transition-all duration-300
                ${isActive ? 'bg-white shadow-sm ring-1 ring-black/5' : 'hover:bg-white/40'}
            `}
        >
            <span className={`text-[10px] font-black uppercase tracking-widest mb-1 transition-colors ${isActive ? 'text-black' : 'text-gray-400'}`}>
                {label}
            </span>
            <span className={`text-2xl font-black transition-all ${isActive ? activeColor : 'text-gray-300'}`}>
                {count}
            </span>
        </button>
    );
}
