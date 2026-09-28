"""Topic modelling with several approaches, compared rather than trusted
individually:

1. TF-IDF + NMF (scikit-learn)
2. LDA on term counts (scikit-learn, batch variational Bayes)
3. Embedding clustering: k-means on paragraph embeddings (see
   src/embeddings.py for which embedding model was actually available),
   with class-based TF-IDF terms per cluster
4. BERTopic — attempted only if the package and a sentence-transformer model
   are available; otherwise recorded as "not run" with the reason.

The pipeline never names or interprets topics. It outputs representative
terms and example paragraphs (with page numbers) for a human to read.
The number of topics k is chosen by NPMI coherence over a sweep, and the
sweep itself is published (outputs/tables/topic_k_sweep.csv).
"""

from __future__ import annotations

import numpy as np
import pandas as pd

TOKEN_PATTERN = r"(?u)\b[^\s\d]{3,}\b"
SEED = 42


def _vectorizers(min_df: int = 3, max_df: float = 0.5):
    from sklearn.feature_extraction.text import CountVectorizer, TfidfVectorizer

    return (TfidfVectorizer(min_df=min_df, max_df=max_df, token_pattern=TOKEN_PATTERN, sublinear_tf=True),
            CountVectorizer(min_df=min_df, max_df=max_df, token_pattern=TOKEN_PATTERN))


def top_terms(components: np.ndarray, vocab: np.ndarray, n: int = 10) -> list[list[str]]:
    return [list(vocab[row.argsort()[::-1][:n]]) for row in components]


def npmi_coherence(topics: list[list[str]], texts: list[list[str]]) -> float:
    """Mean NPMI coherence (gensim c_npmi, sliding window 10)."""
    from gensim.corpora import Dictionary
    from gensim.models.coherencemodel import CoherenceModel

    d = Dictionary(texts)
    topics = [[w for w in t if w in d.token2id] for t in topics]
    topics = [t for t in topics if len(t) >= 3]
    cm = CoherenceModel(topics=topics, texts=texts, dictionary=d, coherence="c_npmi", window_size=10)
    return float(cm.get_coherence())


def fit_tfidf_nmf(docs: list[str], n_topics: int):
    from sklearn.decomposition import NMF

    tfidf, _ = _vectorizers()
    X = tfidf.fit_transform(docs)
    model = NMF(n_components=n_topics, random_state=SEED, init="nndsvda", max_iter=600)
    W = model.fit_transform(X)
    return model, W, np.array(tfidf.get_feature_names_out())


def fit_lda(docs: list[str], n_topics: int):
    from sklearn.decomposition import LatentDirichletAllocation

    _, cv = _vectorizers()
    X = cv.fit_transform(docs)
    model = LatentDirichletAllocation(n_components=n_topics, random_state=SEED, learning_method="batch",
                                      max_iter=60, doc_topic_prior=0.1, topic_word_prior=0.01)
    W = model.fit_transform(X)
    return model, W, np.array(cv.get_feature_names_out())


def fit_embedding_clusters(docs: list[str], embeddings: np.ndarray, n_clusters: int):
    """k-means on L2-normalised embeddings; cluster terms via class-based TF-IDF."""
    from sklearn.cluster import KMeans
    from sklearn.feature_extraction.text import CountVectorizer

    km = KMeans(n_clusters=n_clusters, random_state=SEED, n_init=20)
    labels = km.fit_predict(embeddings)
    cv = CountVectorizer(min_df=2, token_pattern=TOKEN_PATTERN)
    X = cv.fit_transform(docs)
    vocab = np.array(cv.get_feature_names_out())
    class_tf = np.vstack([np.asarray(X[labels == c].sum(axis=0)).ravel() for c in range(n_clusters)])
    tf = class_tf / np.maximum(class_tf.sum(axis=1, keepdims=True), 1)
    avg = class_tf.sum() / n_clusters
    idf = np.log(1 + avg / np.maximum(class_tf.sum(axis=0), 1))
    ctfidf = tf * idf
    # one-hot "doc-topic" matrix for a uniform interface
    W = np.zeros((len(docs), n_clusters))
    W[np.arange(len(docs)), labels] = 1.0
    return km, W, vocab, ctfidf


def fit_bertopic(docs: list[str]):
    """BERTopic requires a sentence-transformer model; returns (model, topics)
    or raises with the reason it could not run."""
    from bertopic import BERTopic  # noqa: F401  (ImportError is reported upstream)

    model = BERTopic(language="multilingual", calculate_probabilities=False, verbose=False)
    topics, _ = model.fit_transform(docs)
    return model, topics


def k_sweep(docs: list[str], texts: list[list[str]], ks=range(6, 15)) -> pd.DataFrame:
    rows = []
    for k in ks:
        m, _, vocab = fit_tfidf_nmf(docs, k)
        rows.append({"model": "tfidf_nmf", "k": k, "npmi": round(npmi_coherence(top_terms(m.components_, vocab), texts), 4)})
        m, _, vocab = fit_lda(docs, k)
        rows.append({"model": "lda", "k": k, "npmi": round(npmi_coherence(top_terms(m.components_, vocab), texts), 4)})
    return pd.DataFrame(rows)


def summarise_model(name: str, W: np.ndarray, components: np.ndarray, vocab: np.ndarray,
                    paras: pd.DataFrame, n_terms: int = 12, n_examples: int = 3):
    """Returns (summary rows, example rows, doc-topic rows)."""
    dominant = W.argmax(axis=1)
    weight = W.max(axis=1)
    summary, examples = [], []
    for t in range(components.shape[0]):
        idx = np.where(dominant == t)[0]
        summary.append({"model": name, "topic": t, "top_terms": ", ".join(vocab[components[t].argsort()[::-1][:n_terms]]),
                        "n_paragraphs_dominant": int(len(idx)),
                        "share_paragraphs": round(len(idx) / len(paras), 4),
                        "label": ""})  # intentionally blank: topics are not auto-labelled
        order = idx[np.argsort(-weight[idx])][:n_examples]
        for rank, i in enumerate(order, start=1):
            r = paras.iloc[i]
            examples.append({"model": name, "topic": t, "rank": rank, "paragraph_id": r.paragraph_id,
                             "page": int(r.page), "section": r.section, "weight": round(float(weight[i]), 4),
                             "excerpt": r.text[:400]})
    doc_topics = pd.DataFrame({"paragraph_id": paras.paragraph_id, "model": name,
                               "dominant_topic": dominant, "weight": np.round(weight, 4)})
    return summary, examples, doc_topics


def topics_by_section(doc_topics: pd.DataFrame, paras: pd.DataFrame) -> pd.DataFrame:
    d = doc_topics.merge(paras[["paragraph_id", "chapter", "level2"]], on="paragraph_id")
    t = d.groupby(["model", "chapter", "dominant_topic"]).size().rename("n").reset_index()
    t["share"] = (t.n / t.groupby(["model", "chapter"]).n.transform("sum")).round(4)
    return t


def model_agreement(doc_topics: pd.DataFrame) -> pd.DataFrame:
    """Pairwise agreement of dominant-topic assignments (ARI and NMI).
    Low agreement means the 'topics' are model-dependent — reported, not hidden."""
    from sklearn.metrics import adjusted_rand_score, normalized_mutual_info_score

    piv = doc_topics.pivot(index="paragraph_id", columns="model", values="dominant_topic").dropna()
    rows = []
    models = list(piv.columns)
    for i, a in enumerate(models):
        for b in models[i + 1:]:
            rows.append({"model_a": a, "model_b": b,
                         "adjusted_rand_index": round(adjusted_rand_score(piv[a], piv[b]), 4),
                         "normalized_mutual_info": round(normalized_mutual_info_score(piv[a], piv[b]), 4)})
    return pd.DataFrame(rows)


def build_concept_network(corpus_df: pd.DataFrame, terms: list[str]):
    from src.entities import build_concept_network as _b

    return _b(corpus_df, terms)
