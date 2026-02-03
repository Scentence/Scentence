"use client";

import { useState } from "react";
import Sidebar from "@/components/common/sidebar";
import Header from "@/components/common/Header";

interface PageLayoutProps {
    children: React.ReactNode;
    subTitle?: string;
    isTransparent?: boolean;
    className?: string; // Wrapper className
    mainClassName?: string; // Main className passed to children wrapper if needed, or consumers handle it
}

export default function PageLayout({
    children,
    subTitle,
    isTransparent = false,
    className = "min-h-screen bg-[#FDFBF8] text-[#2B2B2B] font-sans"
}: PageLayoutProps) {
    const [isNavOpen, setIsNavOpen] = useState(false);

    return (
        <div className={className}>
            <Sidebar
                isOpen={isNavOpen}
                onClose={() => setIsNavOpen(false)}
                context="home"
            />
            {isNavOpen && (
                <div
                    className="fixed inset-0 bg-transparent z-40"
                    onClick={() => setIsNavOpen(false)}
                />
            )}

            <Header
                onToggleSidebar={() => setIsNavOpen(!isNavOpen)}
                isSidebarOpen={isNavOpen}
                subTitle={subTitle}
                isTransparent={isTransparent}
            />

            {children}
        </div>
    );
}
