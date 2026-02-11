/**
 * 시즌 섹션 컴포넌트
 * 시즌 정보와 해당 시즌에 속한 시리즈 그리드를 표시
 * 
 * 현재 사용되지 않음 - 향후 시즌별 페이지 구현 시 사용 예정
 */
import type { Season } from "@/app/perfume-wiki/types";
import SeriesGrid from "./SeriesGrid";

type SeasonSectionProps = {
  season: Season;
};

export default function SeasonSection({ season }: SeasonSectionProps) {
  return (
    <section className="space-y-6">
      <div className="space-y-2">
        <p className="text-xs font-semibold text-[#8C6A1D] tracking-[0.2em] uppercase">
          Series
        </p>
        <h2 className="text-2xl md:text-3xl font-bold text-[#222]">
          {season.title}
        </h2>
        <p className="text-sm text-[#777]">{season.description}</p>
      </div>
      <SeriesGrid series={season.series} />
    </section>
  );
}
