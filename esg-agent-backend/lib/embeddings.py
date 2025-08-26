import numpy as np
import faiss

def embed(texts):
    # MOCK: stable fake embeddings via hash
    vecs = []
    for t in texts:
        rng = np.random.default_rng(abs(hash(t)) % (2**32))
        vecs.append(rng.standard_normal(384).astype("float32"))
    return np.vstack(vecs)

def build_faiss_index(vecs):
    dim = vecs.shape[1]
    index = faiss.IndexFlatIP(dim)
    faiss.normalize_L2(vecs)
    index.add(vecs)
    return index

def search(index, vec, k=5):
    faiss.normalize_L2(vec)
    D, I = index.search(vec, k)
    return I[0].tolist(), D[0].tolist()