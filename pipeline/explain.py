"""Plain-language explanations for each value bet.

Two implementations behind one interface:
  - TemplateExplainer: deterministic, offline, no API key. Always available.
  - LLMExplainer: calls a free OpenAI-compatible chat API (default Groq) to rewrite the
    numbers into a friendly paragraph, with on-disk caching and graceful fallback to the
    template on any error (missing key, network, rate limit).

build_explainer(settings) picks the LLM one when enabled AND a key is present, else the
template. explain_bet(...) is what the pipeline calls per flagged bet.
"""
from __future__ import annotations
import hashlib
import json
import logging
import os
import requests

log = logging.getLogger(__name__)


def _pct(x: float) -> str:
    return f"{100.0 * x:.1f}%"


def template_explanation(bet: dict) -> str:
    """Deterministic explanation from the bet's own numbers — no external service."""
    sel = bet["selection"]
    line = f" {bet['line']}" if bet.get("line") is not None else ""
    market = {"h2h": "match result", "totals_goals": "total goals",
              "totals_corners": "total corners"}.get(bet["market"], bet["market"])
    matchup = f"{bet.get('home', '')} v {bet.get('away', '')}".strip(" v")
    return (
        f"On {matchup} ({market}), our model gives {sel}{line} a "
        f"{_pct(bet['model_prob'])} chance, while the de-vigged market price implies only "
        f"{_pct(bet['fair_prob'])} - an edge of {_pct(bet['edge'])}. The best available "
        f"price is {bet['best_odds']} at {bet['book']}, which makes this a "
        f"+{bet['ev'] * 100:.1f}% expected-value bet. A bet is flagged only when our "
        f"estimated probability beats what the market is charging for it."
    )


_SYSTEM = (
    "You explain sports-betting value picks to a beginner in plain English. "
    "Use 2-3 short sentences. Explain WHY it is a value bet: our model's probability is "
    "higher than the bookmaker's de-vigged implied probability, so the offered odds are "
    "generous. Mention the best price and book. Be factual and calm, never hype, never "
    "promise winnings. Do not give financial advice or mention staking."
)


def _user_prompt(bet: dict) -> str:
    return (
        f"Match: {bet.get('home', '')} vs {bet.get('away', '')}\n"
        f"Market: {bet['market']} | Selection: {bet['selection']} "
        f"| Line: {bet.get('line')}\n"
        f"Model probability: {_pct(bet['model_prob'])}\n"
        f"Market fair (de-vigged) probability: {_pct(bet['fair_prob'])}\n"
        f"Edge: {_pct(bet['edge'])} | Expected value: +{bet['ev'] * 100:.1f}%\n"
        f"Best odds: {bet['best_odds']} at {bet['book']}\n"
        "Write the explanation."
    )


class TemplateExplainer:
    def explain(self, bet: dict) -> str:
        return template_explanation(bet)


class LLMExplainer:
    def __init__(self, base_url: str, api_key: str, model: str, cache_dir: str) -> None:
        self.url = base_url.rstrip("/") + "/chat/completions"
        self.api_key = api_key
        self.model = model
        self.cache_dir = os.path.join(cache_dir, "llm_explanations")

    def _cache_path(self, bet: dict) -> str:
        sig = json.dumps({k: bet.get(k) for k in
                          ("market", "selection", "line", "model_prob", "fair_prob",
                           "best_odds", "book", "home", "away")}, sort_keys=True)
        key = hashlib.sha256((self.model + sig).encode()).hexdigest()
        return os.path.join(self.cache_dir, key + ".txt")

    def explain(self, bet: dict) -> str:
        os.makedirs(self.cache_dir, exist_ok=True)
        path = self._cache_path(bet)
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as fh:
                return fh.read()
        try:
            resp = requests.post(
                self.url,
                headers={"Authorization": f"Bearer {self.api_key}",
                         "Content-Type": "application/json"},
                json={"model": self.model, "temperature": 0.3,
                      "messages": [{"role": "system", "content": _SYSTEM},
                                   {"role": "user", "content": _user_prompt(bet)}]},
                timeout=30)
            resp.raise_for_status()
            text = resp.json()["choices"][0]["message"]["content"].strip()
            if not text:
                raise ValueError("empty LLM response")
            with open(path, "w", encoding="utf-8") as fh:
                fh.write(text)
            return text
        except Exception as exc:  # noqa: BLE001 - never let explanations break the pipeline
            log.warning("LLM explanation failed (%s); using template fallback", exc)
            return template_explanation(bet)


def build_explainer(settings):
    if settings.llm_enabled and settings.llm_api_key:
        return LLMExplainer(settings.llm_base_url, settings.llm_api_key,
                            settings.llm_model, settings.cache_dir)
    return TemplateExplainer()
