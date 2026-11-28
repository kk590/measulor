"""Editable subscription tiers for the public pricing page.

Fill the six PADDLE_PRICE_ID_* env vars with live `pri_...` IDs from Paddle
(Catalog > Prices). Starter / Pro / Advanced × month / year.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Dict, List, Literal, TypedDict


class PriceIds(TypedDict):
    month: str
    year: str


class TierDict(TypedDict):
    name: Literal["Starter", "Pro", "Advanced"]
    description: str
    features: List[str]
    priceId: PriceIds
    highlighted: bool


@dataclass(frozen=True)
class Tier:
    name: Literal["Starter", "Pro", "Advanced"]
    description: str
    features: List[str]
    price_id_month: str
    price_id_year: str
    highlighted: bool = False

    def to_public(self) -> TierDict:
        return {
            "name": self.name,
            "description": self.description,
            "features": list(self.features),
            "priceId": {"month": self.price_id_month, "year": self.price_id_year},
            "highlighted": self.highlighted,
        }


def load_tiers() -> List[Tier]:
    """Build tiers from environment. Empty price IDs mean that plan is not ready yet."""
    return [
        Tier(
            name="Starter",
            description="For solo designers and small ateliers getting started with photo intake.",
            features=[
                "Up to 50 client scans / month",
                "Front-photo body measurements",
                "Export results as table",
                "Email support",
            ],
            price_id_month=os.environ.get("PADDLE_PRICE_ID_STARTER_MONTH", "").strip(),
            price_id_year=os.environ.get("PADDLE_PRICE_ID_STARTER_YEAR", "").strip(),
        ),
        Tier(
            name="Pro",
            description="For tailor shops that need steady daily intake and digital client records.",
            features=[
                "Unlimited client scans",
                "Height auto-estimated from pose",
                "Priority support",
                "Shareable measurement summaries",
                "Best for busy shop floors",
            ],
            price_id_month=os.environ.get(
                "PADDLE_PRICE_ID_PRO_MONTH",
                os.environ.get("PADDLE_PRICE_ID", ""),
            ).strip(),
            price_id_year=os.environ.get("PADDLE_PRICE_ID_PRO_YEAR", "").strip(),
            highlighted=True,
        ),
        Tier(
            name="Advanced",
            description="For design houses and multi-seat teams that need scale and control.",
            features=[
                "Everything in Pro",
                "Multi-seat / team access",
                "API access (coming soon)",
                "Onboarding call",
                "Custom retention & SLA",
            ],
            price_id_month=os.environ.get("PADDLE_PRICE_ID_ADVANCED_MONTH", "").strip(),
            price_id_year=os.environ.get("PADDLE_PRICE_ID_ADVANCED_YEAR", "").strip(),
        ),
    ]


def all_price_ids() -> List[str]:
    ids: List[str] = []
    for tier in load_tiers():
        if tier.price_id_month:
            ids.append(tier.price_id_month)
        if tier.price_id_year:
            ids.append(tier.price_id_year)
    # de-dupe, keep order
    seen = set()
    out = []
    for i in ids:
        if i not in seen:
            seen.add(i)
            out.append(i)
    return out
