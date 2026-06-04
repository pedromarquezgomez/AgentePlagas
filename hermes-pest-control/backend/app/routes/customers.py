from fastapi import APIRouter, Depends, HTTPException, Query, status
from app.dependencies.admin_auth import require_admin_auth
from app.schemas.customer import CustomerCreate, CustomerUpdate
from app.schemas.site import SiteCreate, SiteUpdate
from app.schemas.contract import ContractCreate, ContractUpdate
from app.services.customer_service import (
    CustomerService,
    CustomerNotFoundError,
    SiteNotFoundError,
    ContractNotFoundError,
)

router = APIRouter(
    prefix="/customers",
    tags=["customers"],
    dependencies=[Depends(require_admin_auth)],
)

customer_service = CustomerService()


@router.get("")
async def list_customers(
    limit: int | None = Query(default=50, ge=1, le=200),
) -> list[dict]:
    return await customer_service.list_customers(limit=limit)


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_customer(customer_create: CustomerCreate) -> dict:
    customer = await customer_service.create_customer(customer_create)
    return customer.model_dump()


@router.get("/{customer_id}")
async def get_customer(customer_id: str) -> dict:
    try:
        return await customer_service.get_customer(customer_id)
    except CustomerNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Customer not found.",
        ) from exc


@router.patch("/{customer_id}")
async def update_customer(
    customer_id: str,
    customer_update: CustomerUpdate,
) -> dict:
    updates = customer_update.model_dump(exclude_unset=True)
    try:
        return await customer_service.update_customer(customer_id, updates)
    except CustomerNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Customer not found.",
        ) from exc


# --- SITES ---

@router.get("/{customer_id}/sites")
async def list_customer_sites(
    customer_id: str,
    limit: int | None = Query(default=50, ge=1, le=200),
) -> list[dict]:
    return await customer_service.list_sites(customer_id=customer_id, limit=limit)


@router.post("/{customer_id}/sites", status_code=status.HTTP_201_CREATED)
async def create_customer_site(
    customer_id: str,
    site_create: SiteCreate,
) -> dict:
    if site_create.customer_id != customer_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Customer ID mismatch in body.",
        )
    try:
        site = await customer_service.create_site(site_create)
        return site.model_dump()
    except CustomerNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Customer not found.",
        ) from exc


# --- CONTRACTS ---

@router.get("/{customer_id}/contracts")
async def list_customer_contracts(
    customer_id: str,
    limit: int | None = Query(default=50, ge=1, le=200),
) -> list[dict]:
    return await customer_service.list_contracts(customer_id=customer_id, limit=limit)


@router.post("/{customer_id}/contracts", status_code=status.HTTP_201_CREATED)
async def create_customer_contract(
    customer_id: str,
    contract_create: ContractCreate,
) -> dict:
    if contract_create.customer_id != customer_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Customer ID mismatch in body.",
        )
    try:
        contract = await customer_service.create_contract(contract_create)
        return contract.model_dump()
    except CustomerNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Customer not found.",
        ) from exc
