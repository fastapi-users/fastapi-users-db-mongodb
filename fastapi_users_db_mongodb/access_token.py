from datetime import datetime
from typing import Any, Dict, Generic, Optional, Type

from fastapi_users.authentication.strategy.db import A, AccessTokenDatabase
from motor.motor_asyncio import AsyncIOMotorCollection


class MongoDBAccessTokenDatabase(AccessTokenDatabase, Generic[A]):
    """
    Access token database adapter for MongoDB.

    :param access_token_model: Pydantic model of a DB representation of an access token.
    :param collection: Collection instance from `motor`.
    """

    collection: AsyncIOMotorCollection

    def __init__(self, access_token_model: Type[A], collection: AsyncIOMotorCollection):
        self.access_token_model = access_token_model
        self.collection = collection
        self.initialized = False

    async def get_by_token(
        self, token: str, max_age: Optional[datetime] = None
    ) -> Optional[A]:
        await self._initialize()

        query: Dict[str, Any] = {"token": token}
        if max_age is not None:
            query["created_at"] = {"$gte": max_age}

        access_token = await self.collection.find_one(query)
        return self.access_token_model(**access_token) if access_token else None

    async def create(self, access_token: A) -> A:
        await self._initialize()

        await self.collection.insert_one(access_token.dict())
        return access_token

    async def update(self, access_token: A) -> A:
        await self._initialize()

        await self.collection.replace_one(
            {"token": access_token.token}, access_token.dict()
        )
        return access_token

    async def delete(self, access_token: A) -> None:
        await self._initialize()

        await self.collection.delete_one({"token": access_token.token})

    async def _initialize(self):
        if not self.initialized:
            await self.collection.create_index("token", unique=True)
            self.initialized = True
