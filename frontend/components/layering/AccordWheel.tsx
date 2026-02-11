"use client";

import { useState } from "react";
import { 
  ACCORD_COLORS, 
  ACCORD_LABELS, 
  ACCORD_DESCRIPTIONS, 
  BACKEND_ACCORDS, 
  DISPLAY_ACCORDS 
} from "@/lib/accords";

type AccordWheelProps = {
  vector: number[];
  size?: number;
};

type Point = {
  x: number;
  y: number;
};

// ==================== 상수 ====================

const DEFAULT_SIZE = 360;
const OUTER_RADIUS = 170;
const INNER_RADIUS_MAX = 135;
const INNER_RADIUS_MIN = 70;

const polarToCartesian = (cx: number, cy: number, radius: number, angle: number): Point => {
  const radians = ((angle - 90) * Math.PI) / 180;
  return {
    x: cx + radius * Math.cos(radians),
    y: cy + radius * Math.sin(radians),
  };
};

const arcPath = (
  cx: number,
  cy: number,
  startAngle: number,
  endAngle: number,
  innerRadius: number,
  outerRadius: number,
): string => {
  const startOuter = polarToCartesian(cx, cy, outerRadius, startAngle);
  const endOuter = polarToCartesian(cx, cy, outerRadius, endAngle);
  const startInner = polarToCartesian(cx, cy, innerRadius, endAngle);
  const endInner = polarToCartesian(cx, cy, innerRadius, startAngle);
  const largeArcFlag = endAngle - startAngle <= 180 ? "0" : "1";

  return [
    `M ${startOuter.x} ${startOuter.y}`,
    `A ${outerRadius} ${outerRadius} 0 ${largeArcFlag} 1 ${endOuter.x} ${endOuter.y}`,
    `L ${startInner.x} ${startInner.y}`,
    `A ${innerRadius} ${innerRadius} 0 ${largeArcFlag} 0 ${endInner.x} ${endInner.y}`,
    "Z",
  ].join(" ");
};

