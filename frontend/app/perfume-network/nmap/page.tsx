"use client";

import React, { useEffect, useState } from 'react';
import { useSession } from 'next-auth/react';
import Link from "next/link";
import PageLayout from "@/components/common/PageLayout";
import NMapView from './NMapView';

/**
 * 향수 맵(NMap) 결과 페이지
 * 세션 정보를 관리하고 메인 뷰(NMapView)를 렌더링합니다.
 */
export default function NMapPage() {
  const { data: session } = useSession();
  const [sessionUserId, setSessionUserId] = useState<string | number | undefined>(undefined);
  const [isMounted, setIsMounted] = useState(false);

  useEffect(() => {
    setIsMounted(true);
  }, []);

  useEffect(() => {
    // localAuth 제거: 세션 id만 사용
    // 1. Next-Auth 세션에서 ID 확인
    if (session?.user) {
      const id = (session.user as any).id;
      if (id) {
        setSessionUserId(id);
        return;
      }
    }
    setSessionUserId(undefined);
  }, [session]);

  return (
    <PageLayout subTitle="PERFUME MAP" disableContentPadding>
      <main className="pt-[97px] sm:pt-[120px] pb-12">
        <NMapView sessionUserId={sessionUserId} />
      </main>
    </PageLayout>
  );
}
