from uuid import uuid4
from app.schemas.customer import Customer, CustomerCreate
from app.schemas.site import Site, SiteCreate
from app.schemas.contract import Contract, ContractCreate
from app.services.firestore_factory import get_firestore_service


class CustomerNotFoundError(LookupError):
    pass


class SiteNotFoundError(LookupError):
    pass


class ContractNotFoundError(LookupError):
    pass


class CustomerService:
    customers_collection = "customers"
    sites_collection = "sites"
    contracts_collection = "contracts"

    def __init__(self, firestore_service=None) -> None:
        self.firestore_service = firestore_service or get_firestore_service()

    # --- CUSTOMERS ---
    async def create_customer(self, customer_create: CustomerCreate) -> Customer:
        customer = Customer(
            id=str(uuid4()),
            **customer_create.model_dump(),
        )
        stored = await self.firestore_service.create_document(
            self.customers_collection,
            customer.model_dump(exclude={"created_at", "updated_at"}),
            document_id=customer.id,
        )
        return Customer.model_validate(stored)

    async def list_customers(self, limit: int | None = None) -> list[dict]:
        return await self.firestore_service.list_documents(
            self.customers_collection,
            limit=limit,
        )

    async def get_customer(self, customer_id: str) -> dict:
        customer = await self.firestore_service.get_document(
            self.customers_collection,
            customer_id,
        )
        if customer is None:
            raise CustomerNotFoundError(f"Customer not found: {customer_id}")
        return customer

    async def update_customer(self, customer_id: str, updates: dict) -> dict:
        current = await self.get_customer(customer_id)
        await self.firestore_service.update_document(
            self.customers_collection,
            customer_id,
            updates,
        )
        return await self.get_customer(customer_id)

    # --- SITES ---
    async def create_site(self, site_create: SiteCreate) -> Site:
        # Validamos que el cliente exista
        await self.get_customer(site_create.customer_id)
        
        site = Site(
            id=str(uuid4()),
            **site_create.model_dump(),
        )
        stored = await self.firestore_service.create_document(
            self.sites_collection,
            site.model_dump(exclude={"created_at", "updated_at"}),
            document_id=site.id,
        )
        return Site.model_validate(stored)

    async def list_sites(self, customer_id: str | None = None, limit: int | None = None) -> list[dict]:
        filters = {}
        if customer_id:
            filters["customer_id"] = customer_id
            
        return await self.firestore_service.list_documents(
            self.sites_collection,
            filters=filters or None,
            limit=limit,
        )

    async def get_site(self, site_id: str) -> dict:
        site = await self.firestore_service.get_document(
            self.sites_collection,
            site_id,
        )
        if site is None:
            raise SiteNotFoundError(f"Site not found: {site_id}")
        return site

    async def update_site(self, site_id: str, updates: dict) -> dict:
        await self.get_site(site_id)
        await self.firestore_service.update_document(
            self.sites_collection,
            site_id,
            updates,
        )
        return await self.get_site(site_id)

    # --- CONTRACTS ---
    async def create_contract(self, contract_create: ContractCreate) -> Contract:
        # Validamos que el cliente exista
        await self.get_customer(contract_create.customer_id)
        
        contract = Contract(
            id=str(uuid4()),
            **contract_create.model_dump(),
        )
        stored = await self.firestore_service.create_document(
            self.contracts_collection,
            contract.model_dump(exclude={"created_at", "updated_at"}),
            document_id=contract.id,
        )
        return Contract.model_validate(stored)

    async def list_contracts(self, customer_id: str | None = None, limit: int | None = None) -> list[dict]:
        filters = {}
        if customer_id:
            filters["customer_id"] = customer_id
            
        return await self.firestore_service.list_documents(
            self.contracts_collection,
            filters=filters or None,
            limit=limit,
        )

    async def get_contract(self, contract_id: str) -> dict:
        contract = await self.firestore_service.get_document(
            self.contracts_collection,
            contract_id,
        )
        if contract is None:
            raise ContractNotFoundError(f"Contract not found: {contract_id}")
        return contract

    async def update_contract(self, contract_id: str, updates: dict) -> dict:
        await self.get_contract(contract_id)
        await self.firestore_service.update_document(
            self.contracts_collection,
            contract_id,
            updates,
        )
        return await self.get_contract(contract_id)
