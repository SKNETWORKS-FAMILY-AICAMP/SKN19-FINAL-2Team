'use client';

import React from 'react';
import { useNCard } from '../ncard/use-ncard';
import { NScentCard } from '../ncard/NScentCard';
import PageLayout from "@/components/common/PageLayout";

export default function TestCardPage() {
  const { cards, loading, error, refresh } = useNCard();

  return (
    <PageLayout subTitle="Perfume Test Results">
      <div style={{ padding: '120px 40px 40px', backgroundColor: '#FDFBF8', minHeight: '100vh' }}>
        <div style={{ maxWidth: '800px', margin: '0 auto' }}>

          {/* 헤더 */}
          <header style={{ marginBottom: '30px', textAlign: 'center' }}>
            <h1 style={{ fontSize: '2rem', fontWeight: 'bold', color: '#111827' }}>
              MBTI 유형별 어울리는 나만의 퍼스널 향
            </h1>
            <p style={{ color: '#4b5563', marginTop: '8px' }}>
              사용자가 클릭한 정보 (어코드, 향수)를 기반으로<br></br>
              Scentence에서 준비한 Scent-MBTI 분석 결과를 확인할 수 있습니다.
            </p>
          </header>

          {/* 로딩 중일 때 */}
          {loading && (
            <div style={{ textAlign: 'center', padding: '40px' }}>
              데이터를 불러오는 중입니다...
            </div>
          )}

          {/* 에러 발생 시 */}
          {error && (
            <div style={{
              textAlign: 'center',
              padding: '20px',
              backgroundColor: '#fee2e2',
              color: '#b91c1c',
              borderRadius: '8px'
            }}>
              에러 발생: {error}
            </div>
          )}

          {/* 향기 카드가 없을 때 */}
          {!loading && !error && cards.length === 0 && (
            <div style={{ textAlign: 'center', padding: '40px' }}>
              표시할 향기카드가 없습니다.
            </div>
          )}

          {/* 향기 카드 리스트 */}
          <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '20px' }}>
            {cards.map((card) => (
              <NScentCard key={card.id} card={card} />
            ))}
          </div>
        </div>
      </div>
    </PageLayout>
  );
}
