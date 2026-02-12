from sqlalchemy.orm import Session, joinedload

from app.config import settings
from app.models import Slot
from app.schemas import SlotCreate, SlotFullView, SlotFullViewItem, SlotResponse


from sqlalchemy.exc import IntegrityError

def create_slot(db: Session, data: SlotCreate) -> Slot:
    # Basic check for MAX_SLOTS (Race condition possible but mitigated by unique constraints)
    count = db.query(Slot).count()
    if count >= settings.MAX_SLOTS:
        raise ValueError("slot_limit_reached")
    
    try:
        slot = Slot(
            code=data.code.upper().strip(), # Normalize code to prevent "a1" vs "A1"
            capacity=data.capacity, 
            current_item_count=0
        )
        db.add(slot)
        db.commit()
        db.refresh(slot)
        return slot
    except IntegrityError:
        db.rollback()
        raise ValueError("slot_code_exists")


def list_slots(db: Session) -> list[Slot]:
    return db.query(Slot).all()


def get_slot_by_id(db: Session, slot_id: str) -> Slot | None:
    return db.query(Slot).filter(Slot.id == slot_id).first()


def delete_slot(db: Session, slot_id: str) -> None:
    slot = get_slot_by_id(db, slot_id)
    if not slot:
        raise ValueError("slot_not_found")
    db.delete(slot)
    db.commit()


def get_full_view(db: Session) -> list[SlotFullView]:
    # [Bug 6] N+1 Query Problem: Used joinedload to fetch items with slots in a single query.
    slots = db.query(Slot).options(joinedload(Slot.items)).all()

    result = []
    for slot in slots:
        # slot.items loaded per slot (N+1)
        items = [
            SlotFullViewItem(
                id=item.id,
                name=item.name,
                price=item.price,
                quantity=item.quantity,
            )
            for item in slot.items
        ]
        result.append(
            SlotFullView(
                id=slot.id,
                code=slot.code,
                capacity=slot.capacity,
                items=items,
            )
        )
    return result
