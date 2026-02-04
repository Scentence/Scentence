'use client';

import { useState, useEffect } from "react";
import Link from "next/link";
import { useSession } from "next-auth/react";
import PageLayout from "@/components/common/PageLayout";
import { motion } from "framer-motion";

export default function ContactPage() {
    const { data: session } = useSession();
    const [copied, setCopied] = useState<string | null>(null);


    const handleCopy = (text: string, type: string) => {
        navigator.clipboard.writeText(text);
        setCopied(type);
        setTimeout(() => setCopied(null), 2000);
    };

    return (
        <PageLayout className="min-h-screen bg-[#FDFBF8] text-black font-sans relative selection:bg-black selection:text-white overflow-x-hidden flex flex-col">

            <main className="flex-1 pt-[100px] flex flex-col">

                {/* [MARQUEE SECTION] */}
                <div className="py-20 overflow-hidden relative border-b border-gray-200 bg-white select-none">
                    <motion.div
                        className="flex whitespace-nowrap"
                        animate={{ x: [0, "-50%"] }}
                        transition={{
                            duration: 25,
                            repeat: Infinity,
                            ease: "linear"
                        }}
                    >
                        {/* FIRST SET */}
                        <div className="flex items-center shrink-0">
                            <span className="text-8xl md:text-[10rem] font-black tracking-tighter text-transparent opacity-10 px-6" style={{ WebkitTextStroke: "2px black" }}>
                                GET IN TOUCH •
                            </span>
                            <span className="text-8xl md:text-[10rem] font-black tracking-tighter text-black px-6">
                                CONTACT US •
                            </span>
                            <span className="text-8xl md:text-[10rem] font-black tracking-tighter text-transparent opacity-10 px-6" style={{ WebkitTextStroke: "2px black" }}>
                                SCENTENCE •
                            </span>
                        </div>
                        {/* SECOND SET (Identical) */}
                        <div className="flex items-center shrink-0">
                            <span className="text-8xl md:text-[10rem] font-black tracking-tighter text-transparent opacity-10 px-6" style={{ WebkitTextStroke: "2px black" }}>
                                GET IN TOUCH •
                            </span>
                            <span className="text-8xl md:text-[10rem] font-black tracking-tighter text-black px-6">
                                CONTACT US •
                            </span>
                            <span className="text-8xl md:text-[10rem] font-black tracking-tighter text-transparent opacity-10 px-6" style={{ WebkitTextStroke: "2px black" }}>
                                SCENTENCE •
                            </span>
                        </div>
                    </motion.div>
                </div>

                {/* [MAIN GRID] */}
                <div className="flex-1 grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 divide-y md:divide-y-0 md:divide-x divide-gray-200 border-b border-gray-200">

                    {/* Channel 1: Kakao */}
                    <div className="group relative p-12 flex flex-col justify-between hover-invert cursor-pointer min-h-[400px]"
                        onClick={() => window.open('https://pf.kakao.com/_Scentence', '_blank')}>
                        <div className="flex justify-between items-start">
                            <span className="text-xs font-bold uppercase tracking-[0.2em] text-muted">01 / Instant</span>
                            <span className="text-3xl">💬</span>
                        </div>
                        <div>
                            <h3 className="text-4xl font-bold mb-4 group-hover:translate-x-2 transition-transform">Kakao Channel</h3>
                            <p className="text-sm font-medium text-muted mb-8 leading-relaxed">
                                가장 빠른 답변을 받아보세요.<br />
                                챗봇 상담 및 실시간 문의가 가능합니다.
                            </p>
                            <span className="inline-block border-b border-black group-hover:border-white pb-1 text-xs font-bold uppercase tracking-widest">
                                Visit Channel →
                            </span>
                        </div>
                    </div>

                    {/* Channel 2: Email */}
                    <div className="group relative p-12 flex flex-col justify-between hover-invert cursor-pointer min-h-[400px]"
                        onClick={() => handleCopy('5scompany@contact.com', 'email')}>
                        <div className="flex justify-between items-start">
                            <span className="text-xs font-bold uppercase tracking-[0.2em] text-muted">02 / Official</span>
                            <span className="text-3xl">📧</span>
                        </div>
                        <div>
                            <h3 className="text-4xl font-bold mb-4 group-hover:translate-x-2 transition-transform">
                                {copied === 'email' ? 'Copied!' : 'Email Us'}
                            </h3>
                            <p className="text-sm font-medium text-muted mb-8 leading-relaxed">
                                비즈니스 제휴 및 기타 상세 문의.<br />
                                24시간 이내에 회신 드립니다.
                            </p>
                            <span className="inline-block border-b border-black group-hover:border-white pb-1 text-xs font-bold uppercase tracking-widest font-mono">
                                5scompany@contact.com ❐
                            </span>
                        </div>
                    </div>

                    {/* Channel 3: Location (or Insta) */}
                    <div className="group relative p-12 flex flex-col justify-between hover-invert cursor-pointer min-h-[400px]">
                        <div className="flex justify-between items-start">
                            <span className="text-xs font-bold uppercase tracking-[0.2em] text-muted">03 / Visit</span>
                            <span className="text-3xl">📍</span>
                        </div>
                        <div>
                            <h3 className="text-4xl font-bold mb-4 group-hover:translate-x-2 transition-transform">Headquarters</h3>
                            <p className="text-sm font-medium text-muted mb-8 leading-relaxed">
                                서울특별시 마포구 연희로 1길 52 3F,<br />
                                5S Company
                            </p>
                            <span className="inline-block border-b border-black group-hover:border-white pb-1 text-xs font-bold uppercase tracking-widest">
                                Open Map →
                            </span>
                        </div>
                    </div>
                </div>

                {/* [FOOTER with LOGO] */}
                <div className="py-20 flex flex-col items-center justify-center bg-[#FDFBF8]">
                    <div className="flex items-center gap-1 mb-2 opacity-50 hover:opacity-100 transition-opacity duration-500">
                        <span className="text-xs font-medium tracking-widest text-[#888]">Since 2026 Team.</span>
                        {/* Permanently Skewed Logo */}
                        <img
                            src="/images/5s_logo_skewed.png"
                            alt="5S Logo"
                            className="w-8 h-8 object-contain hover:scale-110 transition-transform duration-300"
                        />
                    </div>
                    {/* <p className="text-[10px] text-gray-300 font-mono mt-4">
                        DESIGNED BY SCENTENCE
                    </p> */}
                </div>
            </main>
        </PageLayout>
    );
}