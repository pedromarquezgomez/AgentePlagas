from app.schemas.client import Client


class ClientService:
    async def get_or_create_client(self, client: Client) -> Client:
        return client

