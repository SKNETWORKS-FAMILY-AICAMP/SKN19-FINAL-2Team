/**
 * 페이지네이션 컴포넌트
 * 에피소드 목록의 페이지 네비게이션을 제공
 */
import Link from "next/link";

type PaginationProps = {
  basePath: string;   // 기본 경로 (예: /perfume-wiki/series-1)
  currentPage: number; // 현재 페이지 번호
  totalPages: number;  // 전체 페이지 수
};

export default function Pagination({
  basePath,
  currentPage,
  totalPages,
}: PaginationProps) {
  // 페이지가 1개 이하면 페이지네이션 표시 안 함
  if (totalPages <= 1) {
    return null;
  }

  const pages = Array.from({ length: totalPages }, (_, idx) => idx + 1);

  return (
    <nav className="flex items-center justify-center gap-1.5 sm:gap-2">
      {pages.map((page) => {
        const isActive = page === currentPage;
        const href =
          page === 1 ? basePath : `${basePath}?page=${page.toString()}`;

        return (
          <Link
            key={page}
            href={href}
            aria-current={isActive ? "page" : undefined}
            className={`w-8 h-8 sm:w-9 sm:h-9 rounded-full flex items-center justify-center text-xs sm:text-sm font-semibold transition ${
              isActive
                ? "bg-[#C8A24D] text-white shadow-[0_6px_16px_rgba(200,162,77,0.35)]"
                : "bg-white border border-[#EFEFEF] text-[#777] hover:border-[#C8A24D] hover:text-[#1F1F1F]"
            }`}
          >
            {page}
          </Link>
        );
      })}
    </nav>
  );
}
