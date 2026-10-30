from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

CATEGORIES = ("CATEGORY_1_SCHOLARSHIP", "CATEGORY_2_COOP_PARTTIME", "CATEGORY_3_FULLTIME")
Category = Literal["CATEGORY_1_SCHOLARSHIP", "CATEGORY_2_COOP_PARTTIME", "CATEGORY_3_FULLTIME"]
Tri = Literal["yes", "no", "unknown"]


class OpportunityItem(BaseModel):
    category: Category
    title: str
    organization: str = ""
    location: str = ""
    url: str
    deadline: str = ""
    funding: str = ""
    moi_accepted: Tri = "unknown"
    gre_required: Tri = "unknown"
    notes: str = ""


class SourceItem(BaseModel):
    name: str
    type: str = Field(description="portal | job_board | telegram | x_account | youtube | rss | api | other")
    url: str
    region: str = ""
    category: str = ""
    update_frequency: str = ""
    access_method: str = Field(default="", description="rss | api | static_html | js_required | login_required")
    scraping_notes: str = ""
    language: str = ""
    quality: int | None = None
