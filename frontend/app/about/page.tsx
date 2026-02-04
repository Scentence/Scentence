'use client';

import { useState, useRef, useEffect } from "react";
import Link from "next/link";
import { useSession } from "next-auth/react";
import PageLayout from "@/components/common/PageLayout";
import { motion, useScroll, useTransform, useInView } from "framer-motion";

// [Animation Variants]
const containerVariants = {
    hidden: { opacity: 0 },
    show: {
        opacity: 1,
        transition: {
            staggerChildren: 0.15,
            delayChildren: 0.2,
        }
    }
};

const textRevealVariants = {
    hidden: { y: "110%", opacity: 0 },
    show: {
        y: "0%",
        opacity: 1,
        transition: {
            duration: 1.2,
            ease: [0.16, 1, 0.3, 1] // Custom quint-like ease
        }
    }
};

const fadeUpVariants = {
    hidden: { opacity: 0, y: 50 },
    visible: {
        opacity: 1,
        y: 0,
        transition: {
            duration: 0.8,
            ease: "easeOut"
        }
    }
};

// [Helper Component for Animate on Scroll]
const AnimateOnScroll = ({ children, delay = 0, className = "" }: { children: React.ReactNode, delay?: number, className?: string }) => {
    const ref = useRef(null);
    const isInView = useInView(ref, { once: true, margin: "-10%" });
    return (
        <motion.div
            ref={ref}
            variants={fadeUpVariants}
            initial="hidden"
            animate={isInView ? "visible" : "hidden"}
            transition={{ delay, duration: 0.8 }}
            className={className}
        >
            {children}
        </motion.div>
    );
};

