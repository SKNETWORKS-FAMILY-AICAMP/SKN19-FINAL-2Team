# 현재 시스템 아키텍처 및 로직 흐름 (AS-IS)

> 2026-01-11 기준 Scentence 시스템의 LangGraph 동작 방식입니다.

## 1. 전체 흐름도 (High Level Flow)

```mermaid
graph TD
    User[사용자 입력] --> Supervisor[Supervisor (라우터)]
    
    Supervisor -- "검색 필요 (완벽한 쿼리)" --> Researcher[Researcher (검색/전략)]
    Supervisor -- "정보 부족/문맥 필요" --> Interviewer[Interviewer (질문/요약)]
    Supervisor -- "잡담/인사" --> Writer[Writer (응답/리포트)]
    
    Researcher -- "검색 결과" --> Writer
    Interviewer -- "정보 충분" --> Researcher
    Interviewer -- "정보 부족 (재질문)" --> End[답변 출력]
    
    Writer --> End
```

## 2. 노드별 상세 로직

### 📡 1. Supervisor (Router)
- **역할**: 사용자의 첫 발화를 듣고 어디로 보낼지 결정합니다.
- **판단 기준**:
    1. **Researcher**: 문맥 없이도 바로 검색 가능한 경우 (예: "샤넬 향수 추천해줘")
    2. **Interviewer**: 추가 질문이 필요하거나 문맥 파악이 필요한 경우 (예: "시크한 거 어때?")
    3. **Writer**: 인사, 잡담, 종료 요청.
- **한계점 (Critical)**: **이전 대화를 보지 않습니다.** ("겨울"이라고만 하면 계절인지 겨울왕국인지 구분 못함)

### 🎤 2. Interviewer (Context Manager)
- **역할**: 사용자의 모호한 요구사항을 구체화하고 정보를 수집합니다.
- **동작**:
    1. **정보 추출**: 사용자 발화를 요약하여 `interview_context`(Text)에 누적합니다.
    2. **판단**: 정보가 충분한지(`is_sufficient`) 판단합니다.
    3. **질문 생성**: 부족하면 되묻는 질문을 생성합니다.
- **한계점**: 정보를 줄글(String)로 관리하여 체계적인 데이터 관리(Slot Filling)가 되지 않음.

### 🕵️ 3. Researcher (Strategist)
- **역할**: 수집된 요구사항을 바탕으로 검색 전략을 짜고 DB를 조회합니다.
- **동작**:
    1. **메타 데이터 로딩**: DB에서 현재 유효한 시즌, 브랜드 등의 목록을 가져옵니다.
    2. **전략 수립**: 3가지 추천 전략(SQL 쿼리 포함)을 생성합니다.
    3. **검색**: Vector DB(뉘앙스) + RDB(필터) 하이브리드 검색을 수행합니다.

### ✍️ 4. Writer (Responder)
- **역할**: 최종 답변을 작성하거나 테스트 리포트를 생성합니다.
- **동작**:
    1. **답변 작성**: 검색 결과를 바탕으로 사용자에게 추천 멘트를 작성합니다.
    2. **앵무새 방지**: 검색 결과가 없어도 스몰토크일 경우 자연스럽게 대처합니다.
    3. **테스트 리포트**: `/t` 명령어로 진입했을 경우, `test_reports/` 폴더에 결과를 저장합니다.
