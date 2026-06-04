import logging
from typing import Any, Optional
from pydantic import BaseModel
from datetime import datetime, timezone, timedelta

from app.schemas.incoming_message import IncomingMessage
from app.services.customer_service import CustomerService
from app.services.incident_service import IncidentService

logger = logging.getLogger(__name__)

class CustomerContext(BaseModel):
    customer_id: str | None = None
    customer_name: str | None = None
    customer_type: str | None = None
    last_incident_id: str | None = None
    last_pest_type: str | None = None
    last_location: str | None = None
    last_incident_date: str | None = None
    days_since_last_incident: int | None = None
    has_multiple_sites: bool = False
    site_locations: list[str] = []

class CustomerContextBuilder:
    def __init__(
        self,
        customer_service: CustomerService | None = None,
        incident_service: IncidentService | None = None,
    ):
        self.customer_service = customer_service or CustomerService()
        from app.services.firestore_factory import get_firestore_service
        self.incident_service = incident_service or IncidentService(get_firestore_service())

    async def build(self, message: IncomingMessage) -> CustomerContext:
        ctx = CustomerContext()
        if not message.external_user_id or not message.channel:
            return ctx

        try:
            customer = await self.customer_service.get_customer_by_channel_id(
                message.channel, message.external_user_id
            )
            if not customer:
                return ctx

            ctx.customer_id = customer.get("id")
            ctx.customer_name = customer.get("name")
            ctx.customer_type = customer.get("customer_type")

            # Query sites to determine if they have multiple sites
            sites = await self.customer_service.list_sites(customer_id=ctx.customer_id)
            ctx.has_multiple_sites = len(sites) > 1
            
            site_locations = []
            for s in sites:
                addr = s.get("address", "").lower()
                name = s.get("name", "").lower()
                for loc in ["torremolinos", "málaga", "malaga", "benalmádena", "benalmadena", "fuengirola", "marbella"]:
                    if loc in addr or loc in name:
                        site_locations.append(loc)
            ctx.site_locations = list(set(site_locations))

            # Look up recent incidents for this customer
            # Currently IncidentService might not have a direct list_incidents_by_customer.
            # Assuming we can list all or use firestore list_documents.
            from app.services.firestore_factory import get_firestore_service
            firestore = get_firestore_service()
            
            recent_incidents = await firestore.list_documents(
                "incidents",
                filters={"customer_id": ctx.customer_id},
            )
            
            # Sort incidents by created_at descending if not already sorted
            def get_created_at(inc):
                ca = inc.get("created_at")
                if not ca:
                    return datetime.min.replace(tzinfo=timezone.utc)
                if isinstance(ca, datetime):
                    return ca
                try:
                    return datetime.fromisoformat(ca.replace('Z', '+00:00'))
                except Exception:
                    return datetime.min.replace(tzinfo=timezone.utc)

            if recent_incidents:
                recent_incidents.sort(key=get_created_at, reverse=True)
                last_inc = recent_incidents[0]
                
                ctx.last_incident_id = last_inc.get("id")
                ctx.last_pest_type = last_inc.get("pest_type")
                ctx.last_location = last_inc.get("location")
                
                created_at = get_created_at(last_inc)
                if created_at != datetime.min.replace(tzinfo=timezone.utc):
                    ctx.last_incident_date = created_at.isoformat()
                    ctx.days_since_last_incident = (datetime.now(timezone.utc) - created_at).days

            return ctx
        except Exception as e:
            logger.error(f"Error building customer context: {e}")
            return ctx
