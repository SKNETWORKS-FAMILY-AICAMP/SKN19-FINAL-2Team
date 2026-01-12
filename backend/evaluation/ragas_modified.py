import os
import json
import asyncio
import pandas as pd
from dotenv import load_dotenv
from tqdm.asyncio import tqdm
from pydantic import BaseModel, Field # Pydantic 추가

# 라이브러리 임포트
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate

load_dotenv()

# 1. 출력 구조 정의 (Pydantic 모델)
class EvaluationResult(BaseModel):
    fact_score: float = Field(description="팩트 정확도 점수 (0~1)")
    emotional_score: float = Field(description="감성적 근거 점수 (0~1)")
    reasoning: str = Field(description="평가 이유")

# 2. 커스텀 판사 프롬프트 설정
JUDGE_PROMPT = """
당신은 매우 엄격하고 객관적인 향수 서비스 품질 검수 전문가입니다. 
제공된 [데이터베이스 정보]와 [모델의 추천 답변]을 비교하여 다음 두 가지 지표를 0.1점 단위로 정밀 평가하세요.

### 1. Fact Accuracy (0.0 ~ 1.0)
DB에 기록된 사실 정보를 왜곡 없이 전달했는지 평가합니다.
- 1.0 (Perfect): 이름, 브랜드, 모든 성분 정보가 DB와 완벽히 일치함.
- 0.9 (Excellent): 정보는 정확하나, DB에 있는 핵심 성분 중 1~2개를 누락함.
- 0.7~0.8 (Good): 정보는 일치하나, DB에 없는 성분을 '추측성'으로 언급함. (예: "머스크가 들어있을 것 같은 포근함" - DB에 머스크 없음)
- 0.5 (Fair): 브랜드나 이름은 맞지만, 전혀 다른 향조로 설명함.
- 0.0~0.4 (Poor): 존재하지 않는 향수이거나 브랜드명을 틀림.

### 2. Emotional Grounding (0.0 ~ 1.0)
감성 수식어가 실제 성분(Note)에서 논리적으로 도출되었는지 평가합니다. (막연한 칭찬은 감점 대상입니다.)
- 1.0 (Specific): 특정 성분과 수식어가 1:1로 매우 정교하게 연결됨. (예: '알데하이드' -> '코끝을 찌르는 서늘한 공기')
- 0.8~0.9 (Plausible): 성분에서 유추 가능하지만 다소 일반적인 표현임. (예: '시트러스' -> '상큼하고 가벼운')
- 0.6~0.7 (Vague): 너무 포괄적이라 어떤 향수에나 붙일 수 있는 표현임. (예: '고급스럽고 매력적인')
- 0.4~0.5 (Weak): 성분과 수식어 사이의 연결 고리가 약함. (예: '로즈' 향인데 '차가운 도시' 느낌이라고 표현)
- 0.0~0.3 (Illogical): 성분과 정반대되는 느낌을 부여함. (예: '우디/레더' 성분인데 '투명하고 물기 어린'이라고 표현)

### 채점 원칙:
- 조금이라도 근거가 부족하면 1.0점 대신 0.8~0.9점을 부여하여 변별력을 확보하세요.
- 'Reasoning'에는 감점이 된 구체적인 단어나 문장을 명시하세요.

### 출력 형식 (반드시 아래 JSON 형식만 출력하세요):
{{
    "fact_score": 0.0,
    "emotional_score": 0.0,
    "reasoning": "0.1점 단위의 구체적 감점 사유 포함"
}}

[데이터베이스 정보]:
{context}

[모델의 추천 답변]:
{answer}
"""

async def run_custom_evaluation(csv_path):
    if not os.path.exists(csv_path):
        print(f"❌ 파일을 찾을 수 없습니다: {csv_path}")
        return

    df = pd.read_csv(csv_path)
    
    # .with_structured_output 에 정의한 Pydantic 모델을 전달합니다.
    judge_llm = ChatOpenAI(model="gpt-4o-mini", temperature=0).with_structured_output(EvaluationResult)
    prompt = ChatPromptTemplate.from_template(JUDGE_PROMPT)
    
    results = []

    print(f"🧐 커스텀 감성 지표 평가 시작 (총 {len(df)}건)...")

    for _, row in tqdm(df.iterrows(), total=len(df), desc="Judging"):
        try:
            chain = prompt | judge_llm
            # 이제 결과는 딕셔너리가 아닌 EvaluationResult 객체로 반환됩니다.
            eval_res = await chain.ainvoke({
                "context": row['retrieved_contexts'],
                "answer": row['response']
            })
            # 객체를 딕셔너리로 변환하여 리스트에 추가
            results.append(eval_res.dict())
        except Exception as e:
            print(f"⚠️ 개별 평가 중 에러 발생: {e}")
            results.append({"fact_score": 0, "emotional_score": 0, "reasoning": f"Error: {e}"})

    # 결과 합치기
    eval_df = pd.DataFrame(results)
    final_df = pd.concat([df, eval_df], axis=1)
    
    output_file = "backend/evaluation/custom_eval_result_final.csv"
    final_df.to_csv(output_file, index=False, encoding="utf-8-sig")
    print(f"✅ 평가 완료! 결과가 {output_file}에 저장되었습니다.")

if __name__ == "__main__":
    asyncio.run(run_custom_evaluation("backend/evaluation/evaluation_result.csv"))