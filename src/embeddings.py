"""Paragraph / section / claim embeddings and 2D projections for
exploratory visualisation only.

Preferred model: a multilingual sentence-transformer
(`paraphrase-multilingual-mpnet-base-v2`). If it cannot be loaded (e.g. the
execution environment blocks huggingface.co, as in the session that produced
the committed outputs), the code falls back to spaCy `es_core_news_lg` static
word vectors averaged per text (300-d, trained on Spanish web text), and the
method actually used is written to every output. Averaged word vectors are a
much weaker semantic representation than sentence transformers — results
built on them are labelled accordingly (RESEARCH_LOG 2026-09-28).

UMAP coordinates are for visual exploration only: 2D distances are NOT a
measurement of semantic distance.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

DEFAULT_EMBEDDING_MODEL = "paraphrase-multilingual-mpnet-base-v2"


def _l2(x: np.ndarray) -> np.ndarray:
    n = np.linalg.norm(x, axis=1, keepdims=True)
    n[n == 0] = 1.0
    return x / n


def embed_texts(texts: list[str], model_name: str = DEFAULT_EMBEDDING_MODEL) -> tuple[np.ndarray, str]:
    """Return (L2-normalised embedding matrix, method description)."""
    try:
        from sentence_transformers import SentenceTransformer

        model = SentenceTransformer(model_name)
        emb = model.encode(texts, batch_size=32, show_progress_bar=False, normalize_embeddings=True)
        return np.asarray(emb), f"sentence-transformers/{model_name}"
    except Exception:
        from src.preprocess import get_nlp

        nlp = get_nlp()
        vecs = []
        with nlp.select_pipes(enable=[]):
            for doc in nlp.pipe(texts, batch_size=64):
                toks = [t.vector for t in doc if t.has_vector and not t.is_stop and not t.is_punct and not t.like_num]
                vecs.append(np.mean(toks, axis=0) if toks else np.zeros(nlp.vocab.vectors_length))
        return _l2(np.vstack(vecs)), f"spaCy {nlp.meta['name']} averaged static word vectors (fallback)"


def paragraph_table(corpus_df: pd.DataFrame, min_words: int = 20) -> pd.DataFrame:
    """Paragraph-level texts rebuilt from the sentence corpus (keeps ids)."""
    g = corpus_df.groupby("paragraph_id", sort=False)
    p = g.agg(page=("page", "min"), chapter=("chapter", "first"), level2=("level2", "first"),
              section=("section", "first"), text=("clean_text", " ".join),
              lemma_text=("lemma_text", " ".join), n_words=("n_words", "sum")).reset_index()
    return p[p.n_words >= min_words].reset_index(drop=True)


def embed_paragraphs(paragraphs: pd.DataFrame) -> tuple[np.ndarray, str]:
    return embed_texts(paragraphs.text.tolist())


def embed_sections(paragraphs: pd.DataFrame, emb: np.ndarray) -> tuple[pd.DataFrame, np.ndarray]:
    """Section vectors = mean of their paragraph vectors (re-normalised)."""
    keys = paragraphs[["chapter", "level2"]].drop_duplicates().reset_index(drop=True)
    vecs = []
    for _, k in keys.iterrows():
        mask = ((paragraphs.chapter == k.chapter) & (paragraphs.level2 == k.level2)).values
        vecs.append(emb[mask].mean(axis=0))
    return keys, _l2(np.vstack(vecs))


def embed_claims(claims_df: pd.DataFrame) -> tuple[np.ndarray, str]:
    return embed_texts(claims_df.claim_text.tolist())


def project_umap(embeddings: np.ndarray, n_neighbors: int = 15, min_dist: float = 0.1,
                 random_state: int = 42) -> np.ndarray:
    import umap

    reducer = umap.UMAP(n_neighbors=n_neighbors, min_dist=min_dist, metric="cosine",
                        random_state=random_state)
    return reducer.fit_transform(embeddings)


def cosine_similarity_matrix(emb: np.ndarray) -> np.ndarray:
    e = _l2(emb)
    return e @ e.T
