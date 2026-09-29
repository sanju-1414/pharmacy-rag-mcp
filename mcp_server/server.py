import json
import requests
from bs4 import BeautifulSoup
from urllib.parse import quote

from mcp.server.mcpserver import MCPServer


# ============================================================
# MCP SERVER
# ============================================================

mcp = MCPServer("Pharmacy MCP Server")


# ============================================================
# RxNorm: Normalize medicine name
# ============================================================

def normalize_medicine(medicine: str):

    url = "https://rxnav.nlm.nih.gov/REST/rxcui.json"

    params = {
        "name": medicine
    }

    try:

        response = requests.get(
            url,
            params=params,
            timeout=10
        )

        if response.status_code != 200:
            return medicine, None

        data = response.json()

        rxnorm_ids = (
            data
            .get("idGroup", {})
            .get("rxnormId", [])
        )

        if not rxnorm_ids:
            return medicine, None

        rxcui = rxnorm_ids[0]

        name_url = (
            f"https://rxnav.nlm.nih.gov/REST/"
            f"rxcui/{rxcui}/properties.json"
        )

        name_response = requests.get(
            name_url,
            timeout=10
        )

        if name_response.status_code == 200:

            name_data = name_response.json()

            properties = name_data.get(
                "properties",
                {}
            )

            normalized_name = properties.get(
                "name",
                medicine
            )

            return normalized_name, rxcui

        return medicine, rxcui

    except Exception:

        return medicine, None


# ============================================================
# openFDA: Retrieve regulatory drug-label information
# ============================================================

def get_openfda_information(medicine: str):

    url = "https://api.fda.gov/drug/label.json"

    params = {
        "search": (
            f"openfda.generic_name:"
            f"{medicine}"
        ),
        "limit": 1
    }

    # Actual openFDA query URL for the retrieved medicine
    source_url = (
        "https://api.fda.gov/drug/label.json"
        "?search=openfda.generic_name:"
        + quote(medicine)
        + "&limit=1"
    )

    try:

        response = requests.get(
            url,
            params=params,
            timeout=10
        )

        if response.status_code != 200:

            return {
                "status": "not_found",
                "source": "openFDA",
                "url": source_url,
                "sections": {}
            }

        data = response.json()

        results = data.get(
            "results",
            []
        )

        if not results:

            return {
                "status": "not_found",
                "source": "openFDA",
                "url": source_url,
                "sections": {}
            }

        result = results[0]

        sections = {}

        # ----------------------------------------------------
        # INDICATIONS
        # ----------------------------------------------------

        if "indications_and_usage" in result:

            sections["indications"] = (
                result["indications_and_usage"]
            )

        # ----------------------------------------------------
        # WARNINGS
        # ----------------------------------------------------

        if "warnings" in result:

            sections["warnings"] = (
                result["warnings"]
            )

        # ----------------------------------------------------
        # CONTRAINDICATIONS
        # ----------------------------------------------------

        if "contraindications" in result:

            sections["contraindications"] = (
                result["contraindications"]
            )

        # ----------------------------------------------------
        # ADVERSE REACTIONS
        # ----------------------------------------------------

        if "adverse_reactions" in result:

            sections["adverse_reactions"] = (
                result["adverse_reactions"]
            )

        # ----------------------------------------------------
        # PRECAUTIONS
        # ----------------------------------------------------

        if "precautions" in result:

            sections["precautions"] = (
                result["precautions"]
            )

        # ----------------------------------------------------
        # DRUG INTERACTIONS
        # ----------------------------------------------------

        if "drug_interactions" in result:

            sections["drug_interactions"] = (
                result["drug_interactions"]
            )

        return {

            "status": "success",

            "source": "openFDA",

            "role": (
                "Regulatory drug-label evidence"
            ),

            # IMPORTANT:
            # This URL will later be passed to XAI
            "url": source_url,

            "sections": sections
        }

    except Exception as e:

        return {

            "status": "error",

            "source": "openFDA",

            "url": source_url,

            "error": str(e),

            "sections": {}
        }


# ============================================================
# MedlinePlus: Retrieve clinical drug information
# ============================================================

def get_medlineplus_information(
    medicine: str,
    rxcui: str
):

    if not rxcui:

        return {

            "status": "not_found",

            "source": "MedlinePlus",

            "sections": {}
        }

    try:

        # ====================================================
        # STEP 1: MedlinePlus Connect
        # ====================================================

        url = "https://connect.medlineplus.gov/service"

        params = {

            "mainSearchCriteria.v.cs":
                "2.16.840.1.113883.6.88",

            "mainSearchCriteria.v.c":
                rxcui,

            "knowledgeResponseType":
                "application/json",

            "informationRecipient.languageCode.c":
                "en"
        }

        response = requests.get(
            url,
            params=params,
            timeout=15
        )

        if response.status_code != 200:

            return {

                "status": "not_found",

                "source": "MedlinePlus",

                "sections": {}
            }

        data = response.json()

        entries = (
            data
            .get("feed", {})
            .get("entry", [])
        )

        if not entries:

            return {

                "status": "not_found",

                "source": "MedlinePlus",

                "sections": {}
            }

        # ====================================================
        # STEP 2: Select exact medicine page
        # ====================================================

        selected_entry = None

        medicine_lower = medicine.lower()

        for entry in entries:

            title = (
                entry
                .get("title", {})
                .get("_value", "")
            )

            if title.lower() == medicine_lower:

                selected_entry = entry

                break

        if selected_entry is None:

            selected_entry = entries[0]

        # ====================================================
        # STEP 3: Get MedlinePlus webpage URL
        # ====================================================

        links = selected_entry.get(
            "link",
            []
        )

        page_url = None

        for link in links:

            if link.get("rel") == "alternate":

                page_url = link.get("href")

                break

        if not page_url:

            return {

                "status": "not_found",

                "source": "MedlinePlus",

                "sections": {}
            }

        # ====================================================
        # STEP 4: Download webpage
        # ====================================================

        page_response = requests.get(
            page_url,
            timeout=15
        )

        if page_response.status_code != 200:

            return {

                "status": "not_found",

                "source": "MedlinePlus",

                "url": page_url,

                "sections": {}
            }

        # ====================================================
        # STEP 5: Parse webpage
        # ====================================================

        soup = BeautifulSoup(
            page_response.text,
            "html.parser"
        )

        for element in soup(
            ["script", "style", "noscript"]
        ):

            element.decompose()

        # ====================================================
        # STEP 6: Extract sections
        # ====================================================

        sections = {}

        current_section = None

        def identify_section(heading):

            heading = heading.lower().strip()

            if (
                "side effects" in heading
                or "what side effects" in heading
            ):
                return "side_effects"

            if (
                "special precautions" in heading
                or "precautions" in heading
            ):
                return "precautions"

            if (
                "why is this medication prescribed" in heading
                or "medication prescribed" in heading
            ):
                return "indications"

            if (
                "in case of emergency" in heading
                or "overdose" in heading
            ):
                return "overdose"

            if "dietary instructions" in heading:

                return "dietary_instructions"

            if (
                "how should this medicine be used"
                in heading
            ):
                return "administration"

            if (
                "what should i know about storage"
                in heading
            ):
                return "storage"

            return None

        for element in soup.find_all(
            [
                "h1",
                "h2",
                "h3",
                "h4",
                "h5",
                "p",
                "li"
            ]
        ):

            text = element.get_text(
                " ",
                strip=True
            )

            if not text:

                continue

            if element.name in [
                "h1",
                "h2",
                "h3",
                "h4",
                "h5"
            ]:

                detected_section = identify_section(
                    text
                )

                if detected_section:

                    current_section = (
                        detected_section
                    )

                    sections.setdefault(
                        current_section,
                        []
                    )

                else:

                    current_section = None

                continue

            if current_section:

                sections[
                    current_section
                ].append(text)

        # ====================================================
        # STEP 7: Remove duplicates
        # ====================================================

        for section_name in list(
            sections.keys()
        ):

            unique_items = []

            seen = set()

            for item in sections[
                section_name
            ]:

                normalized_item = (
                    item.lower().strip()
                )

                if normalized_item not in seen:

                    seen.add(
                        normalized_item
                    )

                    unique_items.append(
                        item
                    )

            sections[
                section_name
            ] = unique_items

        # ====================================================
        # STEP 8: Remove empty sections
        # ====================================================

        sections = {

            key: value

            for key, value in sections.items()

            if value
        }

        # ====================================================
        # STEP 9: Check useful information
        # ====================================================

        if not sections:

            return {

                "status": "not_found",

                "source": "MedlinePlus",

                "url": page_url,

                "sections": {}
            }

        # ====================================================
        # STEP 10: Return structured information
        # ====================================================

        return {

            "status": "success",

            "source": "MedlinePlus",

            "role": (
                "Independent clinical drug information "
                "for evidence corroboration"
            ),

            "url": page_url,

            "sections": sections
        }

    except Exception as e:

        return {

            "status": "error",

            "source": "MedlinePlus",

            "error": str(e),

            "sections": {}
        }


# ============================================================
# MCP TOOL
# ============================================================

@mcp.tool()
def get_drug_information(
    medicine: str
) -> str:

    normalized_name, rxcui = normalize_medicine(
        medicine
    )

    openfda_data = get_openfda_information(
        normalized_name
    )

    medlineplus_data = (
        get_medlineplus_information(
            normalized_name,
            rxcui
        )
    )

    evidence = {

        "medicine_identity": {

            "source": "RxNorm",

            "role": (
                "Medicine identity and normalization"
            ),

            "input_medicine": medicine,

            "normalized_medicine": normalized_name,

            "rxcui": rxcui
        },

        "openfda": {

            "source": "openFDA",

            "role": (
                "Regulatory drug-label evidence"
            ),

            "status": openfda_data.get(
                "status"
            ),

            # IMPORTANT:
            # Pass openFDA URL forward
            "url": openfda_data.get(
                "url"
            ),

            "sections": openfda_data.get(
                "sections",
                {}
            )
        },

        "medlineplus": {

            "source": "MedlinePlus",

            "role": (
                "Independent clinical drug information "
                "for evidence corroboration"
            ),

            "status": medlineplus_data.get(
                "status"
            ),

            "url": medlineplus_data.get(
                "url"
            ),

            "sections": medlineplus_data.get(
                "sections",
                {}
            )
        }
    }

    return json.dumps(
        evidence,
        indent=2
    )


# ============================================================
# START MCP SERVER
# ============================================================

if __name__ == "__main__":

    mcp.run()