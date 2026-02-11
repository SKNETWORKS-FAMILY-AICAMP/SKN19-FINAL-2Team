import axios from 'axios';
import { API_CONFIG } from '@/app/perfume-network/config';
import { NMapResponse } from './types';

// 향수 맵 API
export const nmapService = {
  /**
   * 향수 맵 분석 결과 및 시각화 데이터 조회
   * @param params 조회 옵션 (memberId, maxPerfumes, minSimilarity, topAccords)
   */
  async getNMapResult(params: {
    memberId?: number;
    maxPerfumes?: number;
    minSimilarity?: number;
    topAccords?: number;
  } = {}): Promise<NMapResponse> {
    try {
      const response = await axios.get<NMapResponse>(`${API_CONFIG.BASE_URL}/nmap/result`, {
        params: {
          member_id: params.memberId,
          max_perfumes: params.maxPerfumes,
          min_similarity: params.minSimilarity,
          top_accords: params.topAccords,
        },
      });
      return response.data;
    } catch (error) {
      console.error('Failed to fetch NMap result:', error);
      throw error;
    }
  },

  /**
   * 향수 맵 필터링을 위한 옵션 목록 조회
   */
  async getFilterOptions(): Promise<any> {
    try {
      const response = await axios.get(`${API_CONFIG.BASE_URL}/nmap/filter-options`);
      return response.data;
    } catch (error) {
      console.error('Failed to fetch filter options:', error);
      throw error;
    }
  },
};
