"use client";

export default function NMapHeader() {
  return (
    <header className="flex items-center justify-between pb-2 sm:pb-8 border-b-2 border-[#E6DDCF]">
      <div>
        <h1 className="text-3xl sm:text-4xl font-semibold mt-0">취향 탐색</h1>
        <p className="text-sm text-[#5C5448] mt-3">
          비슷하면서도 다른, 향수 지도로<br className="sm:hidden" />
          새로운 취향을 발견해보세요.
        </p>
      </div>
    </header>
  );
}
