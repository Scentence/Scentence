"use client";

import { useEffect, useState } from "react";
import { useSession, signOut } from "next-auth/react";
import Link from "next/link";
import { motion, AnimatePresence, Variants } from "framer-motion";
import { User, Shield, LogOut, Library } from "lucide-react";

interface UserProfileMenuProps {
    isOpen: boolean;
    onClose: () => void;
}

// [MENU ITEM] 스타일 컴포넌트 (Sidebar와 동일 스타일)
function MenuItem({ href, icon: Icon, title, desc, onClick, className = "" }: any) {
    return (
        <Link
            href={href}
            onClick={onClick}
            className={`flex items-center gap-4 p-4 hover:bg-white/10 transition-all duration-300 group rounded-xl ${className}`}
        >
            <div className="relative group-hover:scale-110 transition-transform duration-300">
                <Icon strokeWidth={1.5} className="w-5 h-5 text-[#1a1a1a] group-hover:text-black transition-colors" />
            </div>

            <div className="flex flex-col">
                <span className="text-base font-bold text-[#1a1a1a] tracking-tight group-hover:tracking-widest transition-all duration-500 whitespace-nowrap">
                    {title}
                </span>
                {desc && <span className="text-[10px] text-gray-500 mt-0.5">{desc}</span>}
            </div>
            {/* Dot Indicator */}
            <div className="ml-auto w-1.5 h-1.5 rounded-full bg-black opacity-0 group-hover:opacity-100 transition-all transform scale-0 group-hover:scale-100 shadow-[0_0_8px_rgba(0,0,0,0.1)]" />
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

    const handleOverlayClick = () => onClose();

    // [ANIMATION VARIANTS]
    const containerVariants: Variants = {
        hidden: { opacity: 0, scale: 0.95, y: -10, backdropFilter: "blur(0px)" },
        show: {
            opacity: 1, scale: 1, y: 0,
            backdropFilter: "blur(16px)", // 서서히 흐려지도록 추가
            transition: { type: "spring" as const, stiffness: 300, damping: 30 }
        },
        exit: { opacity: 0, scale: 0.95, y: -10, backdropFilter: "blur(0px)", transition: { duration: 0.2 } }
    };

    // [HYPER-REALISTIC LIQUID GLASS BLOCK]
    const liquidGlassBlock = "bg-gradient-to-br from-white/[0.08] to-transparent border border-white/40 shadow-[inset_0_1px_1px_rgba(255,255,255,0.9),inset_0_15px_30px_rgba(255,255,255,0.15),inset_0_-2px_10px_rgba(0,0,0,0.05),0_20px_40px_-10px_rgba(0,0,0,0.2)] overflow-hidden rounded-[32px]";

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
                        className="fixed top-20 right-20 z-50 w-[260px] flex flex-col gap-4"
                        variants={containerVariants}
                        initial="hidden"
                        animate="show"
                        exit="exit"
                    >
                        {/* --- CHUNK 1: ADMIN STUDIO --- */}
                        {isAdmin && (
                            <motion.div className={`${liquidGlassBlock} p-1`}>
                                <MenuItem href="/admin" icon={Shield} title="관리자 페이지" className="!text-blue-600" onClick={onClose} />
                            </motion.div>
                        )}

                        {/* --- CHUNK 2: PERSONAL --- */}
                        <motion.div className={`${liquidGlassBlock} p-1`}>
                            <div className="flex flex-col divide-y divide-black/5">
                                <MenuItem href="/mypage" icon={User} title="마이 페이지" desc="내 정보 및 프로필 관리" onClick={onClose} />
                                <MenuItem href="/archives" icon={Library} title="마이 컬렉션" desc="나만의 향수 라이브러리" onClick={onClose} />
                            </div>
                        </motion.div>

                        {/* --- CHUNK 3: LOGOUT --- */}
                        <motion.div className={`${liquidGlassBlock} p-1`}>
                            <button
                                onClick={() => {
                                    if (session) signOut({ callbackUrl: "/login" });
                                    else {
                                        if (typeof window !== "undefined") { localStorage.removeItem("localAuth"); window.location.href = "/login"; }
                                        setLocalUser(null); onClose();
                                    }
                                }}
                                className="w-full flex items-center justify-between p-4 px-6 hover:bg-white/10 transition-all duration-300 group rounded-xl"
                            >
                                <span className="text-base font-bold text-[#1a1a1a] tracking-tight group-hover:tracking-widest transition-all duration-500">로그아웃</span>
                                <LogOut strokeWidth={1.5} className="w-5 h-5 text-gray-400 group-hover:text-red-500 transition-all duration-300" />
                            </button>
                        </motion.div>
                    </motion.div>
                </>
            )}
        </AnimatePresence>
    );
}