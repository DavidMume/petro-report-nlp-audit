"""Zero-shot AI-text detector scores (EXPLORATORY; methodology §23.4–23.6).

Three scores per passage, all computed from the same open-weight model pair:

- **Binoculars** (Hans et al., 2024): log-perplexity of the text under the
  *performer* model divided by the cross-perplexity between *observer* and
  *performer* next-token distributions, following the reference
  implementation (github.com/ahans30/Binoculars). Lower = more machine-like.
- **Fast-DetectGPT, analytic form** (Bao et al., 2024), with the observer as
  both sampling and scoring model: standardised difference between the
  text's log-likelihood and the expected log-likelihood under the model's
  own distribution. Higher = more machine-like.
- **Log-perplexity** under the observer, as a naive baseline.

Default pair: Qwen2.5-1.5B (observer) and Qwen2.5-1.5B-Instruct (performer),
which share a tokenizer and were trained on multilingual data including
Spanish. No score here is interpreted until `src.calibration` has measured
how each one behaves on Spanish human / generated controls.

Requires torch and transformers (see requirements-detectors.txt). The pure
functions on logits are tested without downloading any model.
"""

from __future__ import annotations

import math

MODEL_PAIRS = {
    "1.5B": ("Qwen/Qwen2.5-1.5B", "Qwen/Qwen2.5-1.5B-Instruct"),
    "0.5B": ("Qwen/Qwen2.5-0.5B", "Qwen/Qwen2.5-0.5B-Instruct"),
}
MAX_TOKENS = 512


# --- Pure scoring functions (torch tensors) ------------------------------------------------

def _shift(logits, ids):
    """Logits at position t predict token t+1."""
    return logits[:-1].float(), ids[1:]


def log_perplexity(logits, ids) -> float:
    import torch.nn.functional as F
    lg, tgt = _shift(logits, ids)
    return float(F.cross_entropy(lg, tgt, reduction="mean"))


def cross_perplexity(observer_logits, performer_logits, ids) -> float:
    """Mean over positions of −Σ_v p_observer(v) · log p_performer(v)."""
    import torch
    o, _ = _shift(observer_logits, ids)
    p, _ = _shift(performer_logits, ids)
    return float(-(torch.softmax(o, -1) * torch.log_softmax(p, -1)).sum(-1).mean())


def binoculars(observer_logits, performer_logits, ids) -> float:
    return log_perplexity(performer_logits, ids) / cross_perplexity(observer_logits, performer_logits, ids)


def fast_detectgpt_analytic(logits, ids) -> float:
    import torch
    lg, tgt = _shift(logits, ids)
    logp = torch.log_softmax(lg, -1)
    p = logp.exp()
    ll = logp.gather(-1, tgt.unsqueeze(-1)).squeeze(-1)
    mu = (p * logp).sum(-1)
    var = (p * logp.square()).sum(-1) - mu.square()
    return float((ll.sum() - mu.sum()) / var.sum().clamp_min(1e-12).sqrt())


def mean_entropy(logits, ids) -> float:
    import torch
    lg, _ = _shift(logits, ids)
    logp = torch.log_softmax(lg, -1)
    return float(-(logp.exp() * logp).sum(-1).mean())


# --- Models ---------------------------------------------------------------------------------

def pick_device():
    """cuda/fp16, then Apple MPS/bf16 (Qwen2.5 can overflow in fp16), then
    CPU/bf16. Falls back to float32 on MPS when bf16 is not supported."""
    import torch
    if torch.cuda.is_available():
        return "cuda", torch.float16
    if getattr(torch.backends, "mps", None) and torch.backends.mps.is_available():
        try:
            torch.ones(2, device="mps", dtype=torch.bfloat16) @ torch.ones(2, device="mps", dtype=torch.bfloat16)
            return "mps", torch.bfloat16
        except Exception:
            return "mps", torch.float32
    return "cpu", torch.bfloat16


def _load_causal_lm(name: str, dtype):
    import transformers
    from transformers import AutoModelForCausalLM
    major, minor = (int(x) for x in transformers.__version__.split(".")[:2])
    kw = "dtype" if (major, minor) >= (4, 56) else "torch_dtype"  # `torch_dtype` was renamed in 4.56
    return AutoModelForCausalLM.from_pretrained(name, **{kw: dtype})


class ModelPair:
    """Observer + performer sharing one tokenizer."""

    def __init__(self, size: str = "1.5B", device: str | None = None, dtype=None):
        from transformers import AutoTokenizer
        obs_name, perf_name = MODEL_PAIRS[size]
        dev, dt = pick_device()
        self.device, self.dtype = device or dev, dtype or dt
        self.names = (obs_name, perf_name)
        self.tokenizer = AutoTokenizer.from_pretrained(obs_name)
        perf_tok = AutoTokenizer.from_pretrained(perf_name)
        if self.tokenizer.get_vocab() != perf_tok.get_vocab():
            raise ValueError("Observer and performer tokenizers differ; Binoculars needs a shared vocabulary.")
        self.observer = _load_causal_lm(obs_name, self.dtype).to(self.device).eval()
        self.performer = _load_causal_lm(perf_name, self.dtype).to(self.device).eval()

    @classmethod
    def tiny_random(cls, vocab_size: int = 260):
        """Dry-run pair: two small randomly initialised Qwen2 models and a byte
        tokenizer. Exercises the whole pipeline without downloading anything;
        its scores mean nothing."""
        import torch
        from transformers import Qwen2Config, Qwen2ForCausalLM
        self = cls.__new__(cls)
        cfg = Qwen2Config(vocab_size=vocab_size, hidden_size=32, intermediate_size=64, num_hidden_layers=2,
                          num_attention_heads=2, num_key_value_heads=1, max_position_embeddings=1024)
        torch.manual_seed(0)
        self.observer = Qwen2ForCausalLM(cfg).eval()
        torch.manual_seed(1)
        self.performer = Qwen2ForCausalLM(cfg).eval()
        self.device, self.dtype, self.names = "cpu", torch.float32, ("tiny-random-a", "tiny-random-b")
        self.tokenizer = ByteTokenizer()
        return self

    def encode(self, text: str, max_tokens: int = MAX_TOKENS):
        import torch
        ids = self.tokenizer.encode(text, add_special_tokens=False)[:max_tokens]
        return torch.tensor(ids, dtype=torch.long)

    def score(self, text: str, max_tokens: int = MAX_TOKENS) -> dict:
        import torch
        ids = self.encode(text, max_tokens)
        if len(ids) < 16:
            return {"n_tokens": len(ids)}
        with torch.no_grad():
            x = ids.unsqueeze(0).to(self.device)
            lo = self.observer(x).logits[0].float().cpu()
            lp = self.performer(x).logits[0].float().cpu()
        out = {
            "n_tokens": int(len(ids)),
            "logppl_observer": log_perplexity(lo, ids),
            "logppl_performer": log_perplexity(lp, ids),
            "xppl": cross_perplexity(lo, lp, ids),
            "entropy_observer": mean_entropy(lo, ids),
            "fast_detectgpt": fast_detectgpt_analytic(lo, ids),
        }
        out["binoculars"] = out["logppl_performer"] / out["xppl"]
        # A non-finite score (numerical overflow) is kept as NaN and reported, never silently replaced.
        out["nonfinite"] = not all(math.isfinite(v) for v in out.values())
        return out


class ByteTokenizer:
    def encode(self, text: str, add_special_tokens: bool = False) -> list[int]:
        return list(text.encode("utf-8"))
