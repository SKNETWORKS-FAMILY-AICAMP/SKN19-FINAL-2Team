/**
 * 시리즈 카드 컴포넌트
 * 시리즈 정보를 카드 형태로 표시하고 상세 페이지로 링크
 */
import Link from "next/link";
import type { Series } from "@/app/perfume-wiki/types";

type SeriesCardProps = {
  series: Series;
  seriesLabel: string; // 예: "Series 1"
  seasonTitle: string; // 시즌 제목
};

export default function SeriesCard({
  series,
  seriesLabel,
  seasonTitle,
}: SeriesCardProps) {
  return (
    <Link
      href={`/perfume-wiki/${series.id}`}
      className="group block w-full text-left rounded-2xl overflow-hidden border border-[#F0F0F0] bg-white shadow-sm hover:shadow-md hover:-translate-y-0.5 transition-all"
    >
      <div className="relative w-full aspect-[4/2.7] bg-[#EFEFEF] overflow-hidden" suppressHydrationWarning>
        <img
          src={series.thumbnail}
          alt={series.title}
          className="w-full h-full object-cover group-hover:scale-[1.03] transition-transform"
        />
      </div>
      <div className="px-3.5 sm:px-4 py-3.5 sm:py-4 space-y-2">
        <span className="inline-flex items-center gap-2 text-[10px] font-semibold text-[#8C6A1D] bg-[#F5F1E6] px-2 py-0.5 rounded-full">
          {seriesLabel}
        </span>
        <h3 className="text-[15px] sm:text-base font-bold text-[#2B2B2B] leading-snug break-keep">
          {seasonTitle}
        </h3>
        <p className="text-[11px] text-[#999] pt-1">{`에피소드 ${series.episodes.length}개`}</p>
      </div>
    </Link>
  );
}
