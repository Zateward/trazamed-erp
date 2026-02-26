"""AI / NLQ endpoints."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_user
from app.db.session import get_db
from app.schemas.schemas import NLQRequest, NLQResponse, ClinicalSummaryRequest
from app.ai.rag_service import process_nlq, generate_clinical_summary

router = APIRouter(prefix="/ai", tags=["ai"])


@router.post("/query", response_model=NLQResponse)
async def natural_language_query(
    body: NLQRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Natural Language Query interface.
    Example: "¿Cuál es nuestro stock actual de Propofol que vence en marzo?"
    """
    return await process_nlq(db, body)


@router.post("/clinical-summary")
async def clinical_summary(
    body: ClinicalSummaryRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Generate a concise clinical summary for a patient based on traceability logs."""
    summary = await generate_clinical_summary(db, body)
    return {"patient_id": body.patient_id, "summary": summary}
