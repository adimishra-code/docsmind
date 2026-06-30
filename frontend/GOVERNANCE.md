# Governance & Hallucination Analysis

The `HallucinationTracker.tsx` component is the cornerstone of DocsMind's AI Governance. It tracks "Faithfulness"—a metric defined in `app/services/rag/evaluator.py` (LLM-as-a-judge)—which evaluates if the AI generated claims that are not present in the retrieved context chunks. It highlights failures to cite sources, ensuring enterprise safety.
