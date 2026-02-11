"use client";

import { useRef, useState, MouseEvent } from "react";
import { motion } from "framer-motion";

interface MagneticButtonProps {
    children?: React.ReactNode;
    onClick?: () => void;
    className?: string;
}

const MagneticButton = ({ children, onClick, className = "" }: MagneticButtonProps) => {
    const ref = useRef<HTMLDivElement>(null);
    const [position, setPosition] = useState({ x: 0, y: 0 });

    const handleMouse = (e: MouseEvent<HTMLDivElement>) => {
        const { clientX, clientY } = e;
        const { height, width, left, top } = ref.current?.getBoundingClientRect() || { height: 0, width: 0, left: 0, top: 0 };

        // 마우스 위치에 따라 버튼을 자석처럼 끌어당김 (강도 조절: 0.5)
        const middleX = clientX - (left + width / 2);
        const middleY = clientY - (top + height / 2);

        setPosition({ x: middleX * 0.5, y: middleY * 0.5 });
    };

    const reset = () => {
        setPosition({ x: 0, y: 0 });
    };

    const { x, y } = position;

    return (
        <motion.div
            ref={ref}
            onMouseMove={handleMouse}
            onMouseLeave={reset}
            animate={{ x, y }}
            transition={{ type: "spring", stiffness: 150, damping: 15, mass: 0.1 }}
            onClick={onClick}
            className={`relative cursor-pointer group ${className}`}
        >
            {/* 버튼 스타일: Lusion 직생 (블랙 pill 형태 + 그림자) */}
            <div className="relative flex items-center justify-center px-5 py-2.5 bg-black text-white rounded-full overflow-hidden transition-all duration-300 group-hover:scale-110 shadow-lg border border-transparent group-hover:border-white/20">
                <span className="relative z-10 text-xs font-bold tracking-[0.2em] uppercase pointer-events-none">
                    {children || "MENU"}
                </span>
            </div>
        </motion.div>
    );
};

export default MagneticButton;