export default function AboutPage() {
    const { data: session } = useSession();


    // [Parallax Scroll Logic]
    const { scrollY } = useScroll();
    const y1 = useTransform(scrollY, [0, 1000], [0, 200]);   // "SCENT" moves slightly down
    const y2 = useTransform(scrollY, [0, 1000], [0, -100]);  // "SENTENCE." moves slightly up

    return (
        <PageLayout className="min-h-screen bg-[#FDFBF8] text-black font-sans relative selection:bg-black selection:text-white overflow-x-hidden">

            <main>
                {/* [HERO SECTION - CINEMATIC REVEAL] */}
                <section className="h-screen flex flex-col justify-center px-6 md:px-10 pt-20 overflow-hidden relative">
                    <div className="max-w-[1920px] mx-auto w-full">
                        <motion.div
                            className="flex flex-col leading-[0.8]"
                            variants={containerVariants}
                            initial="hidden"
                            animate="show"
                        >
                            {/* SCENT */}
                            <div className="overflow-hidden">
                                <motion.span
                                    className="block text-[13vw] md:text-[14vw] font-black tracking-tighter text-[#111]"
                                    variants={textRevealVariants}
                                    style={{ y: y1 }} // Parallax Effect
                                >
                                    SCENT
                                </motion.span>
                            </div>

                            {/* AS A */}
                            <div className="overflow-hidden self-start md:self-center pl-2 md:pl-0">
                                <motion.span
                                    className="block text-[4vw] md:text-[3vw] font-serif italic text-gray-500 font-light tracking-wide my-2 md:my-4"
                                    variants={textRevealVariants}
                                >
                                    ( as a )
                                </motion.span>
                            </div>

                            {/* SENTENCE */}
                            <div className="overflow-hidden self-end">
                                <motion.span
                                    className="block text-[13vw] md:text-[14vw] font-black tracking-tighter text-[#111] text-right"
                                    variants={textRevealVariants}
                                    style={{ y: y2 }} // Parallax Effect
                                >
                                    SENTENCE.
                                </motion.span>
                            </div>
                        </motion.div>

                        <AnimateOnScroll delay={0.8} className="mt-12 md:mt-24 flex justify-between items-end">
                            <span className="hidden md:block text-xs font-bold uppercase tracking-[0.2em] text-[#C5A55D]">
                                Scroll to Explore
                            </span>
                            <p className="text-sm md:text-lg font-medium text-gray-500 max-w-md text-right leading-relaxed">
                                우리는 보이지 않는 향기를<br />
                                읽을 수 있는 언어로 번역합니다.
                            </p>
                        </AnimateOnScroll>
                    </div>
                </section>

                {/* [PHILOSOPHY SECTION] */}
                <section className="py-32 px-6 md:px-20 border-t border-gray-200">
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-20">
                        <div className="space-y-12">
                            <AnimateOnScroll>
                                <h2 className="text-xs font-bold uppercase tracking-[0.2em] text-[#C5A55D] mb-8">Our Philosophy</h2>
                            </AnimateOnScroll>
                            <AnimateOnScroll delay={0.1}>
                                <h3 className="text-3xl md:text-4xl font-bold text-[#222] mb-6 leading-tight">
                                    데이터로 <br />
                                    취향을 조각하다.
                                </h3>
                                <p className="text-gray-600 leading-relaxed text-justify">
                                    향수는 단순한 기호품이 아닙니다. 그것은 개인의 정체성이자, 기억을 불러일으키는 매개체입니다.
                                    5S Company는 인공지능 기술을 통해 수많은 향료(Notes)와 감성 키워드 사이의 연결 고리를 발견했습니다.
                                    우리는 당신의 모호한 취향을 명확한 데이터로 시각화하고, 가장 완벽한 향기를 제안합니다.
                                </p>
                            </AnimateOnScroll>
                        </div>
                        <div className="flex flex-col justify-end space-y-12 md:pl-20">
                            <AnimateOnScroll delay={0.2}>
                                <h3 className="text-3xl md:text-4xl font-bold text-[#222] mb-6 leading-tight">
                                    경계를 허무는 <br />
                                    공감각적 경험.
                                </h3>
                                <p className="text-gray-600 leading-relaxed text-justify">
                                    우리는 '향기'를 '문장'으로, '감정'을 '색채'로 변환하는 공감각적 실험을 지속합니다.
                                    Perfume Network Map은 향수 간의 관계를 우주처럼 펼쳐 보이며,
                                    당신이 미처 알지 못했던 새로운 취향의 영역으로 안내합니다.
                                </p>
                            </AnimateOnScroll>
                        </div>
                    </div>
                </section>

                {/* [TEAM SECTION - Minimal List] */}
                <section className="py-32 px-6 md:px-20 bg-[#f4f1ea] border-t border-gray-200">
                    <div className="max-w-6xl mx-auto">
                        <AnimateOnScroll>
                            <h2 className="text-xs font-bold uppercase tracking-[0.2em] text-[#999] mb-20 text-center">TEAM. 5S</h2>
                        </AnimateOnScroll>

                        <div className="divide-y divide-gray-300">
                            {[
                                { id: "01", name: "NAME HERE", role: "Founder / CEO", desc: "Vision & Strategy" },
                                { id: "02", name: "NAME HERE", role: "Lead Developer", desc: "System Architecture" },
                                { id: "03", name: "NAME HERE", role: "Product Manager", desc: "User Experience" },
                                { id: "04", name: "NAME HERE", role: "Data Scientist", desc: "AI / Recommendation Logic" },
                                { id: "05", name: "NAME HERE", role: "Brand Designer", desc: "Visual Identity" },
                            ].map((member, idx) => (
                                <AnimateOnScroll key={idx} delay={idx * 0.1}>
                                    <div className="group py-12 flex flex-col md:flex-row md:items-center justify-between hover:bg-[#ebe7de] transition-colors -mx-6 px-6 cursor-default">
                                        <div className="flex items-baseline gap-8 mb-4 md:mb-0">
                                            <span className="text-xs font-mono text-[#C5A55D]">{member.id}</span>
                                            <h3 className="text-3xl md:text-5xl font-bold text-[#222] group-hover:translate-x-4 transition-transform duration-500">{member.name}</h3>
                                        </div>
                                        <div className="flex flex-col md:items-end text-left md:text-right">
                                            <span className="text-sm font-bold text-black uppercase tracking-wider mb-1">{member.role}</span>
                                            <span className="text-xs text-gray-500 font-medium">{member.desc}</span>
                                        </div>
                                    </div>
                                </AnimateOnScroll>
                            ))}
                        </div>
                    </div>
                </section>

                {/* [CONTACT CTA & FOOTER] */}
                <section className="py-24 px-6 text-center bg-black text-white relative overflow-hidden flex flex-col items-center justify-center">
                    {/* Background Noise/Gradient placeholder */}
                    <div className="absolute inset-0 bg-[radial-gradient(circle_at_center,_var(--tw-gradient-stops))] from-gray-800 to-black opacity-50"></div>

                    <div className="relative z-10 flex flex-col items-center w-full max-w-4xl">
                        <AnimateOnScroll>
                            <h2 className="text-5xl md:text-7xl font-black mb-12 tracking-tighter">
                                Let's Make <br />
                                New Scentence.
                            </h2>
                        </AnimateOnScroll>

                        <AnimateOnScroll delay={0.2}>
                            <Link href="/contact" className="inline-block px-10 py-4 border border-white/30 rounded-full text-sm font-bold uppercase tracking-widest hover:bg-white hover:text-black transition-all duration-300 mb-20">
                                Contact Us
                            </Link>
                        </AnimateOnScroll>

                        {/* [New Footer Logo Area] */}
                        <AnimateOnScroll delay={0.4} className="flex flex-col items-center opacity-50 hover:opacity-100 transition-opacity duration-500">
                            <div className="flex items-center gap-2 mb-2">
                                <span className="text-xs font-medium tracking-widest text-[#888]">TEAM.</span>
                                {/* Permanently Skewed Logo with CSS transform removed */}
                                <img
                                    src="/images/5s_logo_skewed.png"
                                    alt="5S Logo"
                                    className="w-8 h-8 object-contain hover:scale-110 transition-transform duration-300"
                                />
                            </div>
                        </AnimateOnScroll>
                    </div>
                </section>
            </main>
        </PageLayout>
    );
}