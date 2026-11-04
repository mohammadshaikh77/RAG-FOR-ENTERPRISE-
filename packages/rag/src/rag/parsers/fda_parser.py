from typing import Any

from packages.rag.src.rag.parsers.base import ParsedDocument, ParsedSection

FDA_SECTION_MAP = {
    "boxed_warning": "Boxed Warning",
    "indications_and_usage": "Indications and Usage",
    "contraindications": "Contraindications",
    "dosage_and_administration": "Dosage and Administration",
    "warnings_and_cautions": "Warnings and Precautions",
    "warnings": "Warnings",
    "adverse_reactions": "Adverse Reactions",
    "drug_interactions": "Drug Interactions",
    "use_in_specific_populations": "Use in Specific Populations",
    "pregnancy": "Pregnancy Risk",
    "clinical_pharmacology": "Clinical Pharmacology",
    "mechanism_of_action": "Mechanism of Action",
    "pharmacokinetics": "Pharmacokinetics",
    "description": "Drug Description",
    "how_supplied": "How Supplied / Storage and Handling",
    "patient_medication_information": "Patient Counseling Information",
}


class FDALabelParser:
    """Parses openFDA JSON label records into structured clinical sections."""

    def parse(self, record: dict[str, Any]) -> ParsedDocument:
        openfda = record.get("openfda", {})

        brand_names = openfda.get("brand_name", [])
        generic_names = openfda.get("generic_name", [])
        manufacturer = openfda.get("manufacturer_name", ["Unknown Manufacturer"])
        pharm_class = openfda.get("pharm_class_epc", openfda.get("pharm_class_cs", []))
        routes = openfda.get("route", [])

        brand = (
            brand_names[0]
            if brand_names
            else (generic_names[0] if generic_names else "Unknown Drug")
        )
        generic = generic_names[0] if generic_names else brand
        title = f"{brand} ({generic})"

        metadata = {
            "drug_name": brand,
            "generic_name": generic,
            "manufacturer": manufacturer[0] if manufacturer else "Unknown",
            "drug_classes": pharm_class,
            "routes": routes,
            "boxed_warning_present": bool(record.get("boxed_warning")),
            "application_number": openfda.get("application_number", []),
            "ndc": openfda.get("package_ndc", openfda.get("product_ndc", [])),
        }

        sections: list[ParsedSection] = []
        page = 1

        for key, section_title in FDA_SECTION_MAP.items():
            if key in record and record[key]:
                raw_val = record[key]
                if isinstance(raw_val, list):
                    content = "\n\n".join(str(item).strip() for item in raw_val if item)
                else:
                    content = str(raw_val).strip()

                if content:
                    sections.append(
                        ParsedSection(
                            title=section_title,
                            content=content,
                            section_path=f"{title} > {section_title}",
                            page_number=page,
                            metadata={"section_key": key},
                        )
                    )
                    page += 1

        return ParsedDocument(
            title=title,
            file_type="application/json+fda_label",
            sections=sections,
            metadata=metadata,
        )
