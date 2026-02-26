"""
AI RAG service for Natural Language Queries and Clinical Summaries.
Supports Gemini 2.0 Flash and GPT-4o with ChromaDB vector store.
"""
import json
from typing import Any, Optional
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from app.core.config import settings
from app.models.models import (
    InventoryItem, InventoryMovement, Surgery, SterilizationCycle,
    Product, User,
)
from app.schemas.schemas import NLQRequest, NLQResponse, ClinicalSummaryRequest


async def _gather_context(db: AsyncSession, query: str) -> list[dict]:
    """Gather relevant database records as context for the LLM."""
    context = []
    now = datetime.now(timezone.utc)

    # Inventory summary
    inv_result = await db.execute(
        select(InventoryItem, Product)
        .join(Product, InventoryItem.product_id == Product.id)
        .where(InventoryItem.is_active.is_(True))
        .limit(50)
    )
    for item, product in inv_result.all():
        context.append({
            "type": "inventory",
            "product_name": product.name,
            "gtin": product.gtin,
            "batch": item.batch_number,
            "serial": item.serial_number,
            "quantity": str(item.quantity),
            "expiry_date": item.expiry_date.isoformat() if item.expiry_date else None,
        })

    # Recent surgeries
    surg_result = await db.execute(
        select(Surgery).order_by(Surgery.created_at.desc()).limit(20)
    )
    for surgery in surg_result.scalars().all():
        context.append({
            "type": "surgery",
            "surgery_code": surgery.surgery_code,
            "procedure": surgery.procedure_name,
            "patient_id": surgery.patient_id,
            "status": surgery.status.value,
            "scheduled_at": surgery.scheduled_at.isoformat() if surgery.scheduled_at else None,
        })

    # Recent sterilization cycles
    cycle_result = await db.execute(
        select(SterilizationCycle).order_by(SterilizationCycle.created_at.desc()).limit(20)
    )
    for cycle in cycle_result.scalars().all():
        context.append({
            "type": "sterilization_cycle",
            "autoclave_id": cycle.autoclave_id,
            "cycle_number": cycle.cycle_number,
            "status": cycle.status.value,
            "bio_indicator": cycle.biological_indicator_result,
            "created_at": cycle.created_at.isoformat(),
        })

    return context


def _build_system_prompt() -> str:
    return (
        "Eres el asistente clínico de Hospitraze ERP, especializado en trazabilidad hospitalaria. "
        "Tienes acceso a datos en tiempo real sobre inventario farmacéutico, ciclos de esterilización "
        "y registros quirúrgicos. Responde siempre en español de forma concisa y precisa. "
        "Si la información no está disponible en el contexto, indícalo claramente. "
        "Nunca inventes datos. Cumple con NOM-024-SSA3-2012 y NOM-241-SSA1-2025."
    )


async def process_nlq(
    db: AsyncSession,
    request: NLQRequest,
) -> NLQResponse:
    """Process a Natural Language Query against hospital data."""
    context = await _gather_context(db, request.query)
    context_str = json.dumps(context[:request.context_limit * 3], ensure_ascii=False, indent=2)

    prompt = (
        f"Contexto del sistema hospitalario:\n{context_str}\n\n"
        f"Pregunta del usuario: {request.query}\n\n"
        "Responde basándote únicamente en los datos del contexto proporcionado."
    )

    answer, model_used, tokens = await _call_llm(prompt)
    sources = [{"record": c} for c in context[:request.context_limit]]

    return NLQResponse(
        query=request.query,
        answer=answer,
        sources=sources,
        model_used=model_used,
        tokens_used=tokens,
    )


async def generate_clinical_summary(
    db: AsyncSession,
    request: ClinicalSummaryRequest,
) -> str:
    """Generate a clinical summary for a specific patient."""
    sections = []

    if request.include_medications:
        movements_result = await db.execute(
            select(InventoryMovement, InventoryItem, Product)
            .join(InventoryItem, InventoryMovement.item_id == InventoryItem.id)
            .join(Product, InventoryItem.product_id == Product.id)
            .where(InventoryMovement.patient_id == request.patient_id)
            .order_by(InventoryMovement.created_at.desc())
            .limit(30)
        )
        meds = []
        for movement, item, product in movements_result.all():
            meds.append({
                "medication": product.name,
                "quantity": str(movement.quantity_delta),
                "date": movement.created_at.isoformat(),
                "type": movement.movement_type.value,
            })
        sections.append({"section": "Medicamentos", "data": meds})

    if request.include_surgeries:
        surg_result = await db.execute(
            select(Surgery)
            .where(Surgery.patient_id == request.patient_id)
            .order_by(Surgery.scheduled_at.desc())
        )
        surgeries = []
        for s in surg_result.scalars().all():
            surgeries.append({
                "procedure": s.procedure_name,
                "date": s.scheduled_at.isoformat() if s.scheduled_at else None,
                "status": s.status.value,
            })
        sections.append({"section": "Cirugías", "data": surgeries})

    context_str = json.dumps(sections, ensure_ascii=False, indent=2)
    prompt = (
        f"Genera un resumen clínico conciso para el paciente ID: {request.patient_id}\n\n"
        f"Historial de trazabilidad:\n{context_str}\n\n"
        "El resumen debe incluir: medicamentos administrados, procedimientos realizados, "
        "fechas relevantes, y cualquier observación importante. Redacta de forma profesional médica."
    )

    answer, _, _ = await _call_llm(prompt)
    return answer


async def _call_llm(prompt: str) -> tuple[str, str, Optional[int]]:
    """Call the configured LLM provider."""
    provider = settings.LLM_PROVIDER.lower()

    if provider == "gemini" and settings.GOOGLE_API_KEY:
        return await _call_gemini(prompt)
    elif provider == "openai" and settings.OPENAI_API_KEY:
        return await _call_openai(prompt)
    else:
        # Fallback: return a message indicating LLM is not configured
        return (
            "El servicio de IA no está configurado. "
            "Por favor, configure GOOGLE_API_KEY o OPENAI_API_KEY en las variables de entorno.",
            "none",
            0,
        )


async def _call_gemini(prompt: str) -> tuple[str, str, Optional[int]]:
    try:
        import google.generativeai as genai

        genai.configure(api_key=settings.GOOGLE_API_KEY)
        model = genai.GenerativeModel("gemini-2.0-flash-exp")
        system = _build_system_prompt()
        response = model.generate_content(f"{system}\n\n{prompt}")
        text = response.text
        usage = getattr(response, "usage_metadata", None)
        tokens = getattr(usage, "total_token_count", None) if usage else None
        return text, "gemini-2.0-flash-exp", tokens
    except Exception as e:
        return f"Error al conectar con Gemini: {str(e)}", "gemini-error", 0


async def _call_openai(prompt: str) -> tuple[str, str, Optional[int]]:
    try:
        from openai import AsyncOpenAI

        client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        response = await client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": _build_system_prompt()},
                {"role": "user", "content": prompt},
            ],
            max_tokens=1000,
        )
        text = response.choices[0].message.content
        tokens = response.usage.total_tokens if response.usage else None
        return text, "gpt-4o", tokens
    except Exception as e:
        return f"Error al conectar con OpenAI: {str(e)}", "openai-error", 0
