import React from 'react';
import { NMapNode } from '../types';
import { BRAND_LABELS, getAccordColor } from '@/app/perfume-network/config';

interface PerfumeListProps {
  nodes: NMapNode[];
  selectedId: string | null;
  onSelect: (id: string | null) => void;
}

/**
 * 향수 맵(NMap) 추천 향수 목록 컴포넌트
 * 분석 결과에 포함된 향수들을 리스트 형태로 보여줍니다.
 */
const PerfumeList = ({ nodes, selectedId, onSelect }: PerfumeListProps) => {
  // 노드 중 향수 타입만 필터링
  const perfumes = nodes.filter((n) => n.type === 'perfume');

  const getBrandLabel = (brand?: string) => (brand ? BRAND_LABELS[brand] || brand : 'Unknown Brand');

  const getStatusBadge = (status?: string | null) => {
    if (!status) return null;
    const map: Record<string, { label: string; className: string }> = {
      HAVE: { label: '보유', className: 'bg-[#E8F0FF] text-[#3B5CC9]' },
      WANT: { label: '위시', className: 'bg-[#FFE8EE] text-[#C24B6B]' },
      HAD: { label: '과거', className: 'bg-[#F2F2F2] text-[#7A6B57]' },
      RECOMMENDED: { label: '추천', className: 'bg-[#E8F6EC] text-[#2F7D4C]' },
    };
    return map[status.toUpperCase()] || { label: status, className: 'bg-[#F8F4EC] text-[#8A7C68]' };
  };

  return (
    <section className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold text-[#1F1F1F]">탐색된 향수</h2>
        <span className="text-xs text-[#7A6B57] font-medium">{perfumes.length}개</span>
      </div>

      <div className="space-y-3 max-h-[600px] overflow-y-auto pr-2 custom-scrollbar">
        {perfumes.length > 0 ? (
          perfumes.map((perfume) => {
            const isSelected = selectedId === perfume.id;
            const status = getStatusBadge(perfume.register_status);
            const borderColor = getAccordColor(perfume.primary_accord);

            return (
              <div
                key={perfume.id}
                onClick={() => onSelect(isSelected ? null : perfume.id)}
                className={`group p-4 rounded-2xl border-2 transition-all cursor-pointer bg-white hover:shadow-md ${
                  isSelected ? 'border-[#C8A24D] ring-1 ring-[#C8A24D]' : 'border-[#E6DDCF] hover:border-[#C8A24D]/50'
                }`}
              >
                <div className="flex gap-4">
                  {/* 향수 이미지 */}
                  <div className="relative w-16 h-16 flex-shrink-0 rounded-xl overflow-hidden bg-[#F8F4EC] border border-[#F5F2EA]">
                    {perfume.image ? (
                      <img 
                        src={perfume.image} 
                        alt={perfume.label} 
                        className="w-full h-full object-cover transition-transform group-hover:scale-110"
                      />
                    ) : (
                      <div className="w-full h-full flex items-center justify-center text-2xl">✨</div>
                    )}
                    <div 
                      className="absolute bottom-0 left-0 w-full h-1" 
                      style={{ backgroundColor: borderColor }}
                    />
                  </div>

                  {/* 향수 정보 */}
                  <div className="flex-1 min-w-0 space-y-1">
                    <div className="flex items-start justify-between gap-2">
                      <h3 className={`text-sm font-bold truncate transition-colors ${isSelected ? 'text-[#C8A24D]' : 'text-[#2E2B28]'}`}>
                        {perfume.label}
                      </h3>
                      {status && (
                        <span className={`text-[10px] px-2 py-0.5 rounded-full font-semibold whitespace-nowrap ${status.className}`}>
                          {status.label}
                        </span>
                      )}
                    </div>
                    <p className="text-[11px] text-[#7A6B57] truncate">
                      {getBrandLabel(perfume.brand)}
                    </p>
                    <div className="flex flex-wrap gap-1 mt-1">
                      {perfume.accords?.slice(0, 3).map((acc) => (
                        <span key={acc} className="text-[9px] text-[#9C8D7A] bg-[#F8F4EC] px-1.5 py-0.5 rounded">
                          #{acc}
                        </span>
                      ))}
                    </div>
                  </div>
                </div>
              </div>
            );
          })
        ) : (
          <div className="py-12 text-center bg-white rounded-2xl border border-dashed border-[#E6DDCF]">
            <p className="text-sm text-[#9C8D7A]">탐색된 향수가 없습니다.</p>
          </div>
        )}
      </div>
    </section>
  );
};

export default PerfumeList;
