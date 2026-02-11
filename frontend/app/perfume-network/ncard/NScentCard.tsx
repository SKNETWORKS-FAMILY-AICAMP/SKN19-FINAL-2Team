/** **************************************************************
 * 카드 디자인 컴포넌트
 ************************************************************** */
import React, { useState, useRef } from 'react';
import { ScentCard } from './ncard-service';
import { Sparkles } from "lucide-react";
import { ACCORD_ICONS, ACCORD_COLORS, hexToRgba } from '../config';

interface NScentCardProps {
  card: ScentCard;
  userName?: string; // 회원 이름 (미구현)
  userImageUrl?: string | null;
  onClose?: () => void; // 패널 닫기 콜백
  onAccordClick?: (accordName: string) => void; // 어코드 클릭 콜백
  onSave?: () => void; // 카드 저장 콜백
  isSaving?: boolean; // 저장 중 상태
}

export const NScentCard: React.FC<NScentCardProps> = ({ card, userName, userImageUrl, onClose, onAccordClick, onSave, isSaving = false }) => {
  const [currentPage, setCurrentPage] = useState(0);
  const [isOpen, setIsOpen] = useState(true); // 패널 열림 상태
  const [isLiked, setIsLiked] = useState(false); // 하트 상태
  const scrollRef = useRef<HTMLDivElement>(null);
  const cardRef = useRef<HTMLDivElement>(null);
  const baseUserName = (userName || 'Guest').replace(/\s*님$/, '').trim() || 'Guest';
  const displayUserName = `${baseUserName} 님`;

  // 메인 컬러 테마
  const theme = {
    primary: '#C8A24D',
    secondary: '#7A6B57',
    bg: '#FFFFFF',
    accentBg: '#F8F4EC',
    text: '#1F1F1F',
    subText: '#5C5448',
    success: '#2F7D4C',
    error: '#C24B6B',
    successBg: '#E8F6EC',
    errorBg: '#FFE8EE',
  };

  // 어코드별 이모지 및 색상 매핑 (config.ts)
  const getAccordInfo = (name: string) => {
    const key = Object.keys(ACCORD_ICONS).find(
      k => k.toLowerCase() === name.toLowerCase() || name.toLowerCase().includes(k.toLowerCase())
    );
    
    return {
      icon: key ? ACCORD_ICONS[key] : Sparkles,
      color: key ? ACCORD_COLORS[key] : theme.primary
    };
  };

  // 배경 이미지 경로 설정
  const bgImageUrl = card.image_url;
  // 우선은 테스트를 위해 기본 이미지 경로 (없을 경우를 대비해 placeholder 또는 그라디언트 처리)
  const fallbackBg = 'linear-gradient(135deg, #a8caba 0%, #5d4157 100%)';

  // 스크롤 핸들러
  const handleScroll = () => {
    if (scrollRef.current) {
      const scrollLeft = scrollRef.current.scrollLeft;
      const width = scrollRef.current.offsetWidth;
      const page = Math.round(scrollLeft / width);
      setCurrentPage(page);
    }
  };

  // 좌우 이동 버튼 핸들러
  const scrollToIndex = (index: number) => {
    if (scrollRef.current) {
      const width = scrollRef.current.offsetWidth;
      scrollRef.current.scrollTo({
        left: width * index,
        behavior: 'smooth'
      });
    }
  };

  // 하트 버튼 클릭 - 카드 저장 (saved=true)
  const handleLike = async () => {
    if (!onSave || isSaving || isLiked) return;
    setIsLiked(true);
    await onSave();
  };

  // 이미지 다운로드 핸들러
  const handleDownload = async () => {
    try {
      const html2canvas = (await import('html2canvas')).default;
      if (cardRef.current) {
        const canvas = await html2canvas(cardRef.current, {
          scale: 2,
          backgroundColor: '#ffffff',
          logging: false,
          useCORS: true
        });
        const link = document.createElement('a');
        link.download = `scentcard_${card.mbti}_${Date.now()}.png`;
        link.href = canvas.toDataURL('image/png');
        link.click();
      }
    } catch (error) {
      console.error('이미지 다운로드 실패:', error);
      alert('이미지 다운로드에 실패했습니다.');
    }
  };

  return (
    <>
      <style>{`
        .ncard-panel::-webkit-scrollbar {
          width: 8px;
        }
        .ncard-panel::-webkit-scrollbar-track {
          background: #f1f1f1;
        }
        .ncard-panel::-webkit-scrollbar-thumb {
          background: #C8A24D;
          border-radius: 4px;
        }
        .ncard-panel::-webkit-scrollbar-thumb:hover {
          background: #B69140;
        }
      `}</style>
      <div
        className={`ncard-panel fixed right-0 top-0 h-full transition-transform duration-500 ease-in-out z-50 ${isOpen ? 'translate-x-0' : 'translate-x-full'}`}
        style={{
          width: '100%',
          maxWidth: '440px',
          backgroundColor: theme.bg,
          boxShadow: '-10px 0 40px rgba(0,0,0,0.15)',
          overflowY: 'auto',
          overflowX: 'hidden',
          fontFamily: 'inherit',
          color: theme.text,
          display: 'flex',
          flexDirection: 'column',
          borderLeft: '1px solid #efefef',
        }}
      >
      {/* ------------------------------ 패널 토글 버튼 ------------------------------ */}
      <button 
        onClick={() => setIsOpen(!isOpen)}
        style={{
          position: 'absolute',
          left: '-40px',
          top: '50%',
          transform: 'translateY(-50%)',
          width: '40px',
          height: '100px',
          backgroundColor: theme.bg,
          border: '1px solid #efefef',
          borderRight: 'none',
          borderRadius: '12px 0 0 12px',
          cursor: 'pointer',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          boxShadow: '-4px 0 10px rgba(0,0,0,0.05)',
          zIndex: 60
        }}
      >
        <span style={{ transform: isOpen ? 'rotate(0deg)' : 'rotate(180deg)', transition: 'transform 0.3s' }}>
          {isOpen ? '›' : '‹'}
        </span>
      </button>

      {/* ------------------------------ 프로필 헤더 ------------------------------ */}
      <header style={{ 
        padding: '12px 16px', 
        display: 'flex', 
        alignItems: 'center', 
        justifyContent: 'space-between',
        flexShrink: 0,
        zIndex: 10,
        backgroundColor: '#fff'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <div style={{ 
            width: '32px', 
            height: '32px', 
            borderRadius: '50%', 
            background: 'linear-gradient(45deg, #f09433 0%, #e6683c 25%, #dc2743 50%, #cc2366 75%, #bc1888 100%)',
            padding: '2px'
          }}>
            <div style={{ 
              width: '100%', 
              height: '100%', 
              borderRadius: '50%', 
              backgroundColor: '#fff',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              fontSize: '12px',
              overflow: 'hidden'
            }}>
              {userImageUrl ? (
                <img
                  src={userImageUrl}
                  alt="Profile"
                  style={{ width: '100%', height: '100%', objectFit: 'cover' }}
                  onError={(e) => {
                    e.currentTarget.style.display = 'none';
                  }}
                />
              ) : (
                "👤"
              )}
            </div>
          </div>
          <span style={{ fontSize: '14px', fontWeight: 700 }}>{displayUserName}</span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <div style={{ fontSize: '18px', cursor: 'pointer', color: '#262626' }}>•••</div>
          {onClose && (
            <button onClick={onClose} style={{ background: 'none', border: 'none', fontSize: '20px', cursor: 'pointer', color: theme.subText }}>×</button>
          )}
        </div>
      </header>

      {/* ------------------------------ 메인 비주얼 카드 (이미지 슬라이드 영역) ------------------------------ */}
      <div ref={cardRef} style={{ position: 'relative', width: '100%', minHeight: '400px', flexShrink: 0 }}>
        
        {/* 네비게이션 화살표 */}
        {currentPage > 0 && (
          <button 
            onClick={() => scrollToIndex(currentPage - 1)}
            style={{
              position: 'absolute', left: '10px', top: '50%', transform: 'translateY(-50%)',
              zIndex: 10, background: 'rgba(255,255,255,0.8)', border: 'none', borderRadius: '50%',
              width: '28px', height: '28px', cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center',
              boxShadow: '0 2px 5px rgba(0,0,0,0.1)', color: '#262626', fontSize: '18px'
            }}
          >
            ‹
          </button>
        )}
        {currentPage < 3 && (
          <button 
            onClick={() => scrollToIndex(currentPage + 1)}
            style={{
              position: 'absolute', right: '10px', top: '50%', transform: 'translateY(-50%)',
              zIndex: 10, background: 'rgba(255,255,255,0.8)', border: 'none', borderRadius: '50%',
              width: '28px', height: '28px', cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center',
              boxShadow: '0 2px 5px rgba(0,0,0,0.1)', color: '#262626', fontSize: '18px'
            }}
          >
            ›
          </button>
        )}

        <div
          ref={scrollRef}
          onScroll={handleScroll}
          style={{
            display: 'flex',
            overflowX: 'auto',
            scrollSnapType: 'x mandatory',
            scrollbarWidth: 'none',
            msOverflowStyle: 'none',
            WebkitOverflowScrolling: 'touch',
            minHeight: '400px'
          }}
        >
          <style>{`div::-webkit-scrollbar { display: none; }`}</style>

          {/* [PAGE 1] 메인 */}
          <div style={{ 
            flex: '0 0 100%', scrollSnapAlign: 'start', position: 'relative', 
            background: fallbackBg, backgroundImage: `url(${bgImageUrl})`, backgroundSize: 'cover', backgroundPosition: 'center',
            display: 'flex', flexDirection: 'column', justifyContent: 'center', padding: '30px', color: '#fff', textAlign: 'center'
          }}>
            <div style={{ position: 'absolute', inset: 0, backgroundColor: 'rgba(0,0,0,0.25)', backdropFilter: 'blur(2px)', zIndex: 1 }} />
            <div style={{ position: 'relative', zIndex: 2 }}>
              <div style={{ fontSize: '40px', marginBottom: '10px', opacity: 0.8 }}>"</div>
              <h2 style={{ fontSize: '20px', fontWeight: 700, margin: '0 0 5px', opacity: 0.9, wordBreak: 'break-word', overflowWrap: 'break-word', padding: '0 10px' }}>{card.persona_title}</h2>
              <h1 style={{ fontSize: '48px', fontWeight: 900, margin: '0 0 10px', letterSpacing: '-0.03em', textShadow: '0 2px 10px rgba(0,0,0,0.3)' }}>{card.mbti}</h1>
              <p style={{ fontSize: '15px', lineHeight: '1.6', margin: '0 auto 20px', maxWidth: '280px', wordBreak: 'break-word', overflowWrap: 'break-word', opacity: 0.95, fontWeight: 500 }}>{card.story}</p>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px', justifyContent: 'center', marginBottom: '15px', padding: '0 10px' }}>
                {card.keywords.map((kw, idx) => (
                  <span key={idx} style={{ fontSize: '12px', color: 'rgba(255,255,255,0.8)', wordBreak: 'break-word' }}>#{kw}</span>
                ))}
              </div>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px', justifyContent: 'center', padding: '0 10px' }}>
                {card.components.map((item, idx) => (
                  <div key={idx} style={{ display: 'flex', alignItems: 'center', gap: '4px', padding: '4px 12px', backgroundColor: 'rgba(255,255,255,0.15)', borderRadius: '100px', backdropFilter: 'blur(10px)', border: '1px solid rgba(255,255,255,0.2)', fontSize: '12px', fontWeight: 600, wordBreak: 'keep-all', whiteSpace: 'nowrap' }}>
                    <span style={{ color: theme.primary }}>{item.code}</span>
                    <span>{item.axis}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* [PAGE 2] 성향 분석 상세 */}
          <div style={{
            flex: '0 0 100%', scrollSnapAlign: 'start', position: 'relative',
            backgroundColor: '#fff', display: 'flex', flexDirection: 'column', padding: '30px', minHeight: '400px'
          }}>
            <div style={{ position: 'relative', zIndex: 2, minHeight: '340px', display: 'flex', flexDirection: 'column' }}>
              <h3 style={{ flexShrink: 0, fontSize: '16px', fontWeight: 800, marginBottom: '15px', textAlign: 'center', color: theme.text, borderBottom: `1px solid ${theme.accentBg}`, paddingBottom: '10px' }}>성향 분석 리포트</h3>
              <div style={{ flex: 1, display: 'grid', gridTemplateRows: 'repeat(4, auto)', gap: '10px' }}>
                {card.components.map((item, idx) => (
                  <div key={idx} style={{ backgroundColor: theme.accentBg, padding: '10px 16px', borderRadius: '12px', border: '1px solid #efefef', display: 'flex', flexDirection: 'column', justifyContent: 'center' }}>
                    <div style={{ fontSize: '11px', fontWeight: 700, color: theme.primary, marginBottom: '2px', textTransform: 'uppercase' }}>{item.axis} ({item.code})</div>
                    <div style={{ fontSize: '12px', lineHeight: '1.4', color: theme.text, wordBreak: 'break-word', overflowWrap: 'break-word' }}>{item.desc}</div>
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* [PAGE 3] 추천 어코드 & 노트 */}
          <div style={{
            flex: '0 0 100%', scrollSnapAlign: 'start', position: 'relative',
            backgroundColor: '#fff', display: 'flex', flexDirection: 'column', padding: '30px', minHeight: '400px'
          }}>
            <div style={{ position: 'relative', zIndex: 2, minHeight: '340px', display: 'flex', flexDirection: 'column' }}>
              <h3 style={{ flexShrink: 0, fontSize: '16px', fontWeight: 800, marginBottom: '15px', textAlign: 'center', color: theme.text, borderBottom: `1px solid ${theme.accentBg}`, paddingBottom: '10px' }}>추천 어코드 & 노트</h3>
              <div style={{ flex: 1, display: 'grid', gridTemplateRows: 'repeat(3, auto)', gap: '10px' }}>
                {card.recommends.slice(0, 3).map((acc, idx) => {
                  const info = getAccordInfo(acc.name);
                  const Icon = info.icon;
                  return (
                    <div key={idx} style={{ backgroundColor: hexToRgba(info.color, 0.05), padding: '12px 15px', borderRadius: '15px', border: `1px solid ${hexToRgba(info.color, 0.2)}`, display: 'flex', flexDirection: 'column', justifyContent: 'center' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '6px' }}>
                        <span style={{ width: '28px', height: '28px', backgroundColor: info.color, borderRadius: '50%', display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 }}>
                          <Icon size={16} color="#fff" strokeWidth={1.8} />
                        </span>
                        <span style={{ fontWeight: 800, fontSize: '15px', color: theme.text }}>{acc.name}</span>
                      </div>
                      <p style={{ fontSize: '12px', lineHeight: '1.4', color: theme.subText, marginBottom: '8px', wordBreak: 'break-word', overflowWrap: 'break-word' }}>{acc.reason}</p>
                      {acc.notes && (
                        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px' }}>
                          {acc.notes.map((note, nIdx) => (
                            <span key={nIdx} style={{ fontSize: '10px', padding: '2px 10px', backgroundColor: '#fff', borderRadius: '100px', border: `1px solid ${hexToRgba(info.color, 0.2)}`, color: info.color, fontWeight: 600 }}>#{note}</span>
                          ))}
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            </div>
          </div>

          {/* [PAGE 4] 비추천 어코드 */}
          <div style={{
            flex: '0 0 100%', scrollSnapAlign: 'start', position: 'relative',
            backgroundColor: '#fff', display: 'flex', flexDirection: 'column', padding: '30px', minHeight: '400px'
          }}>
            <div style={{ position: 'relative', zIndex: 2, minHeight: '340px', display: 'flex', flexDirection: 'column' }}>
              <h3 style={{ flexShrink: 0, fontSize: '16px', fontWeight: 800, marginBottom: '15px', textAlign: 'center', color: theme.text, borderBottom: `1px solid ${theme.accentBg}`, paddingBottom: '10px' }}>기피해야 할 어코드</h3>
              <div style={{ flex: 1, display: 'grid', gridTemplateRows: 'repeat(3, auto)', gap: '10px' }}>
                {card.avoids.slice(0, 3).map((acc, idx) => {
                  const info = getAccordInfo(acc.name);
                  const Icon = info.icon;
                  return (
                    <div key={idx} style={{ backgroundColor: hexToRgba(info.color, 0.05), padding: '12px 15px', borderRadius: '15px', border: `1px dashed ${hexToRgba(info.color, 0.3)}`, display: 'flex', flexDirection: 'column', justifyContent: 'center' }}>
                      <div style={{ fontWeight: 800, fontSize: '15px', marginBottom: '6px', display: 'flex', alignItems: 'center', gap: '8px', color: theme.text }}>
                        <span style={{ width: '28px', height: '28px', backgroundColor: info.color, borderRadius: '50%', display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 }}>
                          <Icon size={16} color="#fff" strokeWidth={1.8} />
                        </span>
                        {acc.name}
                      </div>
                      <p style={{ fontSize: '12px', lineHeight: '1.4', color: theme.subText, wordBreak: 'break-word', overflowWrap: 'break-word' }}>{acc.reason}</p>
                    </div>
                  );
                })}
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* 페이지네이션 (점 4개) */}
      <div style={{ display: 'flex', justifyContent: 'center', gap: '6px', padding: '10px 0', backgroundColor: '#fff' }}>
        {[0, 1, 2, 3].map(i => (
          <div key={i} style={{ 
            width: '6px', height: '6px', borderRadius: '50%', 
            backgroundColor: currentPage === i ? '#0095f6' : '#dbdbdb',
            transition: 'all 0.2s ease'
          }} />
        ))}
      </div>

      {/* ------------------------------ 액션 바 (아이콘 버튼) ------------------------------ */}
      <div style={{
        padding: '12px 16px', display: 'flex', alignItems: 'center', gap: '16px', flexShrink: 0, backgroundColor: '#fff'
      }}>
        {/* 하트 (카드 저장) */}
        <button
          onClick={handleLike}
          disabled={!onSave || isSaving || isLiked}
          style={{
            background: 'none',
            border: 'none',
            padding: 0,
            cursor: (onSave && !isSaving && !isLiked) ? 'pointer' : 'default',
            display: 'flex',
            opacity: !onSave ? 0.3 : 1
          }}
          title={isLiked ? "저장됨" : isSaving ? "저장 중..." : "내 보관함에 저장"}
        >
          <svg aria-label="저장" color={isLiked ? "#C8A24D" : "#262626"} fill={isLiked ? "#C8A24D" : "none"} height="24" role="img" viewBox="0 0 24 24" width="24">
            <path d="M16.792 3.904A4.989 4.989 0 0121.5 9.122c0 3.072-2.652 4.959-5.197 7.222-2.512 2.243-3.865 3.469-4.303 3.752-.477-.309-2.143-1.823-4.303-3.752C5.141 14.072 2.5 12.194 2.5 9.122a4.989 4.989 0 014.708-5.218 4.21 4.21 0 013.675 1.941c.325.487.544.98.617 1.215h1.412a3.012 3.012 0 01.623-1.222 4.198 4.198 0 013.597-1.934z" stroke="currentColor" strokeWidth={isLiked ? "0" : "2"}></path>
          </svg>
        </button>

        {/* 공유 (비행기) */}
        <button style={{ background: 'none', border: 'none', padding: 0, cursor: 'pointer', display: 'flex' }} title="공유하기">
          <svg aria-label="공유" color="#262626" fill="#262626" height="24" role="img" viewBox="0 0 24 24" width="24">
            <line fill="none" stroke="currentColor" strokeLinejoin="round" strokeWidth="2" x1="22" x2="9.218" y1="3" y2="10.083"></line>
            <polygon fill="none" points="11.698 20.334 22 3.001 2 3.001 9.218 10.084 11.698 20.334" stroke="currentColor" strokeLinejoin="round" strokeWidth="2"></polygon>
          </svg>
        </button>
        <div style={{ flex: 1 }} />

        {/* 이미지 다운로드 (북마크) */}
        <button
          onClick={handleDownload}
          style={{
            background: 'none',
            border: 'none',
            padding: 0,
            cursor: 'pointer',
            display: 'flex'
          }}
          title="이미지로 저장"
        >
          <svg aria-label="이미지 저장" color="#262626" fill="none" height="24" role="img" viewBox="0 0 24 24" width="24">
            <polygon points="20 21 12 13.44 4 21 4 3 20 3 20 21" stroke="currentColor" strokeLinecap="round" strokeLinejoin="round" strokeWidth="2"></polygon>
          </svg>
        </button>
      </div>

      {/* ------------------------------ 캡션 영역 (Summary & Tags & CTA) ------------------------------ */}
      <div style={{ padding: '0 16px 20px', flexShrink: 0, backgroundColor: '#fff' }}>
        <div style={{ marginBottom: '12px' }}>
          <span style={{ fontSize: '14px', lineHeight: '1.5', color: '#262626', wordBreak: 'break-word', overflowWrap: 'break-word', display: 'block' }}>
            {card.summary}
            <br />어울리는 향이 마음에 들었나요? 이제 나만의 향수를 추천받아보세요!
          </span>
        </div>
        <div style={{ fontSize: '12px', lineHeight: '1.6', marginBottom: '12px', wordBreak: 'break-word', overflowWrap: 'break-word' }}>
          {card.recommends.length > 0 && (
            <div style={{ color: theme.primary, fontWeight: 500, display: 'flex', flexWrap: 'wrap', gap: '4px' }}>
              #추천어코드 {card.recommends.map(acc => (
                <span
                  key={acc.name}
                  onClick={() => onAccordClick?.(acc.name)}
                  style={{ cursor: onAccordClick ? 'pointer' : 'default', textDecoration: onAccordClick ? 'underline' : 'none' }}
                >
                  #{acc.name}
                </span>
              ))}
            </div>
          )}
          {card.avoids.length > 0 && (
            <div style={{ color: theme.secondary, fontWeight: 500, marginTop: '4px', wordBreak: 'break-word', overflowWrap: 'break-word' }}>#기피어코드 {card.avoids.map(acc => `#${acc.name}`).join(' ')}</div>
          )}
        </div>
        <div style={{ display: 'flex', justifyContent: 'flex-end' }}>
          <button
            onClick={() => window.location.href = '/chat'}
            style={{
              background: 'none',
              border: 'none',
              padding: 0,
              color: theme.primary,
              fontSize: '14px',
              fontWeight: 700,
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: '4px'
            }}
          >
            나만의 향수 추천받기
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" style={{ marginLeft: '2px' }}>
              <path d="M5 12h14M12 5l7 7-7 7"/>
            </svg>
          </button>
        </div>
      </div>
      </div>
    </>
  );
};
