from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from core.database import Base, engine
from core.deps import get_db, get_current_user
from core.models import User, Record, RecurringRule, UserRule
from core.schemas import (
    RegisterIn, LoginIn, TokenOut,
    RecordIn, RecordOut,
    RecurringIn, RecurringOut,
    RuleIn, RuleOut,
    RecordPatch
)
from core.security import hash_password, verify_password, create_token

from ai.rules import classify, normalize_contains
from ai.finance import build_summary, explain, Transaction

app = FastAPI(title="Money AI")

# MVP: crea tablas al arrancar
Base.metadata.create_all(bind=engine)

# -------------------------
# Auth
# -------------------------
@app.post("/auth/register", response_model=TokenOut)
def register(body: RegisterIn, db: Session = Depends(get_db)):
    existing = db.query(User).filter(User.email == body.email.lower()).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    try:
        pw_hash = hash_password(body.password)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    user = User(email=body.email.lower(), password_hash=pw_hash)
    db.add(user)
    db.commit()
    db.refresh(user)

    token = create_token(user.id)
    return TokenOut(access_token=token)

@app.post("/auth/login", response_model=TokenOut)
def login(body: LoginIn, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == body.email.lower(), User.is_active == True).first()
    if not user or not verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = create_token(user.id)
    return TokenOut(access_token=token)

