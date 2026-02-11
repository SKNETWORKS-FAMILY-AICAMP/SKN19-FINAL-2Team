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
        <PageLayout
            disableContentPadding={true}
            className="min-h-screen bg-[#FDFBF8] text-black font-sans relative selection:bg-black selection:text-white overflow-x-hidden flex flex-col"
        >

            <main className="flex-1 pt-[80px] md:pt-[100px] flex flex-col w-full">

                {/* [MARQUEE SECTION] */}
                <div className="py-12 md:py-20 overflow-hidden relative border-b border-gray-200 bg-white select-none">
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
                            <span className="text-6xl md:text-[10rem] font-black tracking-tighter text-transparent opacity-10 px-4 md:px-6" style={{ WebkitTextStroke: "1px black" }}>
                                GET IN TOUCH •
                            </span>
                            <span className="text-6xl md:text-[10rem] font-black tracking-tighter text-black px-4 md:px-6">
                                CONTACT US •
                            </span>
                            <span className="text-6xl md:text-[10rem] font-black tracking-tighter text-transparent opacity-10 px-4 md:px-6" style={{ WebkitTextStroke: "1px black" }}>
                                SCENTENCE •
                            </span>
                        </div>
                        {/* SECOND SET */}
                        <div className="flex items-center shrink-0">
                            <span className="text-6xl md:text-[10rem] font-black tracking-tighter text-transparent opacity-10 px-4 md:px-6" style={{ WebkitTextStroke: "1px black" }}>
                                GET IN TOUCH •
                            </span>
                            <span className="text-6xl md:text-[10rem] font-black tracking-tighter text-black px-4 md:px-6">
                                CONTACT US •
                            </span>
                            <span className="text-6xl md:text-[10rem] font-black tracking-tighter text-transparent opacity-10 px-4 md:px-6" style={{ WebkitTextStroke: "1px black" }}>
                                SCENTENCE •
                            </span>
                        </div>
                    </motion.div>
                </div>

                {/* [MAIN GRID] */}
                <div className="flex-1 grid grid-cols-1 lg:grid-cols-3 divide-y lg:divide-y-0 lg:divide-x divide-gray-200 border-b border-gray-200">

                    {/* Channel 1: Kakao */}
                    <div
                        className="group relative p-8 md:p-12 flex flex-col justify-between hover:bg-black hover:text-white transition-all duration-500 cursor-pointer min-h-[320px] md:min-h-[450px]"
                        onClick={() => window.open('https://pf.kakao.com/_Scentence', '_blank')}
                    >
                        <div className="flex justify-between items-start">
                            <span className="text-[10px] md:text-xs font-bold uppercase tracking-[0.2em] opacity-60">01 / Instant</span>
                            <span className="text-2xl md:text-3xl">💬</span>
                        </div>
                        <div>
                            <h3 className="text-3xl md:text-5xl font-black mb-4 group-hover:translate-x-2 transition-transform duration-500 uppercase tracking-tighter">Kakao Channel</h3>
                            <p className="text-xs md:text-sm font-medium opacity-60 mb-8 leading-relaxed">
                                가장 빠른 답변을 받아보세요.<br />
                                챗봇 상담 및 실시간 문의가 가능합니다.
                            </p>
                            <span className="inline-block border-b border-black group-hover:border-white pb-1 text-[10px] md:text-xs font-black uppercase tracking-widest">
                                Visit Channel →
                            </span>
                        </div>
                    </div>

                    {/* Channel 2: Email */}
                    <div
                        className="group relative p-8 md:p-12 flex flex-col justify-between hover:bg-black hover:text-white transition-all duration-500 cursor-pointer min-h-[320px] md:min-h-[450px]"
                        onClick={() => handleCopy('5scompany@contact.com', 'email')}
                    >
                        <div className="flex justify-between items-start">
                            <span className="text-[10px] md:text-xs font-bold uppercase tracking-[0.2em] opacity-60">02 / Official</span>
                            <span className="text-2xl md:text-3xl">📧</span>
                        </div>
                        <div>
                            <h3 className="text-3xl md:text-5xl font-black mb-4 group-hover:translate-x-2 transition-transform duration-500 uppercase tracking-tighter">
                                {copied === 'email' ? 'Copied!' : 'Email Us'}
                            </h3>
                            <p className="text-xs md:text-sm font-medium opacity-60 mb-8 leading-relaxed">
                                비즈니스 제휴 및 기타 상세 문의.<br />
                                24시간 이내에 회신 드립니다.
                            </p>
                            <span className="inline-block border-b border-black group-hover:border-white pb-1 text-[10px] md:text-xs font-black uppercase tracking-widest font-mono">
                                5scompany@contact.com ❐
                            </span>
                        </div>
                    </div>

                    {/* Channel 3: Location */}
                    <div className="group relative p-8 md:p-12 flex flex-col justify-between hover:bg-black hover:text-white transition-all duration-500 cursor-pointer min-h-[320px] md:min-h-[450px]">
                        <div className="flex justify-between items-start">
                            <span className="text-[10px] md:text-xs font-bold uppercase tracking-[0.2em] opacity-60">03 / Visit</span>
                            <span className="text-2xl md:text-3xl">📍</span>
                        </div>
                        <div>
                            <h3 className="text-3xl md:text-5xl font-black mb-4 group-hover:translate-x-2 transition-transform duration-500 uppercase tracking-tighter">Office</h3>
                            <p className="text-xs md:text-sm font-medium opacity-60 mb-8 leading-relaxed">
                                서울특별시 마포구 연희로 1길 52 3F,<br />
                                5S Company
                            </p>
                            <span className="inline-block border-b border-black group-hover:border-white pb-1 text-[10px] md:text-xs font-black uppercase tracking-widest">
                                Open Map →
                            </span>
                        </div>
                    </div>
                </div>

                {/* [FOOTER with LOGO] */}
                <div className="py-24 flex flex-col items-center justify-center bg-white">
                    <div className="flex flex-col items-center gap-6 opacity-30 hover:opacity-100 transition-all duration-700">
                        <img
                            src="/images/5s_logo_skewed.png"
                            alt="5S Logo"
                            className="w-12 h-12 object-contain grayscale"
                        />
                        <span className="text-[10px] font-black tracking-[0.5em] text-black uppercase">Scentence Studio.</span>
                    </div>
                </div>
            </main>
        </PageLayout>
    );
}