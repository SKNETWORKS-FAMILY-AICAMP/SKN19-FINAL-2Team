"use client";

/**
 * 향수 백과 메인 페이지
 * 각 시즌의 대표 시리즈를 카드 형태로 렌더링
 */
import SeriesGrid from "@/components/perfume-wiki/SeriesGrid";
import WikiShell from "@/components/perfume-wiki/WikiShell";
import perfumeWikiData from "./_data/perfumeWiki.json";
import type { PerfumeWikiData } from "./types";
import PageLayout from "@/components/common/PageLayout";

const data = perfumeWikiData as PerfumeWikiData;

/**
 * 시즌 데이터에서 각 시즌의 첫 번째 시리즈를 추출하여
 * 메인 페이지에 표시할 카드 목록 데이터 생성
 */
const seriesList = data.seasons.flatMap((season, index) => {
  const [primarySeries] = season.series;
  if (!primarySeries) {
    return [];
  }

  return [
    {
      ...primarySeries,
      seriesLabel: `Series ${index + 1}`,
      seasonTitle: season.title,
    },
  ];
});

export default function PerfumeWikiPage() {
  return (
    <PageLayout subTitle="Perfume Wiki" disableContentPadding>
      <WikiShell className="space-y-10 sm:space-y-14 md:space-y-16">
        <section className="space-y-2.5 sm:space-y-3">
          <h1 className="text-2xl sm:text-3xl md:text-4xl font-bold text-[#1F1F1F] break-keep">
            향수 백과
          </h1>
          <p className="text-sm md:text-base text-[#777] leading-relaxed break-keep">
            향수에 대해 더 알아보고 싶다면 시리즈를 따라 향의 흐름을 배워보세요.
          </p>
        </section>

        <SeriesGrid series={seriesList} />
      </WikiShell>
    </PageLayout>
  );
}
