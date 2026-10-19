"""Load predictor subject config + topic taxonomy."""
from __future__ import annotations
import math
from dataclasses import dataclass
from pathlib import Path

import yaml

from .env import REPO_ROOT


@dataclass(frozen=True)
class Topic:
    id: str
    code: str
    name: str
    descriptors: list[str]


class PredictorConfig:
    def __init__(self, raw: dict, path: Path):
        self.raw = raw
        self.path = path
        self.code: str = raw["subject"]["code"]
        self.name: str = raw["subject"]["name"]
        self.processed_dir: str = raw["subject"]["processed_dir"]
        self.window = raw.get("window", {"start_year": 2015, "end_year": 2026})
        self.spec_eras: list[dict] = raw["spec_eras"]
        self.session_weights: dict = raw.get("session_weights", {})
        self.recency_half_life: float = float(raw.get("recency_half_life_years", 3.0))
        self.target: dict = raw["target"]
        self.papers: list[dict] = raw["papers"]
        self.include_retakes: bool = raw.get("include_retakes", True)
        self.llm: dict = raw.get("llm", {})
        self.topics: list[Topic] = self._load_topics(raw["topics_source"])
        self.topic_by_id = {t.id: t for t in self.topics}

    def _load_topics(self, rel: str) -> list[Topic]:
        data = yaml.safe_load((REPO_ROOT / rel).read_text(encoding="utf-8"))
        out: list[Topic] = []
        for t in data.get("topics", []):
            descs: list[str] = []
            for bucket in ("core", "support"):
                for item in t.get(bucket, []) or []:
                    if isinstance(item, dict) and item.get("text"):
                        descs.append(item["text"])
            out.append(Topic(id=str(t["id"]), code=t.get("code", str(t["id"])),
                             name=t["name"], descriptors=descs))
        return out

    # --- weighting helpers ---
    def spec_era_for(self, year: int) -> dict:
        for era in self.spec_eras:
            if era["start_year"] <= year <= era["end_year"]:
                return era
        return {"name": "unknown", "code": "?", "weight": 0.5}

    def session_weight(self, session: str) -> float:
        return float(self.session_weights.get(session, 1.0))

    def recency_weight(self, year: int) -> float:
        ref = int(self.target.get("year", 2026))
        gap = max(0, ref - year)
        return math.pow(0.5, gap / self.recency_half_life)

    def combined_weight(self, year: int, session: str) -> float:
        era = self.spec_era_for(year)
        return float(era["weight"]) * self.session_weight(session) * self.recency_weight(year)

    def in_window(self, year: int) -> bool:
        return self.window["start_year"] <= year <= self.window["end_year"]

    def topics_prompt_block(self) -> str:
        lines = []
        for t in self.topics:
            hint = "; ".join(t.descriptors[:4])
            lines.append(f'  "{t.id}" = {t.name} (e.g. {hint})')
        return "\n".join(lines)


def load_config(code_or_path: str) -> PredictorConfig:
    p = Path(code_or_path)
    if not p.exists():
        p = REPO_ROOT / "config" / "predictor" / f"{code_or_path}.yaml"
    raw = yaml.safe_load(p.read_text(encoding="utf-8"))
    return PredictorConfig(raw, p)
