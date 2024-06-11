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

# Define model for BioC annotation level
class BioC_annotation(BaseModel):
    id: str
    infon: str | None = None
    location: str
    text: str

# Define model for BioC passage level
class BioC_passage(BaseModel):
    infon: str | None = None
    offset: str
    text: str
    annotations: list[BioC_annotation]

# Define model for BioC document level
class BioC_document(BaseModel):
    id: str
    passage: list[BioC_passage]

# Define model for BioC collection level
class BioC_collection(BaseModel):
    source: str
    date: str
    key: str
    documents: list[BioC_document]

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
@app.get("/interactions_multiple_gtins")
def get_interactions_multiple_gtins(
    gtins: str = Query(description="drug GTINs, separated by commas", example="7680612850014,7680531140760"),
    language: Language = Query(default=Language.FR)
) -> Dict[str, List]:
    # Split GTINs into list
    gtin_list = gtins.split(',')
    original_documents = []

    # Count interactions and create interaction map
    interaction_count: Dict[str, int] = defaultdict(int)
    interaction_map: Dict[str, Interaction] = {}

    # Fetch data from compendium for each GTIN
    for gtin in gtin_list:
        response = requests.get(
            f"https://documedis.hcisolutions.ch/2020-01/api/products/{gtin}?IdType=gtin",
            headers={"Accept-Language": language.value}
        )
        response.raise_for_status()
        data = response.json()
        original_documents.append(data)

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
        repeated_interactions = [Interaction(id="0", name="No interaction found", mechanism="")]

    return {
        "detected_interactions": repeated_interactions,
        "original_documents": original_documents
    }


# Endpoint to get annotations of the compendium notices in BioC format

@app.get("/BioC_annotations")
def get_BioC_annotations(
    gtins: str = Query(description="drug GTINs, separated by commas", example="7680612850014,7680531140760"),
    language: Language = Query(default=Language.FR)
) -> Dict[str, List]:
    # Split GTINs into list
    gtin_list = gtins.split(',')
    original_documents = []

    # Fetch data from compendium for each GTIN
    for gtin in gtin_list:
        response = requests.get(
            f"https://documedis.hcisolutions.ch/2020-01/api/products/{gtin}?IdType=gtin",
            headers={"Accept-Language": language.value}
        )
        response.raise_for_status()
        data = response.json()
        original_documents.append(data)
    
    annotated_documents = original_documents

    return {
        "annotated_documents": annotated_documents,
        "original_documents": original_documents
    }


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
