"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { motion, useScroll, useTransform, useSpring, useInView, AnimatePresence, wrap } from "framer-motion";
import Sidebar from "@/components/common/sidebar";
import Header from "@/components/common/Header";
import UserProfileMenu from "@/components/common/UserProfileMenu"; // New import

export default function LandingPage() {
  const router = useRouter();
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);
  const [isProfileMenuOpen, setIsProfileMenuOpen] = useState(false); // New state
  // localAuth 제거: 랜딩 페이지는 세션 의존 로직 없음

  // Hydration Fix
  const [mounted, setMounted] = useState(false);
  useEffect(() => {
    setMounted(true);
  }, []);


  if (!mounted) return null; // Prevent hydration errors


  return (
    <div className="bg-[#FDFBF8] text-[#1a1a1a] font-sans selection:bg-[#FF6B6B] selection:text-white h-[100dvh] overflow-y-scroll snap-y snap-mandatory md:h-auto md:overflow-visible md:snap-none scroll-smooth">
      <Sidebar isOpen={isSidebarOpen} onClose={() => setIsSidebarOpen(false)} context="home" />

      {/* Profile Menu lifted out of Header */}
      <UserProfileMenu
        isOpen={isProfileMenuOpen}
        onClose={() => setIsProfileMenuOpen(false)}
      />

      <Header
        onToggleSidebar={() => {
          if (!isSidebarOpen) setIsProfileMenuOpen(false);
          setIsSidebarOpen(!isSidebarOpen);
        }}
        isSidebarOpen={isSidebarOpen}
        onToggleProfile={() => {
          if (!isProfileMenuOpen) setIsSidebarOpen(false);
          setIsProfileMenuOpen(!isProfileMenuOpen);
        }}
        isProfileMenuOpen={isProfileMenuOpen}
        showGreeting={true}
        isTransparent={true}
        theme="light"
        className="!shadow-none"
      />

      <main className="w-full">
        <HeroSection />
        <LayeringSection />
        <ArchiveGalaxySection />
        <NetworkSection />
        <WikiSection />
        <BrandStorySection />
        <FooterSection />
      </main>
    </div>
  );
}

// --- 1. HERO: The Atmosphere (Capsula Style with Draggable Carousel) ---
const HERO_IMAGES = [
  "/hero_1.png", // Flowers
  "/hero_2.png", // Rainy City
  "/hero_3.png", // Metasequoia
  "/hero_4.png", // Library
  "/hero_5.png", // Ocean
];

const variants = {
  enter: (direction: number) => {
    return {
      x: direction > 0 ? 1000 : -1000,
      opacity: 0
    };
  },
  center: {
    zIndex: 1,
    x: 0,
    opacity: 1
  },
  exit: (direction: number) => {
    return {
      zIndex: 0,
      x: direction < 0 ? 1000 : -1000,
      opacity: 0
    };
  }
};

const swipeConfidenceThreshold = 10000;
const swipePower = (offset: number, velocity: number) => {
  return Math.abs(offset) * velocity;
};

function HeroSection() {
  const { scrollY } = useScroll();
  const router = useRouter();

  const [[page, direction], setPage] = useState([0, 0]);
  const imageIndex = wrap(0, HERO_IMAGES.length, page);

  const paginate = useCallback((newDirection: number) => {
    setPage([page + newDirection, newDirection]);
  }, [page]);

  useEffect(() => {
    const interval = setInterval(() => {
      paginate(1);
    }, 5000);
    return () => clearInterval(interval);
  }, [paginate]);

  const imageY = useTransform(scrollY, [0, 800], [0, 100]);
  const stickerY_1 = useTransform(scrollY, [0, 800], [0, -150]);
  const stickerY_2 = useTransform(scrollY, [0, 800], [0, -80]);
  const stickerY_3 = useTransform(scrollY, [0, 800], [0, -200]);

  return (
    <section className="relative h-[100dvh] md:min-h-screen w-full flex items-center justify-center bg-[#FDFBF8] md:pt-0 md:pb-0 overflow-hidden snap-start snap-always">
      <div className="container mx-auto px-10 grid md:grid-cols-2 gap-8 md:gap-24 items-center h-full">

        {/* LEFT: Text Content */}
        <div className="relative z-10 flex flex-col items-start text-left space-y-3 md:space-y-8 order-2 md:order-1 mb-10 md:mb-0">
          <motion.div
            initial={{ scale: 0 }} animate={{ scale: 1 }} transition={{ duration: 0.5 }}
            className="w-3 h-3 md:w-6 md:h-6 rounded-full bg-[#FF6B6B]"
          />
          <h1 className="text-4xl md:text-8xl font-sans font-bold tracking-tighter text-[#1a1a1a] leading-[0.9]">
            FIND <br /> YOUR <br /> SIGNATURE.
          </h1>
          <p className="text-sm md:text-xl text-[#555] font-medium max-w-md">
            {/* 당신의 언어는 향기가 된다. <br /> */}
            향기로 기억되는 순간. <br />
            당신의 분위기를 완성하는 향수를 찾아보세요.
          </p>
          <motion.button
            onClick={() => router.push('/chat')}
            initial="initial"
            whileHover="hover"
            className="group relative px-6 py-3 md:px-8 md:py-4 rounded-[2rem] border-2 border-[#1a1a1a] text-[#1a1a1a] bg-transparent hover:bg-[#1a1a1a] hover:text-white transition-all text-xs md:text-sm font-bold uppercase tracking-widest overflow-hidden"
          >
            <span className="relative z-10 block group-hover:hidden">AI 향수 추천</span>
            <span className="relative z-10 hidden group-hover:block">START JOURNEY</span>
          </motion.button>
        </div>

        {/* RIGHT: Image Carousel & Stickers */}
        <div className="relative h-[38vh] md:h-[80vh] w-full order-1 md:order-2 flex items-center justify-center mt-12 md:mt-0">
          <motion.div
            style={{ y: imageY }}
            initial={{ opacity: 0, scale: 0.9, borderRadius: "100%" }}
            animate={{ opacity: 1, scale: 1, borderRadius: "3rem" }}
            transition={{ duration: 1.2, ease: "easeOut" }}
            className="w-full h-full max-h-[800px] overflow-hidden relative shadow-2xl z-10 flex items-center justify-center bg-gray-100 cursor-grab active:cursor-grabbing"
          >
            <AnimatePresence initial={false} custom={direction} mode="popLayout">
              <motion.img
                key={page}
                src={HERO_IMAGES[imageIndex]}
                custom={direction}
                variants={variants}
                initial="enter"
                animate="center"
                exit="exit"
                transition={{
                  x: { type: "spring", stiffness: 300, damping: 30 },
                  opacity: { duration: 0.2 }
                }}
                drag="x"
                dragConstraints={{ left: 0, right: 0 }}
                dragElastic={1}
                onDragEnd={(e, { offset, velocity }) => {
                  const swipe = swipePower(offset.x, velocity.x);
                  if (swipe < -swipeConfidenceThreshold) paginate(1);
                  else if (swipe > swipeConfidenceThreshold) paginate(-1);
                }}
                className={`absolute inset-0 w-full h-full object-cover ${imageIndex === 4 ? 'scale-105' : ''}`}
                draggable={false}
              />
            </AnimatePresence>
          </motion.div>

          {/* Floating Stickers */}
          <motion.div
            style={{ y: stickerY_1, rotate: -12 }}
            initial={{ opacity: 0, x: -100 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: 0.5, type: "spring" }}
            className="absolute top-[5%] md:top-[10%] left-[-5%] md:left-[-15%] bg-[#FF8F8F] text-[#1a1a1a] px-3 py-1 md:px-10 md:py-6 rounded-full shadow-[0_10px_30px_rgba(255,143,143,0.4)] z-20 border-2 border-[#1a1a1a]"
          >
            <span className="text-[10px] md:text-4xl font-bold tracking-tight font-sans">ATMOSPHERE</span>
          </motion.div>
          <motion.div
            style={{ y: stickerY_2, rotate: 8 }}
            initial={{ opacity: 0, x: 100 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: 0.7, type: "spring" }}
            className="absolute bottom-[20%] md:bottom-[30%] right-[-5%] md:right-[-12%] bg-[#FFAB76] text-[#1a1a1a] px-3 py-1 md:px-10 md:py-6 rounded-full shadow-[0_10px_30px_rgba(255,171,118,0.4)] z-20 border-2 border-[#1a1a1a]"
          >
            <span className="text-[10px] md:text-4xl font-bold tracking-tight font-sans">EMOTIONS</span>
          </motion.div>
          <motion.div
            style={{ y: stickerY_3, rotate: -5 }}
            initial={{ opacity: 0, y: 100 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.9, type: "spring" }}
            className="absolute bottom-[-5%] md:bottom-[5%] left-[10%] md:left-[0%] bg-[#FFCB74] text-[#1a1a1a] px-3 py-1.5 md:px-12 md:py-5 rounded-full shadow-[0_10px_30px_rgba(255,203,116,0.4)] z-20 border-2 border-[#1a1a1a]"
          >
            <span className="text-[10px] md:text-3xl font-bold tracking-tight font-sans">& MEMORIES</span>
          </motion.div>
        </div>
      </div>
    </section>
  );
}

// --- 2. ABOUT: Brand Story (The Invisible Language) ---
function BrandStorySection() {
  const router = useRouter();
  const ref = useRef(null);
  const isInView = useInView(ref, { margin: "-20% 0px -20% 0px" });

  return (
    <section ref={ref} className="relative h-[100dvh] md:min-h-[80vh] flex items-center justify-center bg-[#FDFBF8] py-0 md:py-24 overflow-hidden snap-start snap-always">
      <div className="container mx-auto px-10 grid md:grid-cols-2 gap-4 md:gap-24 items-center">

        {/* Visual: Abstract AI with Stickers */}
        <div className="relative order-1 md:order-1 flex justify-center mt-0 md:mt-0">
          <motion.div
            initial={{ opacity: 0, scale: 0.8, borderRadius: "50%" }}
            whileInView={{ opacity: 1, scale: 1, borderRadius: "3rem" }}
            viewport={{ once: true }}
            transition={{ duration: 1 }}
            className="w-full max-w-[300px] md:max-w-[700px] aspect-video overflow-hidden shadow-2xl relative bg-[#EAD7A1] hover:scale-105 transition-transform duration-500 ease-out"
          >
            <img src="/team_5s.png" alt="Scentence Philosophy" className="w-full h-full object-cover opacity-90" />
          </motion.div>

          {/* Sticker: PHILOSOPHY */}
          <motion.div
            initial={{ scale: 0, rotate: -15 }}
            whileInView={{ scale: 1, rotate: -15 }}
            transition={{ delay: 0.3, type: "spring" }}
            className="absolute top-[-5%] right-[-5%] bg-[#A8E6CF] text-[#1a1a1a] px-4 py-2 md:px-8 md:py-4 rounded-full border-2 border-[#1a1a1a] shadow-lg z-20"
          >
            <span className="text-sm md:text-2xl font-bold font-sans">PHILOSOPHY</span>
          </motion.div>
          {/* Sticker: NARRATIVE */}
          <motion.div
            initial={{ scale: 0, rotate: 10 }}
            whileInView={{ scale: 1, rotate: 10 }}
            transition={{ delay: 0.5, type: "spring" }}
            className="absolute bottom-[10%] left-[-10%] bg-[#FDFFAB] text-[#1a1a1a] px-4 py-2 md:px-8 md:py-4 rounded-full border-2 border-[#1a1a1a] shadow-lg z-20"
          >
            <span className="text-sm md:text-2xl font-bold font-sans">NARRATIVE</span>
          </motion.div>
        </div>

        {/* Text Content */}
        <motion.div
          initial={{ opacity: 0, x: -50 }}
          whileInView={{ opacity: 1, x: 0 }}
          transition={{ duration: 0.8 }}
          className="flex flex-col items-start text-left space-y-4 md:space-y-8 order-2 md:order-2"
        >
          <div className="w-4 h-4 rounded-full bg-[#C3AED6] shadow-[0_0_15px_rgba(195,174,214,0.5)]" />
          <h2 className="text-4xl md:text-7xl font-sans font-bold tracking-tighter text-[#1a1a1a] leading-[0.9]">
            ABOUT <br /> SCENTENCE.
          </h2>
          <p className="text-base md:text-lg text-[#555] font-medium max-w-sm">
            향기는 보이지 않는 언어입니다. <br />
            SCENTENCE는 당신의 언어를 <br />향기로 번역합니다.
          </p>
          <div className="flex gap-4">
            <motion.button
              onClick={() => router.push('/about')}
              initial="initial"
              whileHover="hover"
              className="group relative px-6 py-3 md:px-8 md:py-3 rounded-full border-2 border-[#1a1a1a] text-[#1a1a1a] bg-transparent hover:bg-[#1a1a1a] hover:text-white transition-all text-xs md:text-sm font-bold uppercase tracking-wide overflow-hidden"
            >
              <span className="relative z-10 block group-hover:hidden">TEAM. 5S 소개</span>
              <span className="relative z-10 hidden group-hover:block">ABOUT SCENTENCE</span>
            </motion.button>
          </div>
        </motion.div>
      </div>
    </section>
  );
}

// --- 3. LAYERING LAB: The Alchemist (Unified Design) ---
function LayeringSection() {
  const router = useRouter();
  const ref = useRef(null);

  return (
    <section ref={ref} className="relative h-[100dvh] md:min-h-[80vh] flex items-center justify-center bg-[#FDFBF8] py-0 md:py-24 overflow-hidden border-t border-gray-100 snap-start snap-always">
      <div className="container mx-auto px-10 grid md:grid-cols-2 gap-4 md:gap-24 items-center">

        {/* Visual */}
        <div className="relative order-1 md:order-1 flex justify-center mt-0 md:mt-0">
          <motion.div
            initial={{ opacity: 0, scale: 0.8 }}
            whileInView={{ opacity: 1, scale: 1 }}
            transition={{ duration: 1 }}
            className="w-full max-w-[280px] md:max-w-[500px] aspect-[4/5] rounded-[2.5rem] md:rounded-[3rem] overflow-hidden shadow-2xl relative border-2 border-[#1a1a1a]"
          >
            <img src="/section_layering.png" alt="Layering Lab" className="w-full h-full object-cover hover:scale-110 transition-transform duration-700" />
          </motion.div>

          {/* Stickers */}
          <motion.div
            initial={{ scale: 0, rotate: 5 }}
            whileInView={{ scale: 1, rotate: 5 }}
            transition={{ delay: 0.3, type: "spring" }}
            className="absolute top-[10%] left-[-5%] bg-[#FFD3B6] text-[#1a1a1a] px-3 py-1.5 md:px-6 md:py-3 rounded-full border-2 border-[#1a1a1a] shadow-lg z-20"
          >
            <span className="text-[10px] md:text-xl font-bold font-sans">ALCHEMY</span>
          </motion.div>
          <motion.div
            initial={{ scale: 0, rotate: -8 }}
            whileInView={{ scale: 1, rotate: -8 }}
            transition={{ delay: 0.5, type: "spring" }}
            className="absolute bottom-[-2%] right-[5%] bg-[#D4F0F0] text-[#1a1a1a] px-3 py-1.5 md:px-6 md:py-3 rounded-full border-2 border-[#1a1a1a] shadow-lg z-20"
          >
            <span className="text-[10px] md:text-xl font-bold font-sans">UNIQUE</span>
          </motion.div>
        </div>

        {/* Text Content */}
        <motion.div
          initial={{ opacity: 0, x: 50 }}
          whileInView={{ opacity: 1, x: 0 }}
          transition={{ duration: 0.8 }}
          className="flex flex-col items-start text-left space-y-2 md:space-y-8 order-2 md:order-2"
        >
          <div className="w-3 h-3 md:w-4 md:h-4 rounded-full bg-[#FFCB74] shadow-[0_0_15px_rgba(255,203,116,0.5)]" />
          <h2 className="text-3xl md:text-7xl font-sans font-bold tracking-tighter text-[#1a1a1a] leading-[0.9]">
            SCENT <br /> MIXOLOGY.
          </h2>
          <p className="text-sm md:text-lg text-[#555] font-medium max-w-sm">
            A + B = ∞ <br />
            서로 다른 노트를 섞어 만드는 나만의 무드.
          </p>
          <motion.button
            onClick={() => router.push('/layering')}
            initial="initial"
            whileHover="hover"
            className="group relative px-6 py-2.5 md:px-8 md:py-3 rounded-full border-2 border-[#1a1a1a] text-[#1a1a1a] bg-transparent hover:bg-[#1a1a1a] hover:text-white transition-all text-xs md:text-sm font-bold uppercase tracking-wide overflow-hidden"
          >
            <span className="relative z-10 block group-hover:hidden">레이어링 랩</span>
            <span className="relative z-10 hidden group-hover:block">GO TO LAYERING</span>
          </motion.button>
        </motion.div>

      </div>
    </section>
  );
}

// --- 4. ARCHIVE & GALAXY: The Universe (Unified Dark Mode Card) ---
function ArchiveGalaxySection() {
  const router = useRouter();
  return (
    <section className="relative h-[100dvh] md:min-h-[90vh] bg-[#FDFBF8] flex items-center justify-center py-0 md:py-20 snap-start snap-always">
      {/* Dark Mode Card Container */}
      <div className="container mx-auto px-10 h-full flex items-center">
        <div className="w-full bg-[#1a1a1a] rounded-[2rem] md:rounded-[3rem] p-8 md:p-20 relative overflow-hidden text-white shadow-2xl flex flex-col md:block items-center justify-center min-h-[60vh] md:min-h-0">
          {/* Background */}
          <div className="absolute inset-0 z-0 opacity-60">
            <img src="/section_archive.png" alt="Galaxy" className="w-full h-full object-cover" />
          </div>

          <div className="relative z-10 grid md:grid-cols-2 gap-8 md:gap-12 items-center w-full">
            <div className="space-y-4 md:space-y-8 flex flex-col items-center md:items-start text-center md:text-left">
              <span className="text-[#A8E6CF] font-bold tracking-widest uppercase bg-white/10 px-4 py-1 rounded-full text-[10px] md:text-xs">Private Collection</span>
              <h2 className="text-4xl md:text-7xl font-sans font-bold tracking-tighter leading-[0.9]">
                YOUR <br /> ARCHIVE.
              </h2>
              <p className="text-white/70 text-base md:text-lg font-medium max-w-sm">
                당신이 수집한 향기들. <br />
                나만의 보관함에서 당신만의 향수를 만나보세요.
              </p>
              <motion.button
                onClick={() => router.push('/archives')}
                initial="initial"
                whileHover="hover"
                className="group relative px-6 py-3 md:px-8 md:py-3 rounded-full border-2 border-white/20 bg-white text-[#1a1a1a] hover:bg-[#1a1a1a] hover:text-white hover:border-[#1a1a1a] transition-all text-xs md:text-sm font-bold uppercase tracking-wide overflow-hidden shadow-lg"
              >
                <span className="relative z-10 block group-hover:hidden">나만의 보관함</span>
                <span className="relative z-10 hidden group-hover:block">MY COLLECTION</span>
              </motion.button>
            </div>

            {/* Visual: Spinning Galaxy */}
            <div className="relative flex justify-center items-center mt-4 md:mt-0">
              <motion.div
                animate={{ rotate: 360 }}
                transition={{ repeat: Infinity, duration: 60, ease: "linear" }}
                className="w-[200px] h-[200px] md:w-[450px] md:h-[450px] relative"
              >
                {/* Image Mask - Rotates with parent, clips scaled image */}
                <div className="w-full h-full rounded-full overflow-hidden border-4 border-white/20">
                  <img src="/section_archive.png" className="w-full h-full object-cover scale-150" alt="Galaxy Planet" />
                </div>

                {/* Orbit Sticker - Rotates with parent (orbit) & Counter-rotates (stay upright) + Bounce */}
                <motion.div
                  className="absolute top-0 left-[50%] -translate-x-1/2 -translate-y-1/2 bg-[#FF6B6B] text-[#1a1a1a] px-3 py-1 md:px-4 md:py-2 rounded-full font-bold text-[10px] md:text-xs shadow-lg z-20"
                  animate={{ rotate: -360, scale: [1, 1.1, 1] }}
                  transition={{
                    rotate: { repeat: Infinity, duration: 60, ease: "linear" },
                    scale: { repeat: Infinity, duration: 2, ease: "easeInOut" }
                  }}
                >
                  COLLECTION
                </motion.div>
              </motion.div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}

// --- 5. PERFUME NETWORK & WIKI: Unified Design ---
function NetworkSection() {
  const router = useRouter();
  return (
    <section className="relative h-[100dvh] md:min-h-[80vh] bg-[#FDFBF8] py-0 md:py-24 flex items-center snap-start snap-always">
      <div className="container mx-auto px-10 grid md:grid-cols-2 gap-8 md:gap-24 items-center h-full">
        {/* Text */}
        <div className="order-1 md:order-1 space-y-4 md:space-y-6 flex flex-col items-center md:items-start text-center md:text-left">
          <div className="w-4 h-4 rounded-full bg-[#A8E6CF] shadow-[0_0_15px_rgba(168,230,207,0.5)]" />
          <h2 className="text-5xl md:text-7xl font-sans font-bold tracking-tighter text-[#1a1a1a] leading-[0.9]">
            SCENT <br /> MAPPING.
          </h2>
          <p className="text-base md:text-lg text-[#555] font-medium">
            향수 데이터의 거대한 연결망. <br />
            노트와 브랜드의 관계를 시각적으로 탐험하세요.
          </p>
          <motion.button
            onClick={() => router.push('/perfume-network/nmap')}
            initial="initial"
            whileHover="hover"
            className="group relative px-6 py-3 md:px-8 md:py-3 rounded-full border-2 border-[#1a1a1a] text-[#1a1a1a] bg-transparent hover:bg-[#1a1a1a] hover:text-white transition-all text-xs md:text-sm font-bold uppercase tracking-wide overflow-hidden"
          >
            <span className="relative z-10 block group-hover:hidden">향수 지도</span>
            <span className="relative z-10 hidden group-hover:block">PERFUME NETWORK</span>
          </motion.button>
        </div>

        {/* Visual */}
        <div className="relative order-2 md:order-2 flex justify-center">
          <motion.div
            whileHover={{ scale: 1.02 }}
            className="w-full aspect-video rounded-[3rem] overflow-hidden border-2 border-[#1a1a1a] bg-black relative group cursor-pointer"
            onClick={() => router.push('/perfume-network/nmap')}
          >
            <img src="/section_network.png" alt="Network" className="w-full h-full object-cover opacity-80" />
          </motion.div>

          {/* Stickers */}
          <motion.div
            className="absolute -top-6 -left-6 bg-[#FFAA1D] text-[#1a1a1a] px-4 py-2 md:px-6 md:py-3 rounded-full border-2 border-[#1a1a1a] z-20 font-bold transform -rotate-6 text-xs md:text-base"
            whileInView={{ scale: [0, 1] }}
          >
            PERFUME NETWORK
          </motion.div>
        </div>
      </div>
    </section>
  );
}

function WikiSection() {
  const router = useRouter();
  return (
    <section className="relative h-[100dvh] md:min-h-[60vh] bg-[#FDFBF8] py-0 md:py-24 flex items-center border-t border-gray-100 snap-start snap-always">
      <div className="container mx-auto px-10 flex flex-col items-center text-center space-y-8">
        <motion.div
          initial={{ scale: 0.9, opacity: 0 }}
          whileInView={{ scale: 1, opacity: 1 }}
          className="relative w-full max-w-4xl aspect-[4/3] md:aspect-[3/1] rounded-[3rem] overflow-hidden border-2 border-[#1a1a1a]"
        >
          <img src="/section_wiki.png" alt="Library" className="w-full h-full object-cover" />
          <div className="absolute inset-0 bg-black/40 flex flex-col items-center justify-center text-white p-8">
            <h2 className="text-4xl md:text-7xl font-sans font-bold tracking-tighter leading-[0.9] mb-4">
              KNOWLEDGE BASE.
            </h2>
            <motion.button
              onClick={() => router.push('/perfume-wiki')}
              initial="initial"
              whileHover="hover"
              className="group relative px-6 py-3 md:px-8 md:py-3 rounded-full border-2 border-[#1a1a1a] bg-[#FF6B6B] text-[#1a1a1a] hover:bg-white transition-all text-xs md:text-sm font-bold uppercase tracking-wide overflow-hidden shadow-md"
            >
              <span className="relative z-10 block group-hover:hidden">향수 백과</span>
              <span className="relative z-10 hidden group-hover:block">VISIT PERFUME WIKI</span>
            </motion.button>
          </div>
        </motion.div>
      </div>
    </section>
  );
}

// --- 7. FOOTER ---
function FooterSection() {
  return (
    <footer className="bg-[#1a1a1a] text-white/50 text-xs py-12 md:py-24 text-center snap-start snap-always flex flex-col justify-center h-[50dvh] md:h-auto">
      <p className="mb-6 tracking-widest uppercase">© 2026 SCENTENCE.</p>
      <div className="flex flex-col items-center gap-4">
        <div className="flex items-center gap-3 opacity-60 hover:opacity-100 transition-opacity duration-300">
          <span className="text-[10px] font-bold tracking-[0.2em] text-[#888]">TEAM.</span>
          <img
            src="/images/5s_logo_skewed.png"
            alt="5S Logo"
            className="w-8 h-8 object-contain hover:scale-110 transition-transform duration-300"
          />
        </div>
      </div>
    </footer>
  )
}
