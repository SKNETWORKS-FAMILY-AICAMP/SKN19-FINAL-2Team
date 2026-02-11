/** **************************************************************
 * 생성 UI 컴포넌트
 ************************************************************** */
'use client';

import React from 'react';
import { useNCard } from './use-ncard';
import { NScentCard } from './NScentCard';

// 향기카드 생성 및 리스트 표시를 담당하는 메인 컴포넌트
export default function NCardGenerator() {
  const { cards, loading, error, refresh } = useNCard();

  // 로딩 중일 때 표시
  if (loading) return <div>Loading scent cards...</div>;
  
  // 에러 발생 시 표시
  if (error) return <div>Error: {error} <button onClick={() => refresh()}>Retry</button></div>;

  return (
    <div>
      <h2>Scent Cards</h2>
      {/* 리스트 갱신 버튼 */}
      <button onClick={() => refresh()} style={{ marginBottom: '20px' }}>Refresh List</button>
      
      {/* 카드 리스트 렌더링 */}
      <div style={{ display: 'flex', flexWrap: 'wrap' }}>
        {cards.length > 0 ? (
          cards.map(card => (
            <NScentCard key={card.id} card={card} />
          ))
        ) : (
          <p>No scent cards found.</p>
        )}
      </div>
    </div>
  );
}
