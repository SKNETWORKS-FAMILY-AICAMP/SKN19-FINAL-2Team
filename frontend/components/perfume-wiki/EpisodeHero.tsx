/**
 * 에피소드 히어로 섹션 컴포넌트
 * 에피소드 상세 페이지 상단의 대형 이미지와 제목을 표시
 */
import type { Episode } from "@/app/perfume-wiki/types";

type EpisodeHeroProps = {
  episode: Episode;
  seriesTitle: string;
  seriesId: string;
  episodeNumber: number;
};

export default function EpisodeHero({
  episode,
  seriesTitle,
  seriesId,
  episodeNumber,
}: EpisodeHeroProps) {
  // 히어로 이미지가 없으면 썸네일 사용
  const heroImage = episode.heroImage || episode.thumbnail;
  const readTime = episode.readTime || "3분";

  return (
    <section className="relative w-full h-[320px] sm:h-[420px] md:h-[620px] overflow-hidden rounded-2xl sm:rounded-3xl shadow-lg">
      <div className="absolute inset-0 bg-gradient-to-t from-black/75 via-black/35 to-transparent z-10" />
      <img
        src={heroImage}
        alt={episode.title}
        className="w-full h-full object-cover"
      />

      <div className="absolute bottom-0 left-0 right-0 z-20 p-4 sm:p-6 md:p-14 space-y-3 sm:space-y-5">
        <div className="flex flex-wrap items-center gap-x-2.5 gap-y-1.5 text-white/90 text-[11px] sm:text-sm md:text-base leading-relaxed">
          <span className="font-semibold">{seriesTitle}</span>
          <span className="w-1 h-1 sm:w-1.5 sm:h-1.5 rounded-full bg-white/60" />시리즈 {seriesId.split('-')[1]}
          <span className="w-1.5 h-1.5 rounded-full bg-white/60" />에피소드 {episodeNumber}
          <span className="w-1.5 h-1.5 rounded-full bg-white/60" />
          <span>{readTime} 읽기</span>
        </div>

        <h1 className="text-lg sm:text-2xl md:text-3xl lg:text-4xl font-bold text-white leading-tight max-w-4xl break-keep">
          {episode.title}
        </h1>

        <p className="text-xs sm:text-sm md:text-base text-white/85 max-w-2xl">
          {episode.date}
        </p>
      </div>
    </section>
  );
}
