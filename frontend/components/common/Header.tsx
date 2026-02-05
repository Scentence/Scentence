"use client";

import Link from "next/link";
import { useState, useEffect } from "react";
import { useSession } from "next-auth/react";


interface HeaderProps {
    onToggleSidebar: () => void;
    isSidebarOpen: boolean;
    onToggleProfile?: () => void; // New prop
    isProfileMenuOpen?: boolean;  // New prop
    subTitle?: string;
    showGreeting?: boolean;
    className?: string;
    isTransparent?: boolean;
    theme?: "light" | "dark";
}

export default function Header({
    onToggleSidebar,
    isSidebarOpen,
    onToggleProfile,       // New prop destructuring
    isProfileMenuOpen,     // New prop destructuring
    subTitle,
    showGreeting = false,
    className = "",
    isTransparent = false,
    theme = "light",
}: HeaderProps) {
    const { data: session } = useSession();
    // Removed internal state: const [isProfileMenuOpen, setIsProfileMenuOpen] = useState(false);

    // localAuth 제거: 프로필은 세션 기준으로만 조회
    const [profileImageUrl, setProfileImageUrl] = useState<string | null>(null);
    const [profileNickname, setProfileNickname] = useState<string | null>(null);

    useEffect(() => {
        const memberId = session?.user?.id;

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
    }, [session]);

    const displayName = profileNickname || session?.user?.name || session?.user?.email?.split('@')[0] || "Guest";
    const isLoggedIn = Boolean(session);

    // Glass/Scroll logic - Always Active
    const headerStyle = `bg-${theme === 'dark' ? 'black' : 'white'}/60 backdrop-blur-md`;

    return (
        <header
            className={`fixed top-0 left-0 right-0 z-50 flex items-center justify-between px-4 md:px-10 py-4 transition-all duration-500 ease-in-out ${headerStyle} ${className}`}
        >
            {/* Logo & Subtitle */}
            <div className="flex items-center gap-2 md:gap-4">
                <Link href="/" className={`text-lg md:text-xl font-bold tracking-[0.15em] uppercase hover:opacity-70 transition ${theme === 'dark' ? 'text-white' : 'text-black'}`}>
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
                    <div className={`flex items-center gap-2 text-sm md:text-base font-medium ${theme === 'dark' ? 'text-white/70' : 'text-gray-400'}`}>
                        <Link href="/login" className={`hover:text-${theme === 'dark' ? 'white' : 'black'} transition-colors font-semibold`}>Join us</Link>
                    </div>
                ) : (
                    <div className="flex items-center gap-2 md:gap-3">
                        {showGreeting && (
                            <span className={`hidden md:inline-block text-base font-medium mr-2 ${theme === 'dark' ? 'text-white/80' : 'text-gray-600'}`}>
                                <strong className={`font-bold ${theme === 'dark' ? 'text-white' : 'text-gray-900'}`}>{displayName}</strong>님 반가워요!
                            </span>
                        )}
                        <button
                            id="profile-menu-toggle"
                            onClick={onToggleProfile} // Updated onClick
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
                        {/* UserProfileMenu removed from here */}
                    </div>
                )}

                <button
                    id="global-menu-toggle"
                    onClick={onToggleSidebar}
                    className="w-8 h-8 md:w-10 md:h-10 flex items-center justify-center rounded-full p-0.5 transform-gpu bg-gradient-to-br from-white/20 to-transparent border border-white/40 shadow-sm will-change-transform transition-all hover:scale-105 active:scale-95"
                >
                    {isSidebarOpen ? (
                        <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor" className={`w-full h-full p-1 ${theme === 'dark' ? 'text-white' : 'text-[#333]'}`}>
                            <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
                        </svg>
                    ) : (
                        <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor" className={`w-full h-full p-1 ${theme === 'dark' ? 'text-white' : 'text-[#333]'}`}>
                            <path strokeLinecap="round" strokeLinejoin="round" d="M4 6h16M4 12h16M4 18h16" />
                        </svg>
                    )}
                </button>
            </div>
        </header>
    );
}
