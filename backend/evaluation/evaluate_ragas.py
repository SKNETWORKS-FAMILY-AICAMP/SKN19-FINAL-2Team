import os
import json
import asyncio
import pandas as pd
from datasets import Dataset
from ragas import evaluate
from ragas.metrics import (
    faithfulness,
    answer_relevancy,
    context_precision,
    context_recall,
)
from dotenv import load_dotenv
from tqdm.asyncio import tqdm

# --- [수정된 부분 1: 래퍼 임포트] ---
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from ragas.llms import LangchainLLMWrapper
from ragas.embeddings import LangchainEmbeddingsWrapper
# ------------------------------------

import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from graph import build_graph

load_dotenv()

async def run_evaluation():
    test_file = "backend/evaluation/test_set.json"
    with open(test_file, "r", encoding="utf-8") as f:
        test_data = json.load(f)

    # --- [수정된 부분 2: 객체를 Ragas 래퍼로 감싸기] ---
    # 1. 먼저 LangChain 객체 생성
    llm_obj = ChatOpenAI(model="gpt-4o-mini", temperature=0)
    emb_obj = OpenAIEmbeddings(model="text-embedding-3-small")

    # 2. Ragas 전용 래퍼로 감싸기 (에러 방지 핵심)
    eval_llm = LangchainLLMWrapper(llm_obj)
    eval_embeddings = LangchainEmbeddingsWrapper(emb_obj)
    # -----------------------------------------------
    
    workflow = build_graph()
    
    questions, answers, contexts, ground_truths = [], [], [], []

    print(f"🚀 총 {len(test_data)}개의 테스트 케이스 실행 시작...")

    for i, data in enumerate(tqdm(test_data, desc="Running Graph")):
        question = data["question"]
        ground_truth = data["ground_truth"]
        
        config = {"configurable": {"thread_id": f"eval_test_{i}"}}
        inputs = {"user_query": question}
        
        try:
            final_state = await workflow.ainvoke(inputs, config=config)
            answer = final_state.get("final_response", "")
            raw_research = final_state.get("research_result", "")
            
            individual_contexts = [c.strip() for c in raw_research.split("-------------------------") if c.strip()]
            
            questions.append(question)
            answers.append(answer if answer else "No answer generated")
            contexts.append(individual_contexts if individual_contexts else ["No context found"])
            ground_truths.append(ground_truth)
            
        except Exception as e:
            print(f"❌ 그래프 실행 에러: {e}")
            continue

    data_dict = {
        "question": questions,
        "answer": answers,
        "contexts": contexts,
        "ground_truth": ground_truths
    }
    dataset = Dataset.from_dict(data_dict)

    print("\n📊 Ragas 지표 계산 중...")
    try:
        # 수정된 eval_llm과 eval_embeddings를 전달
        result = evaluate(
            dataset,
            metrics=[
                faithfulness,
                answer_relevancy,
                context_precision,
                context_recall,
            ],
            llm=eval_llm,
            embeddings=eval_embeddings
        )

        df = result.to_pandas()
        print("\n[평가 결과 요약]")
        print(result)
        
        output_path = "backend/evaluation/evaluation_result.csv"
        df.to_csv(output_path, index=False, encoding="utf-8-sig")
        print(f"✅ 결과 저장 완료: {output_path}")

    except Exception as e:
        print(f"❌ Ragas 평가 에러: {e}")

if __name__ == "__main__":
    asyncio.run(run_evaluation())