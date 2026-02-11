// 향수 네트워크 설정
import type { LucideIcon } from "lucide-react";
import {
  PawPrint,
  Waves,
  LeafyGreen,
  Citrus,
  Milk,
  Earth,
  Flower2,
  Feather,
  Cherry,
  CakeSlice,
  Sprout,
  Handbag,
  MoonStar,
  Cloud,
  Droplet,
  FlameKindling,
  Flame,
  Candy,
  Beaker,
  TreePine,
  Wind,
} from "lucide-react";

// API 설정
export const API_CONFIG = {
  BASE_URL: "/api/scentmap",
} as const;

// 그래프 설정
export const GRAPH_CONFIG = {
  // API 파라미터 (필터링용)
  MIN_SIMILARITY_DEFAULT: 0.65, // 유사도 임계값 기본값 (0.0 ~ 1.0)
  MIN_SIMILARITY_MIN: 0.0, // 유사도 최소값
  MIN_SIMILARITY_MAX: 1.0, // 유사도 최대값
  MIN_SIMILARITY_STEP: 0.05, // 유사도 조절 단위
  
  TOP_ACCORDS_DEFAULT: 3, // 향수당 표시할 어코드 수 기본값
  TOP_ACCORDS_MIN: 1, // 어코드 최소 개수
  TOP_ACCORDS_MAX: 5, // 어코드 최대 개수
  
  API_MAX_PERFUMES: 300, // [개선] API에서 가져올 최대 향수 개수 (300개로 제한하여 성능 향상)
  
  // 물리 엔진 설정
  PHYSICS: {
    STABILIZATION_ITERATIONS: 150, // 안정화 반복 횟수
    UPDATE_INTERVAL: 25, // 업데이트 간격 (ms)
    MIN_VELOCITY: 0.01, // 최소 속도 (더 작게 = 더 빨리 안정화)
    MAX_VELOCITY: 0.3, // 최대 속도 (더 작게 = 부드러운 움직임)
    GRAVITATIONAL_CONSTANT: -50, // 중력 상수 (작게 = 노드들이 더 가까이)
    SPRING_LENGTH: 80, // 스프링 길이 (짧게 = 어코드 근처에 향수 배치)
    SPRING_CONSTANT: 0.08, // 스프링 상수 (강하게 = 구조 유지)
    DAMPING: 0.95, // 감쇠 계수 (높게 = 빠른 안정화)
    AVOID_OVERLAP: 1.0, // 겹침 방지
  },
  
  // 노드 크기 설정
  NODE_SIZE: {
    PERFUME: {
      DEFAULT: 24,
      SIMILAR: 26,
      SELECTED: 28,
    },
    ACCORD: {
      DEFAULT: 18,      // 향수보다 작게
      HIGHLIGHTED: 22,  // 강조시에도 향수보다 작게
    },
  },
  
  // 노드 질량 설정
  NODE_MASS: {
    PERFUME: 0.8, // 가볍게 (어코드 주변으로 끌림)
    ACCORD: 15, // 무겁게 (중심 유지)
  },
  
  // 애니메이션 설정
  ANIMATION: {
    FOCUS_SCALE: 1.5,
    FOCUS_OFFSET_X: -100,
    FOCUS_OFFSET_Y: 0,
    FOCUS_DURATION: 600,
    FIT_DURATION: 400,
  },
} as const;

// 분위기 계열별 기본 색상 매핑
export const ACCORD_COLORS: Record<string, string> = {
  Animal: "#7A5C3E",
  Aquatic: "#5FBED7",
  Chypre: "#3F6F5E",
  Citrus: "#E6E04A",
  Creamy: "#F1E8D6",
  Earthy: "#AD868B",
  Floral: "#F6B3C6",
  "Foug\\u00e8re": "#6F7A4A",
  Fougère: "#6F7A4A",
  Fruity: "#F39A4C",
  Gourmand: "#B97A4B",
  Green: "#4FA66A",
  Leathery: "#2E2B28",
  Oriental: "#7A3E2F",
  Powdery: "#E9CFCF",
  Resinous: "#4B6F8A",
  Smoky: "#7B7B7B",
  Spicy: "#9E3B32",
  Sweet: "#F4A3C4",
  Synthetic: "#7FA1D6",
  Woody: "#6B4F2A",
  Fresh: "#8FB5FF",
};

export const ACCORD_ICONS: Record<string, LucideIcon> = {
  Animal: PawPrint,
  Aquatic: Waves,
  Chypre: LeafyGreen,
  Citrus: Citrus,
  Creamy: Milk,
  Earthy: Earth,
  Floral: Flower2,
  "Foug\\u00e8re": Feather,
  Fougère: Feather,
  Fruity: Cherry,
  Gourmand: CakeSlice,
  Green: Sprout,
  Leathery: Handbag,
  Oriental: MoonStar,
  Powdery: Cloud,
  Resinous: Droplet,
  Smoky: FlameKindling,
  Spicy: Flame,
  Sweet: Candy,
  Synthetic: Beaker,
  Woody: TreePine,
  Fresh: Wind,
};

export const ACCORD_LABELS: Record<string, string> = {
  Animal: "애니멀",
  Aquatic: "아쿠아틱",
  Chypre: "시프레",
  Citrus: "시트러스",
  Creamy: "크리미",
  Earthy: "얼씨",
  Floral: "플로럴",
  "Foug\\u00e8re": "푸제르",
  Fougère: "푸제르",
  Fruity: "프루티",
  Gourmand: "구르망",
  Green: "그린",
  Leathery: "레더리",
  Oriental: "오리엔탈",
  Powdery: "파우더리",
  Resinous: "수지향",
  Smoky: "스모키",
  Spicy: "스파이시",
  Sweet: "스위트",
  Synthetic: "인공향",
  Woody: "우디",
  Fresh: "프레시",
};

export const ACCORD_DESCRIPTIONS: Record<string, string> = {
  Animal: "체온이 느껴지는 깊은 향, 살에 가까이 붙는 따뜻함, 은근히 관능적인 분위기",
  Aquatic: "바닷가에 서 있는 듯한 시원함, 바람에 실린 물 냄새, 맑고 차가운 느낌",
  Chypre: "숲속 땅을 밟았을 때의 냄새, 이끼와 흙이 섞인 차분함, 조용하지만 고급스러운 분위기",
  Citrus: "막 껍질을 깐 과일 향, 밝고 경쾌한 느낌, 처음 맡자마자 기분 좋아지는 상쾌함",
  Creamy: "부드럽고 포근한 느낌, 크림이나 우유 같은 질감, 자극 없이 편안한 달콤함",
  Earthy: "비 온 뒤 흙 냄새, 자연 그대로의 묵직함, 안정감 있는 차분한 분위기",
  Floral: "꽃이 만개한 정원 같은 향, 부드럽고 화사함, 로맨틱하고 밝은 인상",
  "Foug\\u00e8re": "숲속을 걷는 듯한 향, 풀과 나무가 섞인 자연스러움, 상쾌하면서도 단정한 느낌",
  Fougère: "숲속을 걷는 듯한 향, 풀과 나무가 섞인 자연스러움, 상쾌하면서도 단정한 느낌",
  Fruity: "잘 익은 과일 향, 달콤하고 생기 있는 느낌, 발랄하고 상큼한 분위기",
  Gourmand: "디저트가 떠오르는 향, 달콤하고 따뜻함, 고소하고 포근한 느낌",
  Green: "풀잎을 비볐을 때의 냄새, 생생하고 자연스러움, 인공적이지 않은 신선함",
  Leathery: "새 가죽 제품의 냄새, 단단하면서도 부드러움, 성숙하고 묵직한 인상",
  Oriental: "사막의 더운 느낌, 진하고 화려한 분위기, 밤에 잘 어울리는 향",
  Powdery: "파우더를 바른 듯한 향, 보송하고 부드러움, 차분하고 깨끗한 느낌",
  Resinous: "끈적한 나무 수액 같은 향, 진하고 따뜻함, 묵직하게 남는 잔향",
  Smoky: "불 근처에 있었던 옷 냄새, 그을린 듯한 느낌, 마초적인 분위기",
  Spicy: "코끝을 살짝 자극하는 향, 따뜻하고 생동감 있음, 향에 긴장감을 더해주는 느낌",
  Sweet: "설탕이나 꿀 같은 달콤함, 부드럽고 기분 좋아지는 향, 친근하고 따뜻한 분위기",
  Synthetic: "새 제품을 처음 열었을 때의 냄새, 또렷하고 인공적인 깨끗함, 현대적이고 세련된 느낌",
  Woody: "나무 가구나 숲을 떠올리게 하는 향, 단단하고 안정적인 느낌, 차분하고 무게감 있는 분위기",
  Fresh: "샤워 후처럼 깨끗한 느낌, 공기가 맑아진 듯한 향, 가볍고 시원한 분위기",
};

export const BRAND_LABELS: Record<string, string> = {
  "4711": "4711",
  "Acqua di Parma": "아쿠아 디 파르마",
  Amouage: "아무아주",
  "Ariana Grande": "아리아나 그란데",
  "Atelier Cologne": "아틀리에 코롱",
  Balenciaga: "발렌시아가",
  Bentley: "벤틀리",
  "Bond No 9": "본드 넘버 나인",
  "Bond No. 9": "본드 넘버 나인",
  BorntoStandOut: "본투스탠드아웃",
  "Bottega Veneta": "보테가 베네타",
  Boucheron: "부쉐론",
  Bulgari: "불가리",
  Burberry: "버버리",
  Byredo: "바이레도",
  "Calvin Klein": "캘빈 클라인",
  Celine: "셀린느",
  Chanel: "샤넬",
  Chloe: "끌로에",
  Clean: "클린",
  Clinique: "크리니크",
  Coach: "코치",
  Creed: "크리드",
  "D S  Durga": "디에스 앤 더가",
  Davidoff: "다비도프",
  Dior: "디올",
  Diptyque: "딥티크",
  "Dolce Gabbana": "돌체 가바나",
  "Estee Lauder": "에스티 로더",
  "Etat Libre D Orange": "에따 리브르 도랑쥬",
  "Etat Libre d Orange": "에따 리브르 도랑쥬",
  Ferrari: "페라리",
  Givenchy: "지방시",
  Goutal: "구탈",
  Gucci: "구찌",
  Guerlain: "겔랑",
  Hermes: "에르메스",
  "Hugo Boss": "휴고 보스",
  "Issey Miyake": "이세이 미야케",
  "Jean Paul Gaultier": "장 폴 고티에",
  "Jimmy Choo": "지미 추",
  "Jo Malone": "조 말론",
  "Jo Malone London": "조 말론 런던",
  "John Varvatos": "존 바바토스",
  Kenzo: "겐조",
  Kilian: "킬리안",
  "LArtisan Parfumeur": "라르티장 파퓸르",
  Lalique: "랄리크",
  Lancome: "랑콤",
  Lanvin: "랑방",
  "Lartisan Parfumeur": "라르티장 파퓸르",
  "Le Labo": "르 라보",
  "Loccitane En Provence": "록시땅 앙 프로방스",
  Loewe: "로에베",
  "Louis Vuitton": "루이 비통",
  Lush: "러쉬",
  "Maison Francis Kurkdjian": "메종 프란시스 커정",
  "Maison Margiela": "메종 마르지엘라",
  Mancera: "만세라",
  "Marc Jacobs": "마크 제이콥스",
  "Memo Paris": "메모 파리",
  "Mercedes Benz": "메르세데스 벤츠",
  "Michael Kors": "마이클 코어스",
  "Miller Harris": "밀러 해리스",
  "Miu Miu": "미우미우",
  Montale: "몽탈",
  Moschino: "모스키노",
  "Narciso Rodriguez": "나르시소 로드리게즈",
  Nishane: "니샤네",
  "Parfums de Marly": "파퓸 드 말리",
  "Penhaligon's": "펜할리곤스",
  Prada: "프라다",
  Rabanne: "라반",
  "Roja Parfums": "로자 퍼퓸",
  "Salvatore Ferragamo": "살바토레 페라가모",
  "Santa Maria Novella": "산타 마리아 노벨라",
  "Serge Lutens": "세르주 루텐",
  "The Body Shop": "더 바디샵",
  "Tiffany Co": "티파니",
  "Tiziana Terenzi": "티지아나 테렌치",
  "Tom Ford": "톰 포드",
  Valentino: "발렌티노",
  "Van Cleef Arpels": "반클리프 아펠",
  Versace: "베르사체",
  "Victoria S Secret": "빅토리아 시크릿",
  Xerjoff: "세르조프",
  "Yves Saint Laurent": "입생로랑",
  Zara: "자라",
};

export const SEASON_LABELS: Record<string, string> = {
  Spring: "봄",
  Summer: "여름",
  Fall: "가을",
  Winter: "겨울",
};

export const OCCASION_LABELS: Record<string, string> = {
  Business: "업무/비즈니스",
  Daily: "데일리",
  Evening: "저녁 모임",
  Leisure: "여가/휴식",
  "Night Out": "밤 외출",
  Sport: "운동",
};

export const GENDER_TARGET_LABELS: Record<string, string> = {
  Feminine: "여성",
  Masculine: "남성",
  Unisex: "남녀 공용",
};

// 유틸리티 함수
export const getAccordColor = (accord?: string): string =>
  (accord && ACCORD_COLORS[accord]) || "#E8DDCA";

export const hexToRgba = (hex: string, alpha: number): string => {
  const normalized = hex.replace("#", "");
  const full =
    normalized.length === 3
      ? normalized
          .split("")
          .map((char) => char + char)
          .join("")
      : normalized;
  const value = Number.parseInt(full, 16);
  const r = (value >> 16) & 255;
  const g = (value >> 8) & 255;
  const b = value & 255;
  return `rgba(${r}, ${g}, ${b}, ${alpha})`;
};