# -------------------------
# Rules (Aprendizaje por usuario)
# -------------------------
@app.get("/rules", response_model=List[RuleOut])
def list_rules(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    rows = db.query(UserRule).filter(UserRule.user_id == user.id).order_by(UserRule.id.asc()).all()
    return [RuleOut(id=r.id, contains=r.contains, category=r.category) for r in rows]

@app.post("/rules", response_model=RuleOut)
def create_rule(
    body: RuleIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    contains = normalize_contains(body.contains)
    category = body.category.strip()

    if not contains:
        raise HTTPException(status_code=400, detail="contains vacío")

    existing = db.query(UserRule).filter(
        UserRule.user_id == user.id,
        UserRule.contains == contains
    ).first()

    if existing:
        existing.category = category
        db.commit()
        db.refresh(existing)
        return RuleOut(id=existing.id, contains=existing.contains, category=existing.category)

    rule = UserRule(user_id=user.id, contains=contains, category=category)
    db.add(rule)
    db.commit()
    db.refresh(rule)
    return RuleOut(id=rule.id, contains=rule.contains, category=rule.category)

# -------------------------
# Records
# -------------------------
@app.post("/records", response_model=dict)
def add_records(
    items: List[RecordIn],
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    # carga reglas del usuario
    rules = db.query(UserRule).filter(UserRule.user_id == user.id).all()
    user_rules = [(r.contains, r.category) for r in rules]

    for item in items:
        category, confidence = classify(item.description, item.amount, user_rules=user_rules)
        rec = Record(
            user_id=user.id,
            date=item.date,
            description=item.description,
            amount=item.amount,
            category=category,
            confidence=confidence,
            source=item.source or "manual",
        )
        db.add(rec)

    db.commit()
    return {"ok": True, "added": len(items)}

@app.get("/records/{month}", response_model=List[RecordOut])
def list_records(
    month: str,
    kind: str = "all",
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    q = db.query(Record).filter(
        Record.user_id == user.id,
        Record.date.startswith(month)
    )

    if kind == "income":
        q = q.filter(Record.amount > 0)
    elif kind == "expense":
        q = q.filter(Record.amount < 0)

    rows = q.order_by(Record.date.asc(), Record.id.asc()).all()
    return [
        RecordOut(
            id=r.id,
            date=r.date,
            description=r.description,
            amount=r.amount,
            category=r.category,
            confidence=r.confidence,
            source=r.source,
        )
        for r in rows
    ]

@app.patch("/records/{record_id}", response_model=dict)
def patch_record(
    record_id: int,
    body: RecordPatch,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    r = db.query(Record).filter(Record.id == record_id, Record.user_id == user.id).first()
    if not r:
        raise HTTPException(status_code=404, detail="Record not found")

    if body.category:
        new_cat = body.category.strip()
        r.category = new_cat
        r.confidence = 1.0  # corregido

        # aprender: regla por usuario (MVP)
        contains = normalize_contains(r.description)

        existing = db.query(UserRule).filter(
            UserRule.user_id == user.id,
            UserRule.contains == contains
        ).first()

        if existing:
            existing.category = new_cat
        else:
            db.add(UserRule(user_id=user.id, contains=contains, category=new_cat))

    db.commit()
    return {"ok": True, "record_id": r.id, "category": r.category}

@app.delete("/records/{record_id}", response_model=dict)
def delete_record(
    record_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    r = db.query(Record).filter(
        Record.id == record_id,
        Record.user_id == user.id
    ).first()

    if not r:
        raise HTTPException(status_code=404, detail="Record not found")

    db.delete(r)
    db.commit()
    return {"ok": True, "deleted": record_id}

# -------------------------
# Recurring
# -------------------------
@app.post("/recurring", response_model=RecurringOut)
def create_recurring(
    body: RecurringIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if body.schedule != "monthly":
        raise HTTPException(status_code=400, detail="Fase 1 solo soporta schedule='monthly'")

    rule = RecurringRule(
        user_id=user.id,
        name=body.name.strip(),
        amount=body.amount,
        category=body.category.strip(),
        schedule="monthly",
        day_of_month=int(body.day_of_month),
        active=bool(body.active),
    )
    db.add(rule)
    db.commit()
    db.refresh(rule)

    return RecurringOut(
        id=rule.id,
        name=rule.name,
        amount=rule.amount,
        category=rule.category,
        schedule=rule.schedule,
        day_of_month=rule.day_of_month,
        active=rule.active,
    )

@app.get("/recurring", response_model=List[RecurringOut])
def list_recurring(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    rules = db.query(RecurringRule).filter(
        RecurringRule.user_id == user.id
    ).order_by(RecurringRule.id.asc()).all()

    return [
        RecurringOut(
            id=r.id,
            name=r.name,
            amount=r.amount,
            category=r.category,
            schedule=r.schedule,
            day_of_month=r.day_of_month,
            active=r.active,
        )
        for r in rules
    ]

@app.post("/recurring/generate/{month}", response_model=dict)
def generate_recurring_for_month(
    month: str,  # "YYYY-MM"
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    rules = db.query(RecurringRule).filter(
        RecurringRule.user_id == user.id,
        RecurringRule.active == True,
        RecurringRule.schedule == "monthly"
    ).all()

    created = 0
    for rule in rules:
        dd = max(1, min(28, int(rule.day_of_month)))
        date = f"{month}-{dd:02d}"
        description = f"[REC] {rule.name}"

        exists = db.query(Record).filter(
            Record.user_id == user.id,
            Record.date == date,
            Record.description == description,
            Record.amount == rule.amount,
            Record.source == "recurring",
        ).first()

        if exists:
            continue

        rec = Record(
            user_id=user.id,
            date=date,
            description=description,
            amount=rule.amount,
            category=rule.category,
            confidence=1.0,
            source="recurring",
        )
        db.add(rec)
        created += 1

    db.commit()
    return {"ok": True, "created": created, "month": month}

# -------------------------
# Report
# -------------------------
@app.get("/report/{month}", response_model=dict)
def report(
    month: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    rows = db.query(Record).filter(
        Record.user_id == user.id,
        Record.date.startswith(month)
    ).all()

    txs = [
        Transaction(
            date=r.date,
            description=r.description,
            amount=r.amount,
            category=r.category,
            confidence=r.confidence,
        )
        for r in rows
    ]

    summary = build_summary(txs, month)
    summary["message"] = explain(summary)
    return summary
