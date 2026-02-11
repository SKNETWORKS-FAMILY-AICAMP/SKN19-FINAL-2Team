/**
 * 시리즈 헤더 컴포넌트
 * 시리즈 상세 페이지 상단의 시리즈 정보 표시 영역
 */
import type { Series } from "@/app/perfume-wiki/types";

type SeriesHeaderProps = {
  series: Series;
};

export default function SeriesHeader({ series }: SeriesHeaderProps) {
  return (
    <section className="flex flex-col md:flex-row gap-4 sm:gap-6 rounded-2xl sm:rounded-3xl overflow-hidden border border-[#F0F0F0] bg-white shadow-sm">
      <div className="w-full md:w-[55%] aspect-[16/10] md:aspect-[4/3] bg-[#EFEFEF] overflow-hidden">
        <img
          src={series.thumbnail}
          alt={series.title}
          className="w-full h-full object-cover"
        />
      </div>
      <div className="flex-1 p-4 sm:p-6 md:p-8 flex flex-col justify-between">
        <div className="space-y-2.5 sm:space-y-3">
          <span className="inline-flex items-center gap-2 text-xs font-semibold text-[#8C6A1D]">
            <span className="w-1.5 h-1.5 rounded-full bg-[#C8A24D]" />
            {series.id}
          </span>
          <h1 className="text-xl sm:text-2xl md:text-3xl font-bold text-[#1F1F1F] break-keep">
            {series.title}
          </h1>
          <p className="text-sm text-[#777] leading-relaxed break-keep">{series.summary}</p>
        </div>
        <p className="text-xs text-[#9A9A9A] mt-4 sm:mt-6">{`EP ${series.episodes.length}개`}</p>
      </div>
    </section>
  );
}
