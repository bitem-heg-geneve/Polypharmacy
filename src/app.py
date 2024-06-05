import requests
from typing import List, Dict
from fastapi import FastAPI, Query, Request
from pydantic import BaseModel
from enum import Enum
from collections import defaultdict


# Initialize FastAPI app
app = FastAPI(
    title="My API",
    description="""Long description of the API, on multiple lines""",
    version="0.1.0",
    docs_url="/",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

# Define Enum for "Accept-Language" header in the query to compendium
class Language(Enum):
    FR = "fr-CH"
    DE = "de-CH"

# Define model for drug interaction
class Interaction(BaseModel):
    id: str
    name: str
    mechanism: str

# Define model for drug
class Drug(BaseModel):
    gtin: str
    #name: str
    description: str | None = None
    interactions: list[Interaction]

# Store drugs by GTIN
STORE: dict[Drug] = {}


# Endpoint to get interactions for multiple GTINs
@app.get("/interactions_multiple_gtins", response_model=List[Interaction])
def get_interactions_multiple_gtins(
    gtins: str = Query(description="drug GTINs, separated by commas", example="7680612850014,7680531140760"),
    language: Language = Query(default=Language.FR)
) -> List[Drug]:
    # Split GTINs into list
    gtin_list = gtins.split(',')
    all_drugs = []

    # Count interactions and create interaction map
    interaction_count: Dict[str, int] = defaultdict(int)
    interaction_map: Dict[str, Interaction] = {}

    # Fetch data from compendium for each GTIN
    for gtin in gtin_list:
        response = requests.get(
            f"https://documedis.hcisolutions.ch/2020-01/api/products/{gtin}?IdType=gtin",
            headers={"Accept-Language" : language.value}
        )
        response.raise_for_status()
        data = response.json()

        # Extract drug interactions from response
        interactions = [
            get_interaction(drugInteraction)
            for drugInteraction in data["components"][0]["substances"][0]["drugInteractions"]
        ]

        # Update interaction count and map
        for interaction in interactions:
            interaction_count[interaction.id] += 1
            interaction_map[interaction.id] = interaction

    # Filter matching interactions
    repeated_interactions = [
        interaction for interaction_id, count in interaction_count.items() if count > 1
        for interaction in [interaction_map[interaction_id]]
    ]

    # If no repeated interactions found, return a default interaction
    if not repeated_interactions:
        return [Interaction(id="0", name="No interaction found", mechanism="")]

    return repeated_interactions


# Endpoint to get data for a single GTIN
@app.get("/data_single_gtin", response_model=Drug)
def get_data_single_gtin(
    gtin: str = Query(description="drug GTIN", example="7680612850014"),
    language: Language = Query(default=Language.FR)
) -> Drug:
    # Fetch data for the given GTIN
    response = requests.get(
        f"https://documedis.hcisolutions.ch/2020-01/api/products/{gtin}?IdType=gtin",
        headers={"Accept-Language" : language.value}
    )
    response.raise_for_status()
    data = response.json()

    # Extract drug interactions from response
    interactions = [
        get_interaction(drugInteraction)
        for drugInteraction in data["components"][0]["substances"][0]["drugInteractions"]
    ]

    # Create drug object to be returned
    drug = Drug(
        gtin=gtin,
        #name=data["name"],
        description=data["description"]["description"],
        interactions=interactions
    )

    return drug


# Function to create Interaction object
def get_interaction(drugInteraction) -> Interaction:
    return Interaction(id=drugInteraction["id"], name=drugInteraction["title"], mechanism=drugInteraction["mechanismText"]) 
