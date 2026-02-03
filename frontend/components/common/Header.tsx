"use client";

import Link from "next/link";
import { useState, useEffect } from "react";
import { useSession } from "next-auth/react";
import UserProfileMenu from "@/components/common/UserProfileMenu";

interface HeaderProps {
    onToggleSidebar: () => void;
    isSidebarOpen: boolean;
    subTitle?: string;
    showGreeting?: boolean;
    className?: string;
    isTransparent?: boolean;
}

export default function Header({
    onToggleSidebar,
    isSidebarOpen,
    subTitle,
    showGreeting = false,
    className = "",
    isTransparent = false,
}: HeaderProps) {
    const { data: session } = useSession();
    const [isProfileMenuOpen, setIsProfileMenuOpen] = useState(false);

    // Profile Logic (moved from individual pages)
    const [localUser, setLocalUser] = useState<{ memberId?: string | null; email?: string | null; nickname?: string | null } | null>(null);
    const [profileImageUrl, setProfileImageUrl] = useState<string | null>(null);
    const [profileNickname, setProfileNickname] = useState<string | null>(null);

    useEffect(() => {
        if (typeof window === "undefined") return;
        const stored = localStorage.getItem("localAuth");
        if (stored) {
            try {
                setLocalUser(JSON.parse(stored));
            } catch {
                setLocalUser(null);
            }
        }
    }, []);

    useEffect(() => {
        const memberId = session?.user?.id || localUser?.memberId;

        if (!memberId) {
            setProfileImageUrl(null);
            return;
        }

        fetch(`/api/users/profile/${memberId}`)
            .then((res) => (res.ok ? res.json() : null))
            .then((data) => {
                if (data?.nickname) {
                    setProfileNickname(data.nickname);
                }

                if (data?.profile_image_url) {
                    const rawUrl = data.profile_image_url;
                    const finalUrl = (rawUrl.startsWith("http") || rawUrl.startsWith("/uploads"))
                        ? rawUrl
                        : `/api${rawUrl}`;
                    setProfileImageUrl(finalUrl);
                }
            })
            .catch(() => setProfileImageUrl(null));
    }, [session, localUser]);

    const displayName = profileNickname || session?.user?.name || localUser?.nickname || localUser?.email?.split('@')[0] || "Guest";
    const isLoggedIn = Boolean(session || localUser);

    return (
        <header
            className={`fixed top-0 left-0 right-0 z-30 flex items-center justify-between px-4 md:px-10 py-4 transition-colors duration-300 ${isTransparent ? 'bg-transparent' : 'bg-[#FDFBF8] border-b border-[#F0F0F0]'
                } ${className}`}
        >
            {/* Logo & Subtitle */}
            <div className="flex items-center gap-2 md:gap-4">
                <Link href="/" className="text-lg md:text-xl font-bold text-black tracking-[0.15em] uppercase hover:opacity-70 transition">
                    SCENTENCE
                </Link>
                {subTitle && (
                    <span className="text-[9px] md:text-xs font-semibold text-[#8C6A1D] tracking-[0.1em] md:tracking-[0.3em] uppercase border-l border-gray-300 pl-2 md:pl-4 block whitespace-normal md:whitespace-nowrap w-min md:w-auto leading-none md:leading-normal">
                        {subTitle}
                    </span>
                )}
            </div>

            {/* Right Actions */}
            <div className="flex items-center gap-3 md:gap-4">
                {!isLoggedIn ? (
                    <div className="flex items-center gap-2 text-sm md:text-base font-medium text-gray-400">
                        <Link href="/login" className="hover:text-black transition-colors">Sign in</Link>
                        <span className="text-gray-300 text-xs">|</span>
                        <Link href="/signup" className="hover:text-black transition-colors">Sign up</Link>
                    </div>
                ) : (
                    <div className="flex items-center gap-2 md:gap-3">
                        {showGreeting && (
                            <span className="hidden md:inline-block text-base font-medium text-gray-600 mr-2">
                                <strong className="font-bold text-gray-900">{displayName}</strong>님 반가워요!
                            </span>
                        )}
                        <button
                            id="profile-menu-toggle"
                            onClick={() => setIsProfileMenuOpen(!isProfileMenuOpen)}
                            className="w-8 h-8 md:w-10 md:h-10 flex items-center justify-center rounded-full p-0.5 transform-gpu bg-gradient-to-br from-white/20 to-transparent border border-white/40 shadow-sm will-change-transform transition-all hover:scale-105 active:scale-95 overflow-hidden"
                        >
                            <img
                                src={profileImageUrl || session?.user?.image || "/default_profile.png"}
                                alt="Profile"
                                className="w-full h-full object-cover rounded-full"
                                onError={(e) => {
                                    const target = e.currentTarget;
                                    if (session?.user?.image && target.src !== session.user.image) {
                                        target.src = session.user.image;
                                    } else {
                                        target.src = "/default_profile.png";
                                    }
                                }}
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
                    onClick={onToggleSidebar}
                    className="w-8 h-8 md:w-10 md:h-10 flex items-center justify-center rounded-full p-0.5 transform-gpu bg-gradient-to-br from-white/20 to-transparent border border-white/40 shadow-sm will-change-transform transition-all hover:scale-105 active:scale-95"
                >
                    {isSidebarOpen ? (
                        <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor" className="w-full h-full text-[#333] p-1">
                            <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
                        </svg>
                    ) : (
                        <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor" className="w-full h-full text-[#333] p-1">
                            <path strokeLinecap="round" strokeLinejoin="round" d="M4 6h16M4 12h16M4 18h16" />
                        </svg>
                    )}
                </button>
            </div>
        </header>
    );
}
