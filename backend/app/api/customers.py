"""customers.py — /customers CRUD routes."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID

from app.db.session import get_db, set_tenant_context
from app.models.customer import Customer
from app.models.user import AppUser


router = APIRouter()


@router.get("/")
async def get_customers(
    phone: str = Query(..., description="Development: phone number of the authenticated user"),
    db: AsyncSession = Depends(get_db),
):
    """
    Retrieve customers belonging to the user's tenant.

    Development authentication flow:
        phone -> AppUser -> tenant_id -> RLS context -> customers

    TODO:
        Replace phone lookup with JWT authentication before production.
    """

    # 1. Find the application user
    result = await db.execute(
        select(AppUser).where(AppUser.phone == phone)
    )

    user = result.scalar_one_or_none()

    if user is None:
        raise HTTPException(
            status_code=404,
            detail="User not found.",
        )

    # 2. Set tenant context BEFORE querying tenant-scoped data
    await set_tenant_context(
        db,
        user.tenant_id,
    )

    # 3. Retrieve customers
    result = await db.execute(
        select(Customer)
        .order_by(Customer.created_at.desc())
    )

    customers = result.scalars().all()

    # 4. Return JSON
    return [
        {
            "id": str(customer.id),
            "tenant_id": str(customer.tenant_id),
            "name": customer.name,
            "phone": customer.phone,
            "gstin": customer.gstin,
            "state": customer.state,
            "address": customer.address,
            "created_at": customer.created_at,
        }
        for customer in customers
    ]
    
@router.post("/")
async def create_customer(
    name: str,
    phone: str = Query(..., description="Development: phone number of the authenticated user"),
    customer_phone: str | None = None,
    gstin: str | None = None,
    state: str | None = None,
    address: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    # 1. Find the application user
    result = await db.execute(
        select(AppUser).where(AppUser.phone == phone)
    )

    user = result.scalar_one_or_none()

    if user is None:
        raise HTTPException(
            status_code=404,
            detail="User not found.",
        )

    # 2. Set tenant context
    await set_tenant_context(
        db,
        user.tenant_id,
    )

    # 3. Create customer
    customer = Customer(
        tenant_id=user.tenant_id,
        name=name,
        phone=customer_phone,
        gstin=gstin,
        state=state,
        address=address,
    )

    db.add(customer)

    await db.commit()
    await db.refresh(customer)

    # 4. Return customer
    return {
        "id": str(customer.id),
        "tenant_id": str(customer.tenant_id),
        "name": customer.name,
        "phone": customer.phone,
        "gstin": customer.gstin,
        "state": customer.state,
        "address": customer.address,
        "created_at": customer.created_at,
    }
    
@router.get("/{customer_id}")
async def get_customer(
    customer_id: str,
    phone: str = Query(
        ...,
        description="Development: phone number of the authenticated user",
    ),
    db: AsyncSession = Depends(get_db),
):
    # 1. Find the application user
    result = await db.execute(
        select(AppUser).where(AppUser.phone == phone)
    )

    user = result.scalar_one_or_none()

    if user is None:
        raise HTTPException(
            status_code=404,
            detail="User not found.",
        )

    # 2. Set tenant context
    await set_tenant_context(
        db,
        user.tenant_id,
    )

    # 3. Find the customer
    try:
        cust_uuid = UUID(str(customer_id))
    except ValueError:
        raise HTTPException(
            status_code=422,
            detail="Invalid customer UUID format.",
        )

    result = await db.execute(
        select(Customer).where(Customer.id == cust_uuid)
    )

    customer = result.scalar_one_or_none()

    if customer is None:
        raise HTTPException(
            status_code=404,
            detail="Customer not found.",
        )

    # 4. Return customer
    return {
        "id": str(customer.id),
        "tenant_id": str(customer.tenant_id),
        "name": customer.name,
        "phone": customer.phone,
        "gstin": customer.gstin,
        "state": customer.state,
        "address": customer.address,
        "created_at": customer.created_at,
    }
    
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db, set_tenant_context
from app.models.customer import Customer
from app.models.user import AppUser


@router.put("/{customer_id}")
async def update_customer(
    customer_id: UUID,
    name: str,
    customer_phone: str | None = None,
    gstin: str | None = None,
    state: str | None = None,
    address: str | None = None,
    phone: str = Query(
        ...,
        description="Development: phone number of the authenticated user",
    ),
    db: AsyncSession = Depends(get_db),
):
    """
    Update a customer belonging to the user's tenant.
    """

    # 1. Find the application user
    result = await db.execute(
        select(AppUser).where(AppUser.phone == phone)
    )

    user = result.scalar_one_or_none()

    if user is None:
        raise HTTPException(
            status_code=404,
            detail="User not found.",
        )

    # 2. Set tenant context
    await set_tenant_context(
        db,
        user.tenant_id,
    )

    # 3. Find the customer
    result = await db.execute(
        select(Customer).where(Customer.id == customer_id)
    )

    customer = result.scalar_one_or_none()

    if customer is None:
        raise HTTPException(
            status_code=404,
            detail="Customer not found.",
        )

    # 4. Update customer
    customer.name = name
    customer.phone = customer_phone
    customer.gstin = gstin
    customer.state = state
    customer.address = address

    # 5. Save changes
    await db.commit()
    await db.refresh(customer)

    # 6. Return updated customer
    return {
        "id": str(customer.id),
        "tenant_id": str(customer.tenant_id),
        "name": customer.name,
        "phone": customer.phone,
        "gstin": customer.gstin,
        "state": customer.state,
        "address": customer.address,
        "created_at": customer.created_at,
    }
    
@router.delete("/{customer_id}")
async def delete_customer(
    customer_id: UUID,
    phone: str = Query(
        ...,
        description="Development: phone number of the authenticated user",
    ),
    db: AsyncSession = Depends(get_db),
):
    """
    Delete a customer belonging to the user's tenant.
    """

    # 1. Find the application user
    result = await db.execute(
        select(AppUser).where(AppUser.phone == phone)
    )

    user = result.scalar_one_or_none()

    if user is None:
        raise HTTPException(
            status_code=404,
            detail="User not found.",
        )

    # 2. Set tenant context
    await set_tenant_context(
        db,
        user.tenant_id,
    )

    # 3. Find the customer
    result = await db.execute(
        select(Customer).where(Customer.id == customer_id)
    )

    customer = result.scalar_one_or_none()

    if customer is None:
        raise HTTPException(
            status_code=404,
            detail="Customer not found.",
        )

    # 4. Delete customer
    await db.delete(customer)

    # 5. Save changes
    await db.commit()

    return {
        "message": "Customer deleted successfully."
    }