"use client";

import { useEffect, useState } from "react";
import { useSession, signOut } from "next-auth/react";
import Link from "next/link";
import { motion, AnimatePresence } from "framer-motion";

interface SidebarProps {
    isOpen: boolean;
    onClose: () => void;
    context: "home" | "chat";
}

// [MENU ITEM] Shared Style
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

export default function Sidebar({ isOpen, onClose, context }: SidebarProps) {
    const { data: session } = useSession();
    const [localUser, setLocalUser] = useState<{ memberId?: string | null; email?: string | null; nickname?: string | null; roleType?: string | null; isAdmin?: boolean } | null>(null);
    const [profileRoleType, setProfileRoleType] = useState<string | null>(null);
    const [profileImageUrl, setProfileImageUrl] = useState<string | null>(null);
    const apiBaseUrl = process.env.NEXT_PUBLIC_API_URL || "";

    // [AUTH CHECK LOGIC]
    useEffect(() => {
        if (!isOpen) return;
        if (typeof window === "undefined") return;
        const stored = localStorage.getItem("localAuth");
        if (!stored) { setLocalUser(null); return; }
        try { setLocalUser(JSON.parse(stored)); } catch { setLocalUser(null); }
    }, [isOpen]);

    useEffect(() => {
        if (!isOpen) return;
        if (typeof window === "undefined") return;
        const memberId = session?.user?.id || localUser?.memberId;
        if (!memberId) { setProfileImageUrl(null); return; }
        fetch(`${apiBaseUrl}/users/profile/${memberId}`)
            .then((res) => (res.ok ? res.json() : null))
            .then((data) => {
                if (data?.profile_image_url) {
                    const url = data.profile_image_url.startsWith("http") ? data.profile_image_url : `${apiBaseUrl}${data.profile_image_url}`;
                    setProfileImageUrl(url);
                } else { setProfileImageUrl(null); }
                if (data?.role_type) setProfileRoleType(data.role_type);
            })
            .catch(() => setProfileImageUrl(null));
    }, [isOpen, localUser, session]);

    const isLoggedIn = Boolean(session || localUser);
    const resolvedRoleType = (localUser?.roleType || (localUser?.isAdmin ? "ADMIN" : "") || profileRoleType || "").toUpperCase();
    const isAdmin = resolvedRoleType === "ADMIN";

    // Outside Click Close
    const [ref, setRef] = useState<HTMLDivElement | null>(null);
    useEffect(() => {
        function handleClickOutside(event: MouseEvent) {
            const target = event.target as Element;
            if (target.closest("#global-menu-toggle")) return;
            if (ref && !ref.contains(target as Node)) { onClose(); }
        }
        if (isOpen) { document.addEventListener("mousedown", handleClickOutside); }
        return () => { document.removeEventListener("mousedown", handleClickOutside); };
    }, [isOpen, ref, onClose]);

    // [ANIMATION VARIANTS] Staggered Children
    const containerVariants = {
        hidden: { opacity: 0 },
        show: {
            opacity: 1,
            transition: {
                staggerChildren: 0.1, // 카드 간 시간차 등장
                delayChildren: 0.05
            }
        },
        exit: {
            opacity: 0,
            transition: { staggerChildren: 0.05, staggerDirection: -1 }
        }
    };

    const cardVariants = {
        hidden: { opacity: 0, y: -20, scale: 0.95 },
        show: {
            opacity: 1, y: 0, scale: 1,
            transition: { duration: 0.4, ease: [0.33, 1, 0.68, 1] }
        },
        exit: {
            opacity: 0, y: -10, scale: 0.95,
            transition: { duration: 0.2 }
        }
    };

    return (
        <AnimatePresence>
            {isOpen && (
                <>
                    <div className="fixed inset-0 z-40 bg-transparent" />

                    {/* [CHUNK LAYOUT] Crazy Sensational Stacks */}
                    <motion.div
                        ref={setRef}
                        className="fixed top-20 right-6 z-50 w-[280px] flex flex-col gap-3"
                        variants={containerVariants}
                        initial="hidden"
                        animate="show"
                        exit="exit"
                    >




                        {/* --- CHUNK 1: HOME (Separated) --- */}
                        <motion.div variants={cardVariants} className="bg-white/80 backdrop-blur-xl rounded-[2rem] p-1.5 shadow-2xl border border-white/40 overflow-hidden">
                            <MenuItem href="/" title="HOME" desc="메인 홈으로" onClick={onClose} />
                        </motion.div>

                        {/* --- CHUNK 3: CORE FEATURES (Sensational) --- */}
                        <motion.div variants={cardVariants} className="bg-white/80 backdrop-blur-xl rounded-[2rem] p-1.5 shadow-2xl border border-white/40 overflow-hidden">
                            <div className="flex flex-col gap-1">
                                <MenuItem href="/chat" title="SCENT CURATOR" desc="AI 향수 추천" onClick={onClose} />
                                <MenuItem href="/layering" title="MIX & MATCH" desc="향기 레이어링" onClick={onClose} />
                                <MenuItem href="/perfume-network/nmap" title="PERFUME MAP" desc="향수 시각화 지도" onClick={onClose} />
                                <MenuItem href="/perfume-wiki" title="PERFUME WIKI" desc="향수 백과사전" onClick={onClose} />
                            </div>
                        </motion.div>



                        {/* --- CHUNK 5: FOOTER (Brand & Contact) --- */}
                        <motion.div variants={cardVariants} className="bg-black text-white rounded-[2rem] p-5 shadow-2xl flex flex-col gap-4">
                            <Link href="/contact" onClick={onClose} className="flex items-center justify-between group">
                                <span className="text-xs font-bold tracking-[0.2em] text-gray-400 group-hover:text-white transition-colors">CONTACT US</span>
                                <span className="w-2 h-2 rounded-full bg-red-500 shadow-[0_0_10px_rgba(239,68,68,0.8)] group-hover:bg-green-500 group-hover:shadow-[0_0_10px_rgba(34,197,94,0.8)] transition-all duration-300" />
                            </Link>

                            <div className="h-px bg-white/10" />

                            <Link href="/about" onClick={onClose} className="cursor-pointer group">
                                <p className="text-[10px] text-gray-500 mb-1">About.</p>
                                <div className="flex items-center justify-between">
                                    <span className="text-sm font-black tracking-tighter group-hover:tracking-widest transition-all duration-500">SCENTENCE</span>
                                    <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor" className="w-4 h-4 opacity-0 group-hover:opacity-100 -translate-x-2 group-hover:translate-x-0 transition-all duration-300">
                                        <path strokeLinecap="round" strokeLinejoin="round" d="M13.5 4.5L21 12m0 0l-7.5 7.5M21 12H3" />
                                    </svg>
                                </div>
                            </Link>
                        </motion.div>
                    </motion.div>
                </>
            )}
        </AnimatePresence>
    );
}