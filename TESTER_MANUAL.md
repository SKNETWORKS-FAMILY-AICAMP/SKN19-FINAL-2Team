# 채팅창 '/t' 명령어 기반 테스트 기능 가이드

## 1. Goal Description
채팅창에서 `/t` 명령어를 통해 테스트 목적, 시나리오, 기대값을 입력하고 실행하면, 서버 내부에서 자동으로 리포트(Markdown)를 생성하는 기능을 복구합니다.  
기존의 서버 크래시 문제를 방지하기 위해 안전한 파싱 로직과 LangGraph 내부 상태(State) 관리를 통해 구현합니다. 터미널 스크립트 실행 없이 채팅만으로 테스트가 가능해집니다.

## 2. User Review Required
> [!IMPORTANT]
> - **파일 생성 위치**: Docker 컨테이너 내부(`/app`)에서 생성된 파일이 호스트(`backend/`)에 동기화되는지 확인되었습니다(`docker-compose.yml` 볼륨 마운트).
> - **커맨드 형식**: `/t [목적],[시나리오],[기대값] 실제질문` 형식을 따릅니다.

## 3. Proposed Changes

### Backend

#### [MODIFY] [`schemas.py`](file:///Users/souluk/SKN_19/skn19-final/scentence-system/Scentence/backend/schemas.py)
- **`State` TypedDict**: `test_info` 필드 추가 (테스트 메타데이터 저장용).

#### [MODIFY] [`graph.py`](file:///Users/souluk/SKN_19/skn19-final/scentence-system/Scentence/backend/graph.py)
- **`supervisor` 노드**:
    - 사용자 입력이 `/t`로 시작하는지 감지.
    - 정규식 또는 문자열 분리를 통해 `[목적],[시나리오],[기대값]` 파싱.
    - `test_info`를 State에 저장하고, `user_query`를 실제 질문으로 교체하여 다음 노드로 전달.
- **`writer` 노드**:
    - 응답 생성 후 `test_info`가 존재하는지 확인.
    - 존재할 경우, 토큰 사용량(`input_tokens`, `output_tokens`) 기반 비용 계산($1.75/$14.00).
    - `backend/test_reports` 디렉토리(컨테이너 내 `/app/test_reports`)의 `test_YYYY-MM-DD.md` 파일에 결과 행(Row) 추가.

## 4. Verification Plan

### Manual Verification via Chat
1. 웹 클라이언트 접속 (`http://localhost:3000`).
2. 채팅창 입력: 
   ```text
   /t [테스트목적],[시나리오],[기대값] 여름 향수 추천해줘
   ```
3. 챗봇 정상 응답 확인.
4. `backend/test_reports/test_YYYY-MM-DD.md` 파일이 생성되고 해당 내용이 한 줄 추가되었는지 확인.
5. 테스트 파일이 생성된 후, `backend/test_reports` 디렉토리에서 파일을 확인하여 테스트 결과가 정상적으로 기록되었는지 확인.
6. Ctrl(cmd) + shift + v 누르면 표 형식으으로 뜸.