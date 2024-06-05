# installation (in a virtualenv):
# pip install fastapi uvicorn[standard] requests
# 
# execution:
# fastapi dev sources\app.py

import requests
from typing import List, Dict
from fastapi import FastAPI, Query, Request
from pydantic import BaseModel
from enum import Enum
from collections import defaultdict


app = FastAPI(
    title="My API",
    description="""Long description of the API, on multiple lines""",
    version="0.1.0",
    docs_url="/",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)


# available languages
class Language(Enum):
    FR = "fr-CH"
    DE = "de-CH"


class Interaction(BaseModel):
    id: str
    name: str
    mechanism: str


class Drug(BaseModel):
    gtin: str
    #name: str
    description: str | None = None
    interactions: list[Interaction]


STORE: dict[Drug] = {}


@app.get("/interactions_multiple_gtins", response_model=List[Interaction])
def get_interactions_multiple_gtins(
    gtins: str = Query(description="drug GTINs, separated by commas", example="7680612850014,7680531140760"),
    language: Language = Query(default=Language.FR)
) -> List[Drug]:
    gtin_list = gtins.split(',')
    all_drugs = []

    interaction_count: Dict[str, int] = defaultdict(int)
    interaction_map: Dict[str, Interaction] = {}

    for gtin in gtin_list:
        response = requests.get(
            f"https://documedis.hcisolutions.ch/2020-01/api/products/{gtin}?IdType=gtin",
            headers={"Accept-Language" : language.value}
        )
        response.raise_for_status()
        data = response.json()

        interactions = [
            get_interaction(drugInteraction)
            for drugInteraction in data["components"][0]["substances"][0]["drugInteractions"]
        ]

        for interaction in interactions:
            interaction_count[interaction.id] += 1
            interaction_map[interaction.id] = interaction

    repeated_interactions = [
        interaction for interaction_id, count in interaction_count.items() if count > 1
        for interaction in [interaction_map[interaction_id]]
    ]

    if not repeated_interactions:
        return [Interaction(id="0", name="No interaction found", mechanism="")]

    return repeated_interactions


@app.get("/data_single_gtin", response_model=Drug)
def get_data_single_gtin(
    gtin: str = Query(description="drug GTIN", example="7680612850014"),
    language: Language = Query(default=Language.FR)
) -> Drug:
    response = requests.get(
        f"https://documedis.hcisolutions.ch/2020-01/api/products/{gtin}?IdType=gtin",
        headers={"Accept-Language" : language.value}
    )
    response.raise_for_status()
    data = response.json()

    interactions = [
        get_interaction(drugInteraction)
        for drugInteraction in data["components"][0]["substances"][0]["drugInteractions"]
    ]

    drug = Drug(
        gtin=gtin,
        #name=data["name"],
        description=data["description"]["description"],
        interactions=interactions
    )

    return drug


def get_interaction(drugInteraction) -> Interaction:
    return Interaction(id=drugInteraction["id"], name=drugInteraction["title"], mechanism=drugInteraction["mechanismText"]) 
