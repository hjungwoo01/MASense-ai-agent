from rapidfuzz import process, fuzz
from .embeddings import embed, build_faiss_index, search

class Retriever:
    def __init__(self, chunks):
        self.chunks = chunks               # list[dict]: {"id","text","meta"}
        self.index = build_faiss_index(embed([c["text"] for c in chunks]))

    def query(self, q, k=5):
        # bag-of-words candidates
        texts = [c["text"] for c in self.chunks]
        bow = process.extract(q, texts, scorer=fuzz.token_sort_ratio, limit=10)
        # vector search
        vec = embed([q])
        I, D = search(self.index, vec, k=10)
        # merge unique top items favoring higher BOW and vector scores
        seen, results = set(), []
        for txt, score, idx in bow:
            cid = texts.index(txt)
            if cid not in seen:
                results.append(self.chunks[cid])
                seen.add(cid)
        for cid in I:
            if cid not in seen:
                results.append(self.chunks[cid])
                seen.add(cid)
        return results[:k]