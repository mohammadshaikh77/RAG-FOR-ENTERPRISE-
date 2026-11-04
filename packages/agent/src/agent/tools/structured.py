"""Tool for read-only, parameterized queries over structured drug clinical metadata."""

import uuid
from typing import Any

import structlog
from sqlalchemy import func, select

from agent.tools.base import BaseTool, ToolResult
from apps.api.src.models.drug_metadata import DrugMetadata

logger = structlog.get_logger(__name__)


class QueryStructuredDataTool(BaseTool):
    """Executes read-only, parameterized queries over the structured clinical metadata table."""

    name = "query_structured_data"
    description = (
        "Run read-only, structured queries over drug metadata (drug class, boxed warnings, "
        "administration routes, manufacturers, NDCs). No raw SQL is accepted; choose from "
        "supported query_type: 'list_classes', 'filter_by_class', 'filter_by_boxed_warning', "
        "'get_drug_info', or 'find_drugs'."
    )
    parameters = {
        "type": "object",
        "properties": {
            "query_type": {
                "type": "string",
                "enum": [
                    "list_classes",
                    "filter_by_class",
                    "filter_by_boxed_warning",
                    "get_drug_info",
                    "find_drugs",
                ],
                "description": "The category of structured query to execute",
            },
            "parameters": {
                "type": "object",
                "properties": {
                    "drug_class": {
                        "type": "string",
                        "description": "Drug class (e.g., 'Beta Blocker', 'NSAID', 'ACE Inhibitor')",
                    },
                    "drug_name": {
                        "type": "string",
                        "description": "Brand or generic drug name (e.g., 'Lisinopril', 'Metoprolol')",
                    },
                    "has_boxed_warning": {
                        "type": "boolean",
                        "description": "Filter by presence of a boxed warning (true or false)",
                    },
                    "route": {
                        "type": "string",
                        "description": "Administration route (e.g., 'ORAL')",
                    },
                    "keyword": {
                        "type": "string",
                        "description": "Search keyword for drug name or manufacturer",
                    },
                },
                "description": "Arguments corresponding to the chosen query_type",
            },
        },
        "required": ["query_type"],
    }

    def __init__(self, session_factory: Any) -> None:
        self.session_factory = session_factory

    async def execute(self, org_id: uuid.UUID, **kwargs: Any) -> ToolResult:
        query_type = kwargs.get("query_type")
        params = kwargs.get("parameters", {}) or {}

        if not query_type:
            return ToolResult(
                tool_name=self.name, success=False, data=None, error="Missing query_type"
            )

        async with self.session_factory() as session:
            try:
                stmt: Any
                if query_type == "list_classes":
                    stmt = (
                        select(DrugMetadata.drug_class, func.count(DrugMetadata.id).label("count"))
                        .where(DrugMetadata.org_id == org_id)
                        .group_by(DrugMetadata.drug_class)
                        .order_by(func.count(DrugMetadata.id).desc())
                    )
                    rows = (await session.execute(stmt)).all()
                    data = [{"drug_class": r[0], "drug_count": r[1]} for r in rows]
                    return ToolResult(tool_name=self.name, success=True, data=data)

                elif query_type == "filter_by_class":
                    target_class = params.get("drug_class", "").strip()
                    stmt = select(DrugMetadata).where(
                        DrugMetadata.org_id == org_id,
                        DrugMetadata.drug_class.ilike(f"%{target_class}%"),
                    )
                    drugs = (await session.execute(stmt)).scalars().all()
                    return ToolResult(
                        tool_name=self.name, success=True, data=[self._serialize(d) for d in drugs]
                    )

                elif query_type == "filter_by_boxed_warning":
                    has_warning = bool(params.get("has_boxed_warning", True))
                    stmt = select(DrugMetadata).where(
                        DrugMetadata.org_id == org_id,
                        DrugMetadata.has_boxed_warning == has_warning,
                    )
                    drugs = (await session.execute(stmt)).scalars().all()
                    return ToolResult(
                        tool_name=self.name, success=True, data=[self._serialize(d) for d in drugs]
                    )

                elif query_type == "get_drug_info":
                    drug_name = params.get("drug_name", "").strip()
                    stmt = select(DrugMetadata).where(
                        DrugMetadata.org_id == org_id,
                        (DrugMetadata.drug_name.ilike(f"%{drug_name}%"))
                        | (DrugMetadata.generic_name.ilike(f"%{drug_name}%"))
                        | (DrugMetadata.brand_name.ilike(f"%{drug_name}%")),
                    )
                    drugs = (await session.execute(stmt)).scalars().all()
                    return ToolResult(
                        tool_name=self.name, success=True, data=[self._serialize(d) for d in drugs]
                    )

                elif query_type == "find_drugs":
                    conditions = [DrugMetadata.org_id == org_id]
                    if params.get("keyword"):
                        kw = f"%{params['keyword']}%"
                        conditions.append(
                            (DrugMetadata.drug_name.ilike(kw))
                            | (DrugMetadata.manufacturer_name.ilike(kw))
                            | (DrugMetadata.drug_class.ilike(kw))
                        )
                    if "has_boxed_warning" in params:
                        conditions.append(
                            DrugMetadata.has_boxed_warning == bool(params["has_boxed_warning"])
                        )
                    if params.get("route"):
                        conditions.append(DrugMetadata.route.ilike(f"%{params['route']}%"))

                    stmt = select(DrugMetadata).where(*conditions)
                    drugs = (await session.execute(stmt)).scalars().all()
                    return ToolResult(
                        tool_name=self.name, success=True, data=[self._serialize(d) for d in drugs]
                    )

                else:
                    return ToolResult(
                        tool_name=self.name,
                        success=False,
                        data=None,
                        error=f"Unsupported query_type: '{query_type}'",
                    )

            except Exception as e:
                logger.error("query_structured_data tool error", error=str(e), org_id=str(org_id))
                return ToolResult(tool_name=self.name, success=False, data=None, error=str(e))

    def _serialize(self, drug: DrugMetadata) -> dict[str, Any]:
        return {
            "id": str(drug.id),
            "document_id": str(drug.document_id) if drug.document_id else None,
            "drug_name": drug.drug_name,
            "brand_name": drug.brand_name,
            "generic_name": drug.generic_name,
            "drug_class": drug.drug_class,
            "has_boxed_warning": drug.has_boxed_warning,
            "route": drug.route,
            "product_ndc": drug.product_ndc,
            "manufacturer_name": drug.manufacturer_name,
            "boxed_warning_summary": drug.boxed_warning_summary,
        }
