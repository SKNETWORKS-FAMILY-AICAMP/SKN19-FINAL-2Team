import { useState, useEffect, useCallback } from 'react';
import { nmapService } from './nmap-service';
import { NMapResponse } from './types';
import { GRAPH_CONFIG } from '@/app/perfume-network/config';

/**
 * 향수 맵(NMap) 데이터 및 상태를 관리하는 커스텀 훅
 */
export const useNMap = (memberId?: number) => {
  const [data, setData] = useState<NMapResponse | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  // 분석 옵션 상태 (config의 기본값 사용)
  const [options, setOptions] = useState({
    minSimilarity: GRAPH_CONFIG.MIN_SIMILARITY_DEFAULT,
    topAccords: GRAPH_CONFIG.TOP_ACCORDS_DEFAULT,
    maxPerfumes: GRAPH_CONFIG.API_MAX_PERFUMES || 100,
  });

  /**
   * 향수 맵 데이터 가져오기
   */
  const fetchNMapData = useCallback(async () => {
    try {
      setIsLoading(true);
      setError(null);
      const result = await nmapService.getNMapResult({
        memberId,
        minSimilarity: options.minSimilarity,
        topAccords: options.topAccords,
        maxPerfumes: options.maxPerfumes,
      });
      setData(result);
    } catch (err) {
      console.error('Error fetching NMap data:', err);
      setError('향수 맵 데이터를 불러오는 데 실패했습니다.');
    } finally {
      setIsLoading(false);
    }
  }, [memberId, options]);

  /**
   * 옵션 변경 함수
   */
  const updateOptions = (newOptions: Partial<typeof options>) => {
    setOptions((prev) => ({ ...prev, ...newOptions }));
  };

  // 초기 데이터 로드
  useEffect(() => {
    fetchNMapData();
  }, [fetchNMapData]);

  return {
    data,
    isLoading,
    error,
    options,
    updateOptions,
    refresh: fetchNMapData,
  };
};
