/**
 * 시리즈 관련 에피소드 카드 컴포넌트
 * 현재 에피소드와 같은 시리즈의 다른 에피소드들을 표시
 */
import Link from "next/link";
import type { Series } from "@/app/perfume-wiki/types";

type SeriesRelatedCardProps = {
  series: Series;
  currentEpisodeId: string;
};

export default function SeriesRelatedCard({
  series,
  currentEpisodeId,
}: SeriesRelatedCardProps) {
  // 현재 에피소드를 제외한 다른 에피소드 최대 3개 표시
  const otherEpisodes = series.episodes
    .filter((ep) => ep.id !== currentEpisodeId)
    .slice(0, 3);

  if (otherEpisodes.length === 0) {
    return null;
  }

  return (
    <section className="py-7 sm:py-10 md:py-12 px-4 sm:px-6 md:px-10 rounded-2xl sm:rounded-3xl bg-white border border-[#F0F0F0] shadow-sm">
      <div className="space-y-6 sm:space-y-8">
        <div>
          <p className="text-xs font-semibold text-[#8C6A1D] mb-3 tracking-wider uppercase">
            이 에피소드가 속한 시리즈
          </p>
          <h3 className="text-lg sm:text-xl md:text-2xl font-bold text-[#1F1F1F] mb-3 break-keep">
            {series.title}
          </h3>
          <p className="text-xs sm:text-sm text-[#777] leading-relaxed break-keep">{series.summary}</p>
        </div>

        <div className="space-y-4 sm:space-y-5">
          <h4 className="text-sm font-bold text-[#555]">
            다른 에피소드 둘러보기
          </h4>
          <div className="space-y-2.5 sm:space-y-3">
            {otherEpisodes.map((episode) => (
              <Link
                key={episode.id}
                href={`/perfume-wiki/${series.id}/${episode.id}`}
                className="flex items-center gap-3 sm:gap-4 p-3.5 sm:p-5 rounded-xl bg-[#FDFBF8] hover:bg-[#F8F6F1] border border-transparent hover:border-[#EFEFEF] hover:shadow-sm transition-all duration-300 group"
              >
                <div className="w-16 h-16 sm:w-20 sm:h-20 rounded-xl overflow-hidden bg-[#EFEFEF] shrink-0">
                  <img
                    src={episode.thumbnail}
                    alt={episode.title}
                    className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300"
                  />
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-xs sm:text-sm font-bold text-[#2B2B2B] truncate group-hover:text-[#C8A24D] transition">
                    {episode.title}
                  </p>
                  <p className="text-xs text-[#999] mt-1.5 line-clamp-2">
                    {episode.summary}
                  </p>
                </div>
                <span className="text-xl text-[#CCC] group-hover:text-[#C8A24D] group-hover:translate-x-1 transition-all">
                  →
                </span>
              </Link>
            ))}
          </div>
        </div>

        <Link
          href={`/perfume-wiki/${series.id}`}
          className="block w-full py-3 sm:py-3.5 text-center rounded-xl border-2 border-[#EFEFEF] text-[#555] font-semibold text-sm sm:text-base hover:border-[#C8A24D] hover:text-[#C8A24D] hover:bg-[#FDFBF8] transition-all duration-300"
        >
          시리즈 전체보기
        </Link>
      </div>
    </section>
  );
}
