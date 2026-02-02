"use client";

import { useEffect, useState } from "react";
import { useSession, signOut } from "next-auth/react";
import Link from "next/link";
import { motion, AnimatePresence } from "framer-motion";

interface UserProfileMenuProps {
    isOpen: boolean;
    onClose: () => void;
}

// [MENU ITEM] 스타일 컴포넌트 (Sidebar와 동일 스타일)
function MenuItem({ href, icon, title, desc, onClick, className = "" }: any) {
    return (
        <Link
            href={href}
            onClick={onClick}
            className={`flex items-center justify-between p-3 rounded-xl hover:bg-[#FDFBF8] transition-colors group ${className}`}
        >
            <div className="flex flex-col">
                <span className="text-lg font-bold text-[#1a1a1a] tracking-tight group-hover:tracking-wide transition-all duration-300">
                    {title}
                </span>
                {desc && <span className="text-[10px] text-gray-400 mt-0.5">{desc}</span>}
            </div>
            {/* Dot Indicator */}
            <div className="w-1.5 h-1.5 rounded-full bg-black opacity-0 group-hover:opacity-100 transition-all transform scale-0 group-hover:scale-100" />
        </Link>
    );
}

export default function UserProfileMenu({ isOpen, onClose }: UserProfileMenuProps) {
    const { data: session } = useSession();
    const [localUser, setLocalUser] = useState<{ roleType?: string | null; isAdmin?: boolean } | null>(null);
    const [profileRoleType, setProfileRoleType] = useState<string | null>(null);
    const apiBaseUrl = process.env.NEXT_PUBLIC_API_URL || "";

    // [AUTH CHECK] 권한 확인 로직
    useEffect(() => {
        if (!isOpen) return;
        if (typeof window === "undefined") return;
        const stored = localStorage.getItem("localAuth");
        if (stored) {
            try { setLocalUser(JSON.parse(stored)); } catch { setLocalUser(null); }
        }
    }, [isOpen]);

    // Role 확인
    useEffect(() => {
        if (!isOpen) return;
        const memberId = session?.user?.id || (localUser as any)?.memberId;
        if (!memberId) return;

        fetch(`${apiBaseUrl}/users/profile/${memberId}`)
            .then((res) => (res.ok ? res.json() : null))
            .then((data) => {
                if (data?.role_type) setProfileRoleType(data.role_type);
            })
            .catch(() => { });
    }, [isOpen, localUser, session]);

    const resolvedRoleType = (localUser?.roleType || (localUser?.isAdmin ? "ADMIN" : "") || profileRoleType || "").toUpperCase();
    const isAdmin = resolvedRoleType === "ADMIN";

    // Outside Click Close
    useEffect(() => {
        function handleClickOutside(event: MouseEvent) {
            const target = event.target as Element;
            // 프로필 아이콘(토글 버튼) 클릭 시 닫히지 않도록 예외 처리용 ID 확인 필요
            if (target.closest("#profile-menu-toggle")) return;
            // 메뉴 내부 클릭은 유지, 그 외 닫기 (실제 구현 시 ref 사용 권장하지만 간단히 처리)
        }
        if (isOpen) { document.addEventListener("mousedown", handleClickOutside); }
        return () => { document.removeEventListener("mousedown", handleClickOutside); };
        // *심플한 닫기 처리를 위해 메뉴 클릭 시 닫히도록 MenuItem에 onClose 연결함
    }, [isOpen, onClose]);

    // 배경 클릭 시 닫기용
    const handleOverlayClick = () => onClose();

    // [ANIMATION VARIANTS]
    const containerVariants = {
        hidden: { opacity: 0, scale: 0.95, y: -10 },
        show: {
            opacity: 1, scale: 1, y: 0,
            transition: { type: "spring", stiffness: 300, damping: 30 }
        },
        exit: { opacity: 0, scale: 0.95, y: -10, transition: { duration: 0.2 } }
    };

    return (
        <AnimatePresence>
            {isOpen && (
                <>
                    {/* 투명 배경 (외부 클릭 감지 역할) */}
                    <div
                        className="fixed inset-0 z-40 bg-transparent"
                        onClick={handleOverlayClick}
                    />

                    <motion.div
                        className="fixed top-[70px] right-[70px] z-50 w-[240px] flex flex-col gap-2"
                        variants={containerVariants}
                        initial="hidden"
                        animate="show"
                        exit="exit"
                    >
                        {/* --- CHUNK 1: ADMIN STUDIO --- */}
                        {isAdmin && (
                            <div className="bg-white/80 backdrop-blur-xl rounded-[1.5rem] p-1.5 shadow-2xl border border-blue-100/50 overflow-hidden">
                                <MenuItem href="/admin" title="ADMIN STUDIO" className="text-blue-600" onClick={onClose} />
                            </div>
                        )}

                        {/* --- CHUNK 2: PERSONAL (My Page & Gallery) --- */}
                        <div className="bg-white/80 backdrop-blur-xl rounded-[1.5rem] p-1.5 shadow-2xl border border-white/40 overflow-hidden">
                            <div className="flex flex-col gap-1">
                                <MenuItem href="/mypage" title="MY PAGE" desc="마이 페이지" onClick={onClose} />
                                <MenuItem href="/archives" title="MY GALLERY" desc="향수 컬렉션" onClick={onClose} />
                            </div>
                        </div>

                        {/* --- CHUNK 3: LOGOUT --- */}
                        <div className="bg-white/80 backdrop-blur-xl rounded-[1.5rem] p-1.5 shadow-2xl border border-white/40 overflow-hidden">
                            <button
                                onClick={() => {
                                    if (session) signOut({ callbackUrl: "/login" });
                                    else {
                                        if (typeof window !== "undefined") { localStorage.removeItem("localAuth"); window.location.href = "/login"; }
                                        setLocalUser(null); onClose();
                                    }
                                }}
                                className="w-full text-left flex items-center justify-between p-3 rounded-xl hover:bg-black hover:text-white transition-all duration-300 group"
                            >
                                <span className="text-sm font-bold tracking-widest pl-1">LOG OUT</span>
                                <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor" className="w-4 h-4 group-hover:text-red-500 group-hover:rotate-180 transition-all duration-500">
                                    <path strokeLinecap="round" strokeLinejoin="round" d="M5.636 5.636a9 9 0 1012.728 0M12 3v9" />
                                </svg>
                            </button>
                        </div>
                    </motion.div>
                </>
            )}
        </AnimatePresence>
    );
}