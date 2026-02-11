'use client';

import { useState, useRef, useEffect } from "react";
import Link from "next/link";
import { useSession } from "next-auth/react";
import PageLayout from "@/components/common/PageLayout";
import { motion, useScroll, useTransform, useInView, Variants } from "framer-motion";

// [Animation Variants]
const containerVariants: Variants = {
    hidden: { opacity: 0 },
    show: {
        opacity: 1,
        transition: {
            staggerChildren: 0.15,
            delayChildren: 0.2,
        }
    }
};

const textRevealVariants: Variants = {
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

const fadeUpVariants: Variants = {
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
        <PageLayout
            disableContentPadding={true}
            className="min-h-screen bg-[#FDFBF8] text-black font-sans relative selection:bg-black selection:text-white overflow-x-hidden"
        >

            <main className="w-full">
                {/* [HERO SECTION - CINEMATIC REVEAL] */}
                <section className="h-[90vh] md:h-screen flex flex-col justify-center px-4 md:px-10 pt-16 md:pt-20 overflow-hidden relative">
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
                                    className="block text-[18vw] md:text-[14vw] font-black tracking-tighter text-[#111]"
                                    variants={textRevealVariants}
                                    style={{ y: y1 }}
                                >
                                    SCENT
                                </motion.span>
                            </div>

                            {/* AS A */}
                            <div className="overflow-hidden self-start md:self-center pl-2 md:pl-0">
                                <motion.span
                                    className="block text-[6vw] md:text-[3vw] font-serif italic text-gray-400 font-light tracking-wide my-4 md:my-4"
                                    variants={textRevealVariants}
                                >
                                    ( as a )
                                </motion.span>
                            </div>

                            {/* SENTENCE */}
                            <div className="overflow-hidden self-end">
                                <motion.span
                                    className="block text-[18vw] md:text-[14vw] font-black tracking-tighter text-[#111] text-right"
                                    variants={textRevealVariants}
                                    style={{ y: y2 }}
                                >
                                    SENTENCE.
                                </motion.span>
                            </div>
                        </motion.div>

                        <AnimateOnScroll delay={0.8} className="mt-16 md:mt-24 flex justify-between items-end">
                            <span className="hidden md:block text-[10px] font-black uppercase tracking-[0.3em] text-[#C5A55D]">
                                Scroll to Explore
                            </span>
                            <p className="text-xs md:text-lg font-medium text-gray-500 max-w-xs md:max-w-md text-right leading-relaxed">
                                우리는 보이지 않는 향기를<br />
                                읽을 수 있는 언어로 번역합니다.
                            </p>
                        </AnimateOnScroll>
                    </div>
                </section>

                {/* [PHILOSOPHY SECTION] */}
                <section className="py-24 md:py-32 px-6 md:px-20 border-t border-gray-200">
                    <div className="max-w-screen-2xl mx-auto grid grid-cols-1 md:grid-cols-2 gap-16 md:gap-20">
                        <div className="space-y-8 md:space-y-12">
                            <AnimateOnScroll>
                                <h2 className="text-[10px] md:text-xs font-black uppercase tracking-[0.3em] text-[#C5A55D] mb-6 md:mb-8">Our Philosophy</h2>
                            </AnimateOnScroll>
                            <AnimateOnScroll delay={0.1}>
                                <h3 className="text-3xl md:text-5xl font-black text-[#111] mb-6 leading-[1.1] tracking-tighter uppercase">
                                    데이터로 <br />
                                    취향을 조각하다.
                                </h3>
                                <p className="text-sm md:text-base text-gray-600 leading-relaxed text-justify font-medium">
                                    향수는 단순한 기호품이 아닙니다. 그것은 개인의 정체성이자, 기억을 불러일으키는 매개체입니다.
                                    5S Company는 인공지능 기술을 통해 수많은 향료(Notes)와 감성 키워드 사이의 연결 고리를 발견했습니다.
                                    우리는 당신의 모호한 취향을 명확한 데이터로 시각화하고, 가장 완벽한 향기를 제안합니다.
                                </p>
                            </AnimateOnScroll>
                        </div>
                        <div className="flex flex-col justify-end space-y-8 md:space-y-12 md:pl-20">
                            <AnimateOnScroll delay={0.2}>
                                <h3 className="text-3xl md:text-5xl font-black text-[#111] mb-6 leading-[1.1] tracking-tighter uppercase">
                                    경계를 허무는 <br />
                                    공감각적 경험.
                                </h3>
                                <p className="text-sm md:text-base text-gray-600 leading-relaxed text-justify font-medium">
                                    우리는 '향기'를 '문장'으로, '감정'을 '색채'로 변환하는 공감각적 실험을 지속합니다.
                                    Perfume Network Map은 향수 간의 관계를 우주처럼 펼쳐 보이며,
                                    당신이 미처 알지 못했던 새로운 취향의 영역으로 안내합니다.
                                </p>
                            </AnimateOnScroll>
                        </div>
                    </div>
                </section>

                {/* [TEAM SECTION - Minimal List] */}
                <section className="py-24 md:py-32 px-6 md:px-20 bg-[#f4f1ea] border-t border-gray-200">
                    <div className="max-w-screen-xl mx-auto">
                        <AnimateOnScroll>
                            <h2 className="text-[10px] md:text-xs font-black uppercase tracking-[0.5em] text-[#999] mb-16 md:mb-20 text-center">STUDIO. 5S</h2>
                        </AnimateOnScroll>

                        <div className="divide-y divide-gray-300">
                            {[
                                { id: "01", nameEn: "SHIN JI SEOP", nameKr: "신지섭", role: "BACKEND", desc: "PM / System Architecture" },
                                { id: "02", nameEn: "LEE SANG MIN", nameKr: "이상민", role: "BACKEND", desc: "Data Engineering" },
                                { id: "03", nameEn: "KIM JELLY", nameKr: "김젤리", role: "FRONTEND", desc: "UI/UX & Data Visualization" },
                                { id: "04", nameEn: "MA HAN SUNG", nameKr: "마한성", role: "BACKEND", desc: "Data Analytics & 발표자" },
                                { id: "05", nameEn: "KIM SUNG UK", nameKr: "김성욱", role: "FRONTEND", desc: "Frontend Development" },
                            ].map((member, idx) => (
                                <AnimateOnScroll key={idx} delay={idx * 0.1}>
                                    <div className="group py-8 md:py-12 flex flex-col md:flex-row md:items-center justify-between hover:bg-[#ebe7de] transition-all duration-500 -mx-6 px-6 cursor-default">
                                        <div className="flex items-baseline gap-4 md:gap-8 mb-4 md:mb-0">
                                            <span className="text-[10px] font-mono text-[#C5A55D] font-bold">{member.id}</span>
                                            <div className="flex items-baseline gap-4">
                                                <h3 className="text-2xl md:text-6xl font-black text-[#111] group-hover:translate-x-4 transition-transform duration-700 tracking-tighter uppercase">{member.nameEn}</h3>
                                                <span className="text-sm md:text-lg font-bold text-gray-400 opacity-60 group-hover:translate-x-4 transition-transform duration-700 delay-75">{member.nameKr}</span>
                                            </div>
                                        </div>
                                        <div className="flex flex-col md:items-end text-left md:text-right">
                                            <span className="text-xs md:text-sm font-black text-black uppercase tracking-widest mb-1">{member.role}</span>
                                            <span className="text-[10px] md:text-xs text-gray-500 font-bold uppercase tracking-tight">{member.desc}</span>
                                        </div>
                                    </div>
                                </AnimateOnScroll>
                            ))}
                        </div>
                    </div>
                </section>

                {/* [CONTACT CTA & FOOTER] */}
                <section className="py-32 px-6 text-center bg-black text-white relative overflow-hidden flex flex-col items-center justify-center">
                    <div className="absolute inset-0 bg-[radial-gradient(circle_at_center,_var(--tw-gradient-stops))] from-gray-900 to-black opacity-80"></div>

                    <div className="relative z-10 flex flex-col items-center w-full max-w-4xl">
                        <AnimateOnScroll>
                            <h2 className="text-4xl md:text-8xl font-black mb-12 tracking-tighter uppercase leading-[0.95]">
                                Let's Make <br />
                                New Scentence.
                            </h2>
                        </AnimateOnScroll>

                        <AnimateOnScroll delay={0.2}>
                            <motion.div whileHover={{ scale: 1.05 }} whileTap={{ scale: 0.95 }}>
                                <Link href="/contact" className="inline-block px-8 md:px-12 py-4 md:py-5 bg-white text-black rounded-full text-[10px] md:text-xs font-black uppercase tracking-[0.2em] shadow-2xl transition-all duration-300 mb-24 md:mb-32">
                                    Get in Touch
                                </Link>
                            </motion.div>
                        </AnimateOnScroll>

                        <AnimateOnScroll delay={0.4} className="flex flex-col items-center opacity-30 hover:opacity-100 transition-all duration-700">
                            <div className="flex flex-col items-center gap-6">
                                <img
                                    src="/images/5s_logo_skewed.png"
                                    alt="5S Logo"
                                    className="w-10 md:w-14 h-10 md:h-14 object-contain grayscale invert"
                                />
                                <span className="text-[10px] font-black tracking-[0.5em] text-white uppercase">Scentence Studio.</span>
                            </div>
                        </AnimateOnScroll>
                    </div>
                </section>
            </main>
        </PageLayout>
    );
}