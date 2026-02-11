
import logging
import sys
import os

# Ensure we can import from the current directory
sys.path.append(os.getcwd())

from agent.database import PerfumeRepository
from agent.graph import analyze_user_query

# Setup logging
logging.basicConfig(level=logging.INFO)


def test_recognition(user_text):
    print(f"\nTesting query: '{user_text}'")
    repo = PerfumeRepository()
    print(f"Repository loaded with {repo.count} perfumes.")

    # Debug: Check explicit calls
    print("Debug: find_brand_candidates('샤넬')...")
    brands = repo.find_brand_candidates("샤넬")
    print(f"  Result: {brands}")

    print("Debug: find_perfume_candidates('느와르')...")
    cands = repo.find_perfume_candidates("느와르")
    print(f"  Result: {[(p.perfume_name, p.perfume_brand, s) for p, s, k in cands]}")

    analysis = analyze_user_query(user_text, repo)
    
    print("Detected perfumes:")
    if not analysis.detected_perfumes:
        print("  None")
    for p in analysis.detected_perfumes:
        print(f"  - {p.perfume_brand} : {p.perfume_name} (Score: {p.match_score:.4f}, Matched: '{p.matched_text}')")

if __name__ == "__main__":
    # Test case that is currently failing (picking Tom Ford Noir instead of Chanel)
    test_recognition("샤넬 느와르랑 어울리는 향수 추천해줘")
    
    # Control cases
    test_recognition("Tom Ford Noir")
    test_recognition("Chanel No 5")
