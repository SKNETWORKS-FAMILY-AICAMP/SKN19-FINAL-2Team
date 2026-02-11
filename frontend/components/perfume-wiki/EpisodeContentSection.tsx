/**
 * 에피소드 콘텐츠 섹션 컴포넌트
 * 에피소드의 본문 내용을 섹션 단위로 표시
 */
import type { ContentSection } from "@/app/perfume-wiki/types";

type EpisodeContentSectionProps = {
  content: ContentSection[];
};

export default function EpisodeContentSection({
  content,
}: EpisodeContentSectionProps) {
  if (!content || content.length === 0) {
    return null;
  }

  return (
    <section className="space-y-8 sm:space-y-12 md:space-y-16 max-w-4xl mx-auto">
      {content.map((section, index) => (
        <div key={index} className="space-y-4 sm:space-y-6">
          <h2 className="text-lg sm:text-xl md:text-2xl font-bold text-[#1F1F1F] leading-tight break-keep">
            {section.subtitle}
          </h2>
          <div className="space-y-3.5 sm:space-y-5">
            {section.paragraphs.map((paragraph, pIndex) => (
              <p
                key={pIndex}
                className="text-sm md:text-base leading-relaxed text-[#444] whitespace-pre-line break-keep"
              >
                {paragraph}
              </p>
            ))}
          </div>
        </div>
      ))}
    </section>
  );
}
