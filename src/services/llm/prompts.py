from typing import List

RAG_SYSTEM_PROMPT = (
    "You are a careful assistant that answers questions using ONLY the context provided below. "
    "If the context does not contain enough information to answer, say: *I don't have enough information in the provided context.* "
    "When you use a piece of context, cite it inline with its bracketed number, e.g. [1], [2]."
)


def build_rag_messages(query: str, chunks: List[str]) -> List[dict]:
    """Messages for a strictly context-grounded answer over retrieved chunks."""
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
        {"role": "system", "content": RAG_SYSTEM_PROMPT},
        {"role": "user", "content": user_prompt},
    ]
