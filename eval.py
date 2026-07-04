import sys
from src.generation.generator import answer_query

queries = [
    "What are the holdings of HDFC Large Cap Fund?",
    "What is the expense ratio of HDFC Large Cap Fund?",
    "What is the minimum SIP amount for HDFC Large Cap Fund?",
    "What are the 1 year returns of HDFC Large Cap Fund?",
    "What is the fund size (AUM) of HDFC Large Cap Fund?",
    "What is the NAV of HDFC Large Cap Fund?",
    "Who is the fund manager for HDFC Large Cap Fund?"
]

success = 0
for q in queries:
    print(f"\nQ: {q}")
    ans = answer_query(q)
    print(f"A: {ans}")
    if "I don't have this information" not in ans and "cannot provide financial advice" not in ans.lower():
        success += 1

print(f"\nSuccess Rate: {success}/{len(queries)}")