export default function AccordWheel({ vector, size = DEFAULT_SIZE }: AccordWheelProps) {
  // ==================== 상태 관리 ====================
  
  /** 현재 호버 중인 어코드 */
  const [hoveredAccord, setHoveredAccord] = useState<string | null>(null);
  
  /** 클릭으로 고정된 어코드 */
  const [pinnedAccord, setPinnedAccord] = useState<string | null>(null);
  
  // ==================== 데이터 준비 ====================
  
  const safeVector = Array.isArray(vector) ? vector : [];
  const maxValue = Math.max(...safeVector, 0);
  const viewBox = `0 0 ${size} ${size}`;
  const cx = size / 2;
  const cy = size / 2;
  const segmentAngle = 360 / DISPLAY_ACCORDS.length;
  const backendIndex = new Map(
    BACKEND_ACCORDS.map((accord, index) => [accord, index]),
  );

  // 표시할 어코드 정보 (고정된 것 우선, 없으면 호버된 것)
  const displayedAccord = pinnedAccord || hoveredAccord;
  
  // 어코드 정보
  const accordInfo = displayedAccord ? {
    accord: displayedAccord as (typeof BACKEND_ACCORDS)[number],
    koreanName: ACCORD_LABELS[displayedAccord] || displayedAccord,
    englishName: displayedAccord,
    description: ACCORD_DESCRIPTIONS[displayedAccord] || "",
    vectorIndex: backendIndex.get(displayedAccord as (typeof BACKEND_ACCORDS)[number]) ?? 0,
    rawValue: safeVector[backendIndex.get(displayedAccord as (typeof BACKEND_ACCORDS)[number]) ?? 0] ?? 0,
    percentage: maxValue > 0 
      ? Math.round((safeVector[backendIndex.get(displayedAccord as (typeof BACKEND_ACCORDS)[number]) ?? 0] ?? 0) / maxValue * 100)
      : 0,
    isPinned: displayedAccord === pinnedAccord,
  } : null;
  
  /**
   * 어코드 클릭 핸들러
   * - 같은 어코드 클릭 시: 고정 해제
   * - 다른 어코드 클릭 시: 해당 어코드 고정
   */
  const handleAccordClick = (accord: string) => {
    if (pinnedAccord === accord) {
      setPinnedAccord(null); // 고정 해제
    } else {
      setPinnedAccord(accord); // 고정
    }
  };

  return (
    <div className="relative w-full flex flex-col items-center gap-4">
      {/* ==================== SVG 원판 ==================== */}
      <div className="w-full max-w-[360px] aspect-square">
        <svg
          viewBox={viewBox}
          width="100%"
          height="100%"
          className="w-full h-full"
          aria-label="Accord wheel"
        >
        {DISPLAY_ACCORDS.map((accord, index) => {
          const vectorIndex = backendIndex.get(accord) ?? index;
          const rawValue = safeVector[vectorIndex] ?? 0;
          const normalized = maxValue > 0 ? Math.min(rawValue / maxValue, 1) : 0;
          const innerRadius =
            INNER_RADIUS_MAX - (INNER_RADIUS_MAX - INNER_RADIUS_MIN) * normalized;
          const opacity = 0.25 + normalized * 0.75;
          const startAngle = index * segmentAngle;
          const endAngle = startAngle + segmentAngle;
          const path = arcPath(cx, cy, startAngle, endAngle, innerRadius, OUTER_RADIUS);
          
          // 상태에 따른 스타일
          const isPinned = pinnedAccord === accord;
          const isHovered = hoveredAccord === accord;
          const isActive = isPinned || isHovered;
          
          const strokeWidth = isPinned ? 4 : (isHovered ? 3 : 2);
          const strokeColor = isPinned 
            ? "rgba(200, 162, 77, 1)" 
            : (isHovered ? "rgba(200, 162, 77, 0.8)" : "rgba(255,255,255,0.6)");

          return (
            <path
              key={accord}
              d={path}
              fill={ACCORD_COLORS[accord]}
              fillOpacity={opacity}
              stroke={strokeColor}
              strokeWidth={strokeWidth}
              onMouseEnter={() => !pinnedAccord && setHoveredAccord(accord)}
              onMouseLeave={() => !pinnedAccord && setHoveredAccord(null)}
              onClick={() => handleAccordClick(accord)}
              style={{ 
                cursor: "pointer",
                transition: "stroke-width 0.2s, stroke 0.2s",
              }}
              aria-label={`${ACCORD_LABELS[accord] || accord} 어코드`}
              role="button"
              tabIndex={0}
            />
          );
        })}
        
        {/* 중앙 원 */}
        <circle cx={cx} cy={cy} r={55} fill="#FDFDFB" stroke="#E4E0D4" />
        
        {/* 중앙 텍스트 */}
        <text
          x={cx}
          y={cy - 4}
          textAnchor="middle"
          fill="#2B2B2B"
          fontSize="16"
          fontWeight={600}
        >
          SCENTENCE
        </text>
        <text
          x={cx}
          y={cy + 16}
          textAnchor="middle"
          fill="#7B7B7B"
          fontSize="11"
          letterSpacing="0.12em"
        >
          ACCORDS
        </text>
        </svg>
      </div>

      {/* ==================== 툴팁 (호버/고정 정보) ==================== */}
      {accordInfo && (
        <div 
          className="w-full rounded-xl bg-gradient-to-br from-white to-[#FDFBF9] border-2 border-[#C8A24D] p-4 shadow-lg"
          role="tooltip"
        >
          {/* 어코드 이름과 상태 */}
          <div className="flex items-center justify-between mb-2">
            <div className="flex items-center gap-2">
              <span className="text-base font-bold text-[#2E2B28]">
                {accordInfo.koreanName}
              </span>
              <span className="text-xs text-[#7A6B57] font-medium">
                {accordInfo.englishName}
              </span>
            </div>
            {/* 비중 표시 */}
            <div className="flex items-center gap-1.5 bg-[#C8A24D]/10 px-2.5 py-1 rounded-lg border border-[#C8A24D]/30">
              <div 
                className="w-3 h-3 rounded-sm" 
                style={{ backgroundColor: ACCORD_COLORS[accordInfo.accord] }}
              />
              <span className="text-sm font-bold text-[#C8A24D]">
                {accordInfo.percentage}%
              </span>
            </div>
          </div>
          
          {/* 어코드 설명 */}
          <p className="text-xs text-[#5C5448] leading-relaxed mb-2">
            {accordInfo.description}
          </p>
          
          {/* 안내 문구 */}
          <p className="text-[10px] text-[#9C8D7A] text-center pt-2 border-t border-[#E6DDCF]">
            {accordInfo.isPinned 
              ? "클릭하면 고정이 해제됩니다" 
              : "클릭하면 이 정보를 고정할 수 있습니다"}
          </p>
        </div>
      )}
    </div>
  );
}
