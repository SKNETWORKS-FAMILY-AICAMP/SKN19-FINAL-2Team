"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";

export default function PerfumeNetworkPage() {
  const router = useRouter();

  useEffect(() => {
    router.replace("/perfume-network/nmap");
  }, [router]);

  return (
    <div className="min-h-screen flex items-center justify-center bg-[#FFFBF3]">
      <div className="text-center space-y-4">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-[#C8A24D] mx-auto"></div>
        <p className="text-[#7A6B57] text-sm">향수 지도로 이동 중...</p>
      </div>
    </div>
  );
}
