# installation (in a virtualenv):
# pip install fastapi uvicorn[standard] requests
# 
# execution:
# fastapi dev sources\app.py

import requests
from typing import Any
from fastapi import FastAPI, Query, Request
from pydantic import BaseModel
from enum import Enum


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
    name: str
    description: str | None = None
    interactions: list[Interaction]


STORE: dict[Drug] = {}


# class Item(BaseModel):
#     name: str
#     description: str | None = None
#     price: float

# @app.post("/item", description="Store item", status_code=201)
# def create_item(item: Drug) -> Drug:
#     if item.name in STORE:
#         raise HTTPException(status_code=403, detail="Item already exists")
#     STORE[item.name] = item
#     return item

# @app.get("/item/{gtin}", description="Return item")
# def get_item(name: str) -> Drug:
#     if name not in STORE:
#         raise HTTPException(status_code=404, detail="Item not found")
#     return STORE[name]

# @app.delete("/item/{name}", description="Delete item")
# def delete_item(name: str) -> Drug:
#     if name not in STORE:
#         raise HTTPException(status_code=404, detail="Item not found")
#     return STORE.pop(name)



@app.get("/interactions_multiple_sources")
def get_interactions_multiple_sources(
    gtins: str = Query(description="drug GTINs, separated by commas", example="7680612850014,7680612850090"),
    language: Language = Query(default=Language.FR)
) -> list[list[Interaction]]:
    gtin_list = gtins.split(',')
    all_interactions = []

    for gtin in gtin_list:
        response = requests.get(
            f"https://documedis.hcisolutions.ch/2020-01/api/products/{gtin}?IdType=gtin",
            headers={"Accept-Language" : language.value}
        )
        response.raise_for_status()
        data = response.json()

        # print(data["components"][0]["substances"][0]["substance"])

        interactions = [
            get_interaction(drugInteraction)
            for drugInteraction in data["components"][0]["substances"][0]["drugInteractions"]
        ]
        all_interactions.append(interactions)

    return all_interactions


@app.get("/interactions_single_source")
def get_interactions_single_source(
    gtin: str = Query(description="drug GTIN", example="7680612850014"),
    language: Language = Query(default=Language.FR)
) -> list[Interaction]:
    response = requests.get(
        f"https://documedis.hcisolutions.ch/2020-01/api/products/{gtin}?IdType=gtin",
        headers={"Accept-Language" : language.value}
    )
    response.raise_for_status()
    data = response.json()

    # print(data["components"][0]["substances"][0]["substance"])

    return [
        get_interaction(drugInteraction)
        for drugInteraction in data["components"][0]["substances"][0]["drugInteractions"]
        #for drugInteraction in substance["drugInteractions"]
    ]


def get_interaction(drugInteraction) -> Interaction:
    return Interaction(id=drugInteraction["id"], name=drugInteraction["title"], mechanism=drugInteraction["mechanismText"]) 
