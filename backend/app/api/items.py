"""items.py — /items CRUD routes."""

from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db, set_tenant_context
from app.models.item import Item
from app.models.user import AppUser


router = APIRouter()


# ---------------------------------------------------------
# Request body for creating an item
# ---------------------------------------------------------

class ItemCreate(BaseModel):
    name: str
    hsn_code: str | None = None
    gst_rate_percent: Decimal
    unit_price: Decimal
    unit: str = "pcs"


# ---------------------------------------------------------
# GET /items/
# ---------------------------------------------------------

@router.get("/")
async def get_items(
    phone: str = Query(
        ...,
        description="Development: phone number of the authenticated user",
    ),
    db: AsyncSession = Depends(get_db),
):
    """
    Retrieve all items belonging to the user's tenant.
    """

    # Find the user
    result = await db.execute(
        select(AppUser).where(AppUser.phone == phone)
    )

    user = result.scalar_one_or_none()

    if user is None:
        raise HTTPException(
            status_code=404,
            detail="User not found.",
        )

    # Set tenant context BEFORE querying tenant-scoped data
    await set_tenant_context(
        db,
        user.tenant_id,
    )

    # Retrieve items
    result = await db.execute(
        select(Item)
        .order_by(Item.created_at.desc())
    )

    items = result.scalars().all()

    # Return items
    return [
        {
            "id": str(item.id),
            "tenant_id": str(item.tenant_id),
            "name": item.name,
            "hsn_code": item.hsn_code,
            "gst_rate_percent": float(item.gst_rate_percent),
            "unit_price": float(item.unit_price),
            "unit": item.unit,
            "created_at": item.created_at,
        }
        for item in items
    ]


# ---------------------------------------------------------
# POST /items/
# ---------------------------------------------------------

@router.post("/")
async def create_item(
    item_data: ItemCreate,
    phone: str = Query(
        ...,
        description="Development: phone number of the authenticated user",
    ),
    db: AsyncSession = Depends(get_db),
):
    """
    Create a new item for the user's tenant.

    Development authentication flow:
        phone -> AppUser -> tenant_id -> RLS context -> create item
    """

    # 1. Find the user
    result = await db.execute(
        select(AppUser).where(AppUser.phone == phone)
    )

    user = result.scalar_one_or_none()

    if user is None:
        raise HTTPException(
            status_code=404,
            detail="User not found.",
        )

    # 2. Set tenant context BEFORE accessing tenant-scoped data
    await set_tenant_context(
        db,
        user.tenant_id,
    )

    # 3. Create the item
    new_item = Item(
        tenant_id=user.tenant_id,
        name=item_data.name,
        hsn_code=item_data.hsn_code,
        gst_rate_percent=item_data.gst_rate_percent,
        unit_price=item_data.unit_price,
        unit=item_data.unit,
    )

    db.add(new_item)

    # 4. Save to database
    await db.commit()

    # 5. Get generated values such as id and created_at
    await db.refresh(new_item)

    # 6. Return the newly created item
    return {
        "id": str(new_item.id),
        "tenant_id": str(new_item.tenant_id),
        "name": new_item.name,
        "hsn_code": new_item.hsn_code,
        "gst_rate_percent": float(new_item.gst_rate_percent),
        "unit_price": float(new_item.unit_price),
        "unit": new_item.unit,
        "created_at": new_item.created_at,
    }
    
@router.get("/{item_id}")
async def get_item(
    item_id: str,
    phone: str = Query(
        ...,
        description="Development: phone number of the authenticated user",
    ),
    db: AsyncSession = Depends(get_db),
):
    """
    Retrieve a single item belonging to the user's tenant.
    """

    # Find the user
    result = await db.execute(
        select(AppUser).where(AppUser.phone == phone)
    )

    user = result.scalar_one_or_none()

    if user is None:
        raise HTTPException(
            status_code=404,
            detail="User not found.",
        )

    # Set tenant context
    await set_tenant_context(
        db,
        user.tenant_id,
    )

    # Find the item
    try:
        it_uuid = UUID(str(item_id))
    except ValueError:
        raise HTTPException(
            status_code=422,
            detail="Invalid item UUID format.",
        )

    result = await db.execute(
        select(Item).where(Item.id == it_uuid)
    )

    item = result.scalar_one_or_none()

    if item is None:
        raise HTTPException(
            status_code=404,
            detail="Item not found.",
        )

    return {
        "id": str(item.id),
        "tenant_id": str(item.tenant_id),
        "name": item.name,
        "hsn_code": item.hsn_code,
        "gst_rate_percent": float(item.gst_rate_percent),
        "unit_price": float(item.unit_price),
        "unit": item.unit,
        "created_at": item.created_at,
    }
    
@router.put("/{item_id}")
async def update_item(
    item_id: str,
    name: str,
    hsn_code: str | None = None,
    gst_rate_percent: float = 0,
    unit_price: float = 0,
    unit: str = "pcs",
    phone: str = Query(
        ...,
        description="Development: phone number of the authenticated user",
    ),
    db: AsyncSession = Depends(get_db),
):
    """
    Update an existing item belonging to the user's tenant.
    """

    # Find the user
    result = await db.execute(
        select(AppUser).where(AppUser.phone == phone)
    )

    user = result.scalar_one_or_none()

    if user is None:
        raise HTTPException(
            status_code=404,
            detail="User not found.",
        )

    # Set tenant context
    await set_tenant_context(
        db,
        user.tenant_id,
    )

    # Find the item
    result = await db.execute(
        select(Item).where(Item.id == item_id)
    )

    item = result.scalar_one_or_none()

    if item is None:
        raise HTTPException(
            status_code=404,
            detail="Item not found.",
        )

    # Update fields
    item.name = name
    item.hsn_code = hsn_code
    item.gst_rate_percent = gst_rate_percent
    item.unit_price = unit_price
    item.unit = unit

    await db.commit()
    await db.refresh(item)

    return {
        "id": str(item.id),
        "tenant_id": str(item.tenant_id),
        "name": item.name,
        "hsn_code": item.hsn_code,
        "gst_rate_percent": float(item.gst_rate_percent),
        "unit_price": float(item.unit_price),
        "unit": item.unit,
        "created_at": item.created_at,
    }
    
@router.delete("/{item_id}")
async def delete_item(
    item_id: str,
    phone: str = Query(
        ...,
        description="Development: phone number of the authenticated user",
    ),
    db: AsyncSession = Depends(get_db),
):
    """
    Delete an item belonging to the user's tenant.
    """

    # Find the user
    result = await db.execute(
        select(AppUser).where(AppUser.phone == phone)
    )

    user = result.scalar_one_or_none()

    if user is None:
        raise HTTPException(
            status_code=404,
            detail="User not found.",
        )

    # Set tenant context
    await set_tenant_context(
        db,
        user.tenant_id,
    )

    # Find the item
    result = await db.execute(
        select(Item).where(Item.id == item_id)
    )

    item = result.scalar_one_or_none()

    if item is None:
        raise HTTPException(
            status_code=404,
            detail="Item not found.",
        )

    # Delete the item
    await db.delete(item)
    await db.commit()

    return {
        "message": "Item deleted successfully."
    }