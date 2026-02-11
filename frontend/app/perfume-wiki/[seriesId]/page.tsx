/**
 * 시리즈 상세 페이지
 * 선택한 시리즈의 에피소드 목록을 페이지네이션과 함께 표시
 */
import { notFound } from "next/navigation";
import SeriesHeader from "@/components/perfume-wiki/SeriesHeader";
import EpisodeListItem from "@/components/perfume-wiki/EpisodeListItem";
import Pagination from "@/components/perfume-wiki/Pagination";
import WikiShell from "@/components/perfume-wiki/WikiShell";
import WikiBackButton from "@/components/perfume-wiki/WikiBackButton";
import PageLayout from "@/components/common/PageLayout";
import perfumeWikiData from "../_data/perfumeWiki.json";
import type { PerfumeWikiData, Series } from "../types";

const data = perfumeWikiData as PerfumeWikiData;
const PAGE_SIZE = 4; // 페이지당 표시할 에피소드 수

type SeriesPageProps = {
  params: Promise<{ seriesId: string }>;
  searchParams?: Promise<{ page?: string }>;
};

/**
 * 시리즈 ID로 데이터 조회
 * 시리즈 ID 또는 시즌 ID로 검색 가능 (시즌 ID인 경우 첫 번째 시리즈 반환)
 */
function findSeries(seriesId: string): Series | undefined {
  for (const season of data.seasons) {
    const series = season.series.find((item) => item.id === seriesId);
    if (series) {
      return series;
    }
    // 시즌 ID로 검색한 경우 해당 시즌의 첫 번째 시리즈 반환
    if (season.id === seriesId) {
      return season.series[0];
    }
  }
  return undefined;
}

export default async function SeriesPage({ params, searchParams }: SeriesPageProps) {
  const { seriesId } = await params;
  const series = findSeries(seriesId);

  if (!series) {
    notFound();
  }

  // 페이지네이션 처리
  const searchParamsResolved = await searchParams;
  const currentPage = Math.max(
    1,
    Number.parseInt(searchParamsResolved?.page ?? "1", 10) || 1
  );
  const totalPages = Math.max(1, Math.ceil(series.episodes.length / PAGE_SIZE));
  const startIndex = (currentPage - 1) * PAGE_SIZE;
  const episodes = series.episodes.slice(startIndex, startIndex + PAGE_SIZE);

  return (
    <PageLayout subTitle="Perfume Wiki" disableContentPadding>
      <WikiShell>
        <div className="flex justify-end mb-4 sm:mb-8">
          <WikiBackButton href="/perfume-wiki" label="목록" />
        </div>

        <div className="max-w-5xl mx-auto space-y-8 sm:space-y-10 md:space-y-12">
          <SeriesHeader series={series} />

          <section className="space-y-4 sm:space-y-6">
            <div className="flex items-center justify-between gap-3">
              <h2 className="text-lg sm:text-xl font-bold text-[#1F1F1F] break-keep">
                에피소드 리스트
              </h2>
              <span className="text-xs sm:text-sm text-[#999] font-medium shrink-0">{`총 ${series.episodes.length}개`}</span>
            </div>
            <div>
              {episodes.map((episode) => (
                <EpisodeListItem
                  key={episode.id}
                  episode={episode}
                  seriesId={series.id}
                />
              ))}
            </div>
          </section>

          <Pagination
            basePath={`/perfume-wiki/${series.id}`}
            currentPage={currentPage}
            totalPages={totalPages}
          />
        </div>
      </WikiShell>
    </PageLayout>
  );
}
