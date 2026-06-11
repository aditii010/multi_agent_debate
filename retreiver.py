import re
from collections import Counter


class EvidenceRetriever:
    

    def __init__(self, docs: list[str], collection_name: str = "debate_context"):
        self.docs = docs

    def _score(self, doc: str, query: str) -> float:
        query_terms = set(re.findall(r'\w+', query.lower()))
        doc_terms = re.findall(r'\w+', doc.lower())
        doc_freq = Counter(doc_terms)
        return sum(doc_freq.get(term, 0) for term in query_terms)

    def retrieve(self, query: str, n_results: int = 3) -> list[str]:
        if not self.docs:
            return []
        scored = [(self._score(doc, query), doc) for doc in self.docs]
        scored.sort(key=lambda x: x[0], reverse=True)
        return [doc for _, doc in scored[:n_results]]

    def retrieve_for_side(self, question: str, side: str, n_results: int = 3) -> list[str]:
        angle = "supporting reasons benefits cost savings" if side == "proponent" else "risks drawbacks alternatives problems"
        query = f"{question} {angle}"
        return self.retrieve(query, n_results)
