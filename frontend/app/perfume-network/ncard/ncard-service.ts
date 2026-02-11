/** **************************************************************
 * API 통신 
 ************************************************************** */
// MBTI 축별 분석
export interface MBTIComponent {
  axis: string;
  code: string;
  desc: string;
}

// 향기 어코드 상세
export interface AccordDetail {
  name: string;
  reason: string;
  notes?: string[];
}

// 향기 분석 카드 (메인)
export interface ScentCard {
  id: number;
  mbti: string;
  persona_title: string;
  image_url: string;
  keywords: string[];
  components: MBTIComponent[];
  recommends: AccordDetail[];
  avoids: AccordDetail[];
  story: string;
  summary: string;
}

// NMap 요약(payload) 기반 카드 생성용 타입
export interface GenerateCardPayload {
  top_notes: string[];
  middle_notes: string[];
  base_notes: string[];
  mood_keywords: string[];
  analysis_text?: string;
  representative_color?: string;
  member_id?: number;
  mbti?: string;
}

import { API_CONFIG } from '@/app/perfume-network/config';
import axios from 'axios';

// 향기 분석 카드 관련 API 통신 서비스
export const ncardService = {

  // 조회
  // 백엔드로부터 향기카드 리스트를 가져옴
  getScentCards: async (memberId: number): Promise<ScentCard[]> => {
    try {
      const response = await axios.get(`${API_CONFIG.BASE_URL}/ncard/`, {
        params: { member_id: memberId }
      });
      return response.data;
    } catch (error) {
      console.warn('Backend not reachable, using frontend dummy data');
      return [
        {
          id: 1,
          mbti: "INFJ",
          persona_title: "안개 낀 새벽의 호숫가",
          image_url: "/images/mbti/infj_space.png",
          keywords: ["신비로운", "깊이 있는", "고요한", "영적인", "서늘한"],
          components: [
            { axis: "존재방식", code: "I", desc: "피부에 밀착되어 은은하게 남는 내밀한 여운을 선호합니다." },
            { axis: "인식방식", code: "N", desc: "장면과 기억을 소환하는 추상적이고 서사적인 향에 끌립니다." },
            { axis: "감정질감", code: "F", desc: "감성을 자극하는 부드럽고 따뜻한 포근한 인상을 줍니다." },
            { axis: "취향안정성", code: "J", desc: "균형 잡힌 밸런스의 대중적이고 클래식한 조화를 추구합니다." }
          ],
          recommends: [
            { name: "Woody", reason: "깊고 고요한 통찰력을 닮은 묵직한 안정감을 줍니다.", notes: ["Sandalwood", "Cedarwood"] },
            { name: "Smoky", reason: "신비로운 실루엣처럼 지적인 분위기를 완성해 줍니다.", notes: ["Incense", "Patchouli"] }
          ],
          avoids: [
            { name: "Citrus", reason: "너무 밝은 에너지는 당신의 깊은 사색을 방해할 수 있습니다." }
          ],
          story: "당신의 내면은 [안개 낀 새벽의 호숫가]처럼 깊고 고요한 통찰력을 품고 있습니다. 오늘 선택하신 어코드의 조화는, 안개 사이로 비치는 나무의 신비로운 실루엣처럼 당신의 지적인 분위기를 더욱 완성해 줍니다.",
          summary: "신비롭고 깊이 있는 분위기가 당신을 빛나게 할 거예요. 우디와 스모키 어코드를 중심으로 향수를 찾아보는 걸 추천드려요!"
        }
      ];
    }
  },

  // 추가
  // 향수 맵 분석 데이터를 기반으로 실제 향기 카드를 생성하고 저장
  generateAndSaveCard: async (payload: string | GenerateCardPayload): Promise<ScentCard> => {
    try {
      if (typeof payload === "string") {
        // 세션 기반 카드 생성 API 호출 (세션에서 MBTI와 어코드 정보 자동 조회)
        const response = await axios.post(`${API_CONFIG.BASE_URL}/session/${payload}/generate-card`);
        return response.data.card;
      }

      // 요약(payload) 기반 카드 생성 (정식 백엔드 엔드포인트)
      const response = await axios.post(`${API_CONFIG.BASE_URL}/ncard/generate-from-summary`, payload);
      return response.data.card;
    } catch (error) {
      console.error('Failed to generate card:', error);
      throw error;
    }
  },

  // 카드 저장 (회원용)
  saveCard: async (sessionId: string, cardId: string, memberId: number): Promise<{ success: boolean; newSessionId?: string }> => {
    try {
      const response = await axios.post(`${API_CONFIG.BASE_URL}/session/${sessionId}/save-card`,
        { card_id: cardId },
        { params: { member_id: memberId } }
      );
      return {
        success: true,
        newSessionId: response.data.new_session_id
      };
    } catch (error) {
      console.error('Failed to save card:', error);
      return { success: false };
    }
  }
};
