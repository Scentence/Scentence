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
    const isGalaxy = viewMode === 'GLOBE';
    const t = isKorean
        ? {
            switchToGallery: "갤러리 모드로 전환",
            switchToGalaxy: "갤럭시 모드로 전환",
            total: "총합",
            have: "보유",
            wish: "위시",
            searchPlaceholder: "향수를 검색해보세요...",
            history: "히스토리",
            addScent: "향수 추가",
            noScents: "검색 결과가 없어요",
            addFirst: "+ 첫 향수 추가하기",
            scentMap: "향수 지도",
        }
        : {
            switchToGallery: "Switch to Gallery mode",
            switchToGalaxy: "Switch to Galaxy mode",
            total: "TOTAL",
            have: "HAVE",
            wish: "WISH",
            searchPlaceholder: "SEARCH YOUR SCENTS...",
            history: "HISTORY",
            addScent: "ADD SCENT",
            noScents: "No scents found",
            addFirst: "+ Add Your First Perfume",
            scentMap: "Scent Map",
        };
    const modeLabel = isGalaxy ? "GALAXY" : "GALLERY";
    const modeLabelSlotClass = "w-[7.8ch] md:w-[8.4ch]";
    const modeLabelTextClass = "tracking-[-0.015em]";
    const archiveSubtitleFixed = "나만의 향수 보관함";

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
            <PageLayout
                className={`min-h-screen font-sans overflow-x-hidden relative ${isGalaxy ? 'bg-[#02030A] text-white' : 'bg-[#FDFBF8] text-black'}`}
                isTransparent={isGalaxy}
                headerTheme={isGalaxy ? "dark" : "light"}
                disableContentPadding
            >
                {isGalaxy ? (
                    <div className="fixed inset-0 pointer-events-none overflow-hidden z-0">
                        <div className="absolute inset-0 bg-[#02030A]" />
                        <div
                            className="absolute inset-0 opacity-95"
                            style={{
                                backgroundImage:
                                    "radial-gradient(circle at 14% 22%, rgba(255,255,255,0.98) 1px, transparent 1.4px), radial-gradient(circle at 78% 62%, rgba(255,255,255,0.78) 1px, transparent 1.5px), radial-gradient(circle at 36% 82%, rgba(255,255,255,0.62) 0.8px, transparent 1.15px), radial-gradient(circle at 62% 18%, rgba(140,180,255,0.35) 0.9px, transparent 1.4px)",
                                backgroundSize: "170px 170px, 240px 240px, 300px 300px, 420px 420px",
                            }}
                        />
                        <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_top,rgba(255,255,255,0.12),transparent_45%),radial-gradient(ellipse_at_bottom,rgba(84,105,255,0.16),transparent_52%)]" />
                        <div className="absolute inset-0 bg-gradient-to-b from-black/25 via-transparent to-black/45" />
                    </div>
                ) : (
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
                            className="absolute bottom-[10%] -left-[10%] w-[50%] h-[50%] bg-[#FADBD8]/20 rounded-full blur-[100px]"
                        />
                    </div>
                )}

                {/* Main Content */}
                <main className="relative z-10 pt-[92px] sm:pt-[98px] md:pt-[108px] lg:pt-[114px] pb-32 px-3 sm:px-6 max-w-7xl mx-auto min-h-screen">

                    {/* Header: Title & Description */}
                    <div className="mb-3 md:mb-4 text-center md:text-left">
                        <motion.h1
                            initial={{ opacity: 0, x: -20 }}
                            animate={{ opacity: 1, x: 0 }}
                            className={`flex items-baseline justify-center md:justify-start gap-1 md:gap-1.5 text-[2.04rem] sm:text-[2.78rem] md:text-[3.48rem] lg:text-6xl font-black tracking-tighter leading-[0.94] md:leading-[0.9] uppercase whitespace-nowrap mb-2 ${isGalaxy ? 'text-white' : 'text-black'}`}
                        >
                            <span className="inline-block align-baseline">MY</span>
                            <motion.button
                                type="button"
                                onClick={() => setViewMode((prev) => (prev === 'GRID' ? 'GLOBE' : 'GRID'))}
                                whileHover={{ scale: 1.01 }}
                                whileTap={{ scale: 0.98 }}
                                className="group inline-flex items-baseline gap-1 md:gap-1.5 align-baseline leading-[0.9] transition-all duration-200"
                                title={isGalaxy ? t.switchToGallery : t.switchToGalaxy}
                                aria-label={isGalaxy ? t.switchToGallery : t.switchToGalaxy}
                            >
                                <span
                                    className={`relative inline-flex ${modeLabelSlotClass} justify-start ${modeLabelTextClass} ${isGalaxy ? 'text-white/95' : 'text-black/95'}`}
                                >
                                    {modeLabel}
                                    <span
                                        className={`pointer-events-none absolute left-0 -bottom-0.5 h-[2px] w-[96%] rounded-full transition-opacity duration-200 ${
                                            isGalaxy ? 'bg-white/45' : 'bg-black/30'
                                        } opacity-70 group-hover:opacity-100`}
                                    />
                                </span>
                                <span className={`inline-flex shrink-0 items-center justify-center w-4 h-4 md:w-5 md:h-5 mb-[0.04em] transition-colors ${
                                    isGalaxy ? 'text-white/70 group-hover:text-white' : 'text-black/55 group-hover:text-black'
                                }`}>
                                    <svg
                                        className="w-3 h-3 md:w-4 md:h-4 transition-transform duration-300 group-hover:rotate-180"
                                        viewBox="0 0 24 24"
                                        fill="none"
                                        stroke="currentColor"
                                        strokeWidth="2"
                                        strokeLinecap="round"
                                        strokeLinejoin="round"
                                    >
                                        <path d="M3 12a9 9 0 0 1 15.5-6.4" />
                                        <path d="M18.5 2.5v4h-4" />
                                        <path d="M21 12a9 9 0 0 1-15.5 6.4" />
                                        <path d="M5.5 21.5v-4h4" />
                                    </svg>
                                </span>
                            </motion.button>
                        </motion.h1>
                        <motion.p
                            initial={{ opacity: 0 }}
                            animate={{ opacity: 1 }}
                            transition={{ delay: 0.3 }}
                            className={`text-xs md:text-sm font-bold uppercase tracking-[0.2em] ${isGalaxy ? 'text-white/60' : 'text-gray-400'}`}
                        >
                            {archiveSubtitleFixed}
                        </motion.p>
                    </div>

                    {/* Stats & Toolbar Container */}
                    <div className="flex flex-col gap-3 md:gap-3.5 mb-4 md:mb-6">
                        {/* 1. Integrated Stats Bar */}
                        <motion.div
                            initial={{ opacity: 0, y: 20 }}
                            animate={{ opacity: 1, y: 0 }}
                            className={`order-2 flex flex-wrap items-center justify-center md:justify-start gap-2.5 md:gap-3 px-3 py-1.5 rounded-[28px] ${
                                isGalaxy
                                    ? 'bg-black/45 border border-white/22 backdrop-blur-xl shadow-[inset_0_1px_0_rgba(255,255,255,0.2),0_18px_40px_rgba(0,0,0,0.5)]'
                                    : 'bg-white/40 border border-white/60 backdrop-blur-md shadow-sm'
                            }`}
                        >
                            <StatItem
                                label={t.total}
                                count={stats.have + stats.wish}
                                isActive={activeTab === 'ALL'}
                                onClick={() => setActiveTab('ALL')}
                                isGalaxy={isGalaxy}
                            />
                            <div className={`w-px h-6 hidden sm:block ${isGalaxy ? 'bg-white/28' : 'bg-gray-200/50'}`} />
                            <StatItem
                                label={t.have}
                                count={stats.have}
                                activeColor={isGalaxy ? 'text-sky-300' : 'text-indigo-500'}
                                isActive={activeTab === 'HAVE'}
                                onClick={() => setActiveTab('HAVE')}
                                isGalaxy={isGalaxy}
                            />
                            <div className={`w-px h-6 hidden sm:block ${isGalaxy ? 'bg-white/28' : 'bg-gray-200/50'}`} />
                            <StatItem
                                label={t.wish}
                                count={stats.wish}
                                activeColor={isGalaxy ? 'text-rose-300' : 'text-rose-400'}
                                isActive={activeTab === 'WISH'}
                                onClick={() => setActiveTab('WISH')}
                                isGalaxy={isGalaxy}
                            />

                            {/* Language Toggle (Stats/Search 사이) */}
                            <button
                                onClick={() => setIsKorean(!isKorean)}
                                className={`group relative shrink-0 md:mx-1 inline-flex items-center justify-center h-10 w-10 transition-all ${
                                    isGalaxy
                                        ? 'text-white/90 hover:text-white'
                                        : 'text-black/65 hover:text-black'
                                }`}
                                aria-label={isKorean ? "영어로 전환" : "Switch to Korean"}
                                title={isKorean ? "한국어 사용 중" : "ENG mode"}
                            >
                                <svg
                                    className="w-8 h-8"
                                    viewBox="0 0 24 24"
                                    fill="none"
                                    stroke="currentColor"
                                    strokeWidth="1.85"
                                    strokeLinecap="round"
                                    strokeLinejoin="round"
                                >
                                    <circle cx="12" cy="12" r="9" />
                                    <path d="M3 12h18" />
                                    <path d="M12 3a14 14 0 0 1 0 18" />
                                    <path d="M12 3a14 14 0 0 0 0 18" />
                                </svg>
                                <span
                                    className={`pointer-events-none absolute left-1/2 -translate-x-1/2 -top-10 whitespace-nowrap rounded-full px-3 py-1 text-[10px] font-black tracking-[0.06em] transition-all duration-150 opacity-0 translate-y-1 group-hover:opacity-100 group-hover:translate-y-0 ${
                                        isGalaxy
                                            ? 'bg-black/80 text-white border border-white/30 shadow-[0_8px_20px_rgba(0,0,0,0.45)]'
                                            : 'bg-white text-black border border-black/10 shadow-md'
                                    }`}
                                >
                                    한국어 | ENG
                                </span>
                            </button>

                            {/* Quick Search */}
                            <div className="flex-1 min-w-[220px] w-full md:w-auto md:ml-2 relative group">
                                <div className={`absolute left-4 top-1/2 -translate-y-1/2 transition-colors ${
                                    isGalaxy ? 'text-white/45 group-focus-within:text-white' : 'text-gray-300 group-focus-within:text-black'
                                }`}>
                                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2.5" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"></path></svg>
                                </div>
                                <input
                                    type="text"
                                    value={searchQuery}
                                    onChange={(e) => setSearchQuery(e.target.value)}
                                    placeholder={t.searchPlaceholder}
                                    className={`w-full h-10 rounded-2xl pl-12 pr-4 text-[11px] font-black uppercase tracking-widest outline-none transition-all ${
                                        isGalaxy
                                            ? 'bg-black/38 border border-white/24 text-white placeholder:text-white/56 focus:border-white/72 focus:bg-black/28 shadow-[inset_0_1px_0_rgba(255,255,255,0.18)]'
                                            : 'bg-white/50 border border-transparent text-black placeholder:text-gray-300 focus:border-black/10 focus:bg-white shadow-inner'
                                    }`}
                                />
                                {searchQuery && (
                                    <button
                                        onClick={() => setSearchQuery("")}
                                        className={`absolute right-4 top-1/2 -translate-y-1/2 ${isGalaxy ? 'text-white/60 hover:text-white' : 'text-gray-300 hover:text-black'}`}
                                    >
                                        <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="3" d="M6 18L18 6M6 6l12 12"></path></svg>
                                    </button>
                                )}
                            </div>
                        </motion.div>

                        {/* 2. Action Toolbar */}
                        <div className="order-1 -mt-2 md:-mt-3 flex items-center gap-3 w-full md:w-auto justify-between md:justify-end">
                            <div className="flex items-center gap-3 w-full md:w-auto">
                                <div className="relative">
                                    <button
                                        onClick={() => setIsHistoryOpen(!isHistoryOpen)}
                                        className={`flex items-center gap-2 px-5 py-3 rounded-full transition-all ${
                                            isGalaxy
                                                ? `${isHistoryOpen ? 'ring-2 ring-white/85' : ''} border border-white/45 bg-black/58 backdrop-blur-md hover:bg-black/44 shadow-[0_8px_20px_rgba(0,0,0,0.45)]`
                                                : `${isHistoryOpen ? 'ring-2 ring-black bg-white shadow-md' : 'shadow-sm'} border border-gray-100 bg-white/50 backdrop-blur-sm hover:border-gray-200`
                                        }`}
                                    >
                                        <svg className={`w-4 h-4 ${isGalaxy ? 'text-white/92' : 'text-gray-400'}`} fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg>
                                        <span className={`text-[10px] font-black uppercase tracking-widest ${isGalaxy ? 'text-white' : 'text-gray-500'}`}>{t.history}</span>
                                        <span className={`text-xs font-black ml-1 ${isGalaxy ? 'text-white' : 'text-black'}`}>{stats.had}</span>
                                    </button>
                                    <AnimatePresence>
                                        {isHistoryOpen && (
                                            <HistoryModal
                                                historyItems={collection.filter(p => p.register_status === 'HAD')}
                                                onClose={() => setIsHistoryOpen(false)}
                                                onSelect={(p) => setSelectedPerfume(p as MyPerfume)}
                                                isKorean={isKorean}
                                            />
                                        )}
                                    </AnimatePresence>
                                </div>
                                <motion.button
                                    whileHover={{ scale: 1.02 }}
                                    whileTap={{ scale: 0.98 }}
                                    onClick={() => setIsSearchOpen(true)}
                                    className={`flex-1 md:flex-none flex items-center justify-center gap-2 md:gap-3 px-6 py-2.5 md:px-8 md:py-3 rounded-full text-[9px] md:text-[10px] font-black uppercase tracking-[0.1em] md:tracking-[0.2em] ${
                                        isGalaxy
                                            ? 'bg-[#606EFF]/90 border border-[#CFD4FF]/80 text-white backdrop-blur-md hover:bg-[#7380FF]/95 shadow-[0_10px_28px_rgba(78,96,255,0.55)]'
                                            : 'bg-black text-white shadow-lg shadow-black/10'
                                    }`}
                                >
                                    <span>{t.addScent}</span>
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
                                    <div className={`flex flex-col items-center justify-center py-32 rounded-[40px] border backdrop-blur-sm ${
                                        isGalaxy ? 'bg-black/35 border-white/20' : 'bg-white/30 border-white/50'
                                    }`}>
                                        <p className={`font-bold uppercase tracking-widest mb-6 ${isGalaxy ? 'text-white/70' : 'text-gray-400'}`}>{t.noScents}</p>
                                        <button
                                            onClick={() => setIsSearchOpen(true)}
                                            className={`font-black text-xs uppercase tracking-widest hover:underline decoration-2 underline-offset-8 ${isGalaxy ? 'text-white' : 'text-black'}`}
                                        >
                                            {t.addFirst}
                                        </button>
                                    </div>
                                ) : (
                                    <section className="grid grid-cols-3 sm:grid-cols-4 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6 gap-2 md:gap-8">
                                        {filteredCollection.map((item) => (
                                            <CabinetShelf
                                                key={item.my_perfume_id}
                                                perfume={item}
                                                onSelect={(p) => setSelectedPerfume(p as MyPerfume)}
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
                        className={`flex items-center gap-2 md:gap-3 px-4 py-2.5 md:px-8 md:py-4 rounded-full font-black text-[8px] md:text-xs uppercase tracking-widest ${
                            isGalaxy
                                ? 'bg-white/12 backdrop-blur-md border border-white/34 text-white shadow-2xl shadow-black/35'
                                : 'bg-white/80 backdrop-blur-md border border-white/50 text-black shadow-2xl shadow-black/5'
                        }`}
                    >
                        <div className={`w-1.5 h-1.5 md:w-2 md:h-2 rounded-full animate-pulse ${isGalaxy ? 'bg-white' : 'bg-black'}`} />
                        <span>{t.scentMap}</span>
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
    onClick,
    isGalaxy = false,
}: {
    label: string;
    count: number;
    activeColor?: string;
    isActive: boolean;
    onClick: () => void;
    isGalaxy?: boolean;
}) {
    return (
        <button
            onClick={onClick}
            className={`
                flex flex-col items-center min-w-[72px] md:min-w-[92px] px-3.5 md:px-4 py-1.5 md:py-2 rounded-[20px] transition-all duration-300
                ${isActive
                    ? (isGalaxy ? 'bg-white/20 shadow-sm ring-1 ring-white/35' : 'bg-white shadow-sm ring-1 ring-black/5')
                    : (isGalaxy ? 'hover:bg-white/16' : 'hover:bg-white/40')
                }
            `}
        >
            <span className={`text-[9px] md:text-[10px] font-black uppercase tracking-widest mb-0.5 transition-colors ${
                isActive
                    ? (isGalaxy ? 'text-white' : 'text-black')
                    : (isGalaxy ? 'text-white/65' : 'text-gray-400')
            }`}>
                {label}
            </span>
            <span className={`text-[1.8rem] md:text-[1.95rem] leading-none font-black transition-all ${
                isActive
                    ? activeColor
                    : (isGalaxy ? 'text-white/70' : 'text-gray-300')
            }`}>
                {count}
            </span>
        </button>
    );
}
