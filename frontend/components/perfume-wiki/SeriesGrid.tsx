/**
 * 시리즈 카드 그리드 컴포넌트
 * 시리즈 목록을 반응형 그리드로 표시
 */
import SeriesCard from "./SeriesCard";
import type { Series } from "@/app/perfume-wiki/types";

type SeriesGridProps = {
  series: (Series & {
    seriesLabel?: string;
    seasonTitle?: string;
  })[];
};

export default function SeriesGrid({ series }: SeriesGridProps) {
  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 sm:gap-6">
      {series.map((item, index) => (
        <SeriesCard
          key={item.id}
          series={item}
          seriesLabel={item.seriesLabel || `Series ${index + 1}`}
          seasonTitle={item.seasonTitle || item.title}
        />
      ))}
    </div>
  );
}
