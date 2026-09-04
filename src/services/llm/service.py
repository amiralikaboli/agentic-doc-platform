from typing import List

from src.services.llm.client import get_llm_client

SYSTEM_PROMPT = (
    "You are a careful assistant that answers questions using ONLY the context provided below. "
    "If the context does not contain enough information to answer, say: *I don't have enough information in the provided context.*"
    "When you use a piece of context, cite it inline with its bracketed number, e.g. [1], [2]."
)


class GenerationService:
    def __init__(self):
        self.client = get_llm_client()

    @staticmethod
    def _build_messages(query: str, chunks: List[str]) -> List[dict]:
        if chunks:
            context = "\n\n".join(f"[{i + 1}] {chunk}" for i, chunk in enumerate(chunks))
        else:
            context = "(no relevant context was retrieved for this question)"

        user_prompt = (
            f"Context:\n{context}\n\n"
            f"Question: {query}\n\n"
            f"Answer:"
        )

        return [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ]

    def generate(self, query: str, chunks: List[str]) -> str:
        messages = self._build_messages(query, chunks)
        return self.client.generate(messages)
