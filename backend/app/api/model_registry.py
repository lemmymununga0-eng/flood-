from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.models.prediction import ModelVersion
from app.schemas.model_registry import ModelVersionOut

router = APIRouter(prefix="/models", tags=["model-registry"])


@router.get("", response_model=list[ModelVersionOut])
def list_models(db: Session = Depends(get_db)) -> list[ModelVersion]:
    # Legitimately empty until Phase 9 (Model Packaging) registers a real trained
    # model — never seeded with a placeholder row.
    return db.scalars(select(ModelVersion).order_by(ModelVersion.registered_at.desc())).all()


@router.get("/{model_id}", response_model=ModelVersionOut)
def get_model(model_id: int, db: Session = Depends(get_db)) -> ModelVersion:
    model = db.get(ModelVersion, model_id)
    if model is None:
        raise HTTPException(status_code=404, detail={"error": "not_found", "message": "Model version not found"})
    return model
