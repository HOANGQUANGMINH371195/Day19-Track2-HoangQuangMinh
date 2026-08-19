"""Run the five bonus queries and optionally ask OpenAI for final answers."""
from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1]))
from agent import FeatureStoreAdapter, HybridMemoryAgent


def load_env() -> None:
    """Small dependency-free .env loader; existing shell env always wins."""
    env_file = Path(__file__).parents[1] / ".env"
    if not env_file.exists():
        return
    for raw in env_file.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def main() -> None:
    load_env()
    features = FeatureStoreAdapter(profiles={
        "u_001": {"preferred_language": "vi", "reading_speed_wpm": 245,
                  "topic_affinity": "cloud + security", "active_hours": "20:00-23:00"},
    })
    agent = HybridMemoryAgent(feature_store=features)
    agent.remember("Tôi đã đọc về Kubernetes, autoscaling và cách triển khai blue-green.")
    agent.remember("Ghi chú bảo mật: OAuth2, rotation của secret và nguyên tắc least privilege.")
    agent.remember("Tôi thích tài liệu tiếng Việt, nhưng các thuật ngữ cloud và security có thể để tiếng Anh.")

    queries = [
        "Tôi đã đọc gì về Kubernetes?",
        "Recommend đọc gì tiếp",
        "Tôi đang quan tâm gì gần đây?",
        "Tài liệu về tự động mở rộng hạ tầng?",
        "Cho tôi summary cloud security",
    ]
    for i, query in enumerate(queries, 1):
        print(f"\n[{i}] {query}")
        print(agent.answer(query))


if __name__ == "__main__":
    main()
