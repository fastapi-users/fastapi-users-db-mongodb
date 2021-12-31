import uuid
from datetime import datetime, timedelta, timezone
from typing import AsyncGenerator

import pymongo.errors
import pytest
from fastapi_users.authentication.strategy.db.models import BaseAccessToken
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import UUID4

from fastapi_users_db_mongodb.access_token import MongoDBAccessTokenDatabase


class AccessToken(BaseAccessToken):
    pass


@pytest.fixture
def user_id() -> UUID4:
    return uuid.uuid4()


@pytest.fixture(scope="module")
async def mongodb_client():
    client = AsyncIOMotorClient(
        "mongodb://localhost:27017",
        serverSelectionTimeoutMS=10000,
        uuidRepresentation="standard",
    )

    try:
        await client.server_info()
        yield client
        client.close()
    except pymongo.errors.ServerSelectionTimeoutError:
        pytest.skip("MongoDB not available", allow_module_level=True)
        return


@pytest.fixture
@pytest.mark.asyncio
async def mongodb_access_token_db(
    mongodb_client: AsyncIOMotorClient,
) -> AsyncGenerator[MongoDBAccessTokenDatabase, None]:
    db = mongodb_client["test_database_access_token"]
    collection = db["access_tokens"]

    yield MongoDBAccessTokenDatabase(AccessToken, collection)

    await collection.delete_many({})


@pytest.mark.asyncio
@pytest.mark.db
async def test_queries(
    mongodb_access_token_db: MongoDBAccessTokenDatabase[AccessToken],
    user_id: UUID4,
):
    access_token = AccessToken(token="TOKEN", user_id=user_id)

    # Create
    access_token_db = await mongodb_access_token_db.create(access_token)
    assert access_token_db.token == "TOKEN"
    assert access_token_db.user_id == user_id

    # Update
    access_token_db.created_at = datetime.now(timezone.utc)
    await mongodb_access_token_db.update(access_token_db)

    # Get by token
    access_token_by_token = await mongodb_access_token_db.get_by_token(
        access_token_db.token
    )
    assert access_token_by_token is not None

    # Get by token expired
    access_token_by_token = await mongodb_access_token_db.get_by_token(
        access_token_db.token, max_age=datetime.now(timezone.utc) + timedelta(hours=1)
    )
    assert access_token_by_token is None

    # Get by token not expired
    access_token_by_token = await mongodb_access_token_db.get_by_token(
        access_token_db.token, max_age=datetime.now(timezone.utc) - timedelta(hours=1)
    )
    assert access_token_by_token is not None

    # Get by token unknown
    access_token_by_token = await mongodb_access_token_db.get_by_token(
        "NOT_EXISTING_TOKEN"
    )
    assert access_token_by_token is None

    # Exception when inserting existing token
    with pytest.raises(pymongo.errors.DuplicateKeyError):
        await mongodb_access_token_db.create(access_token_db)

    # Delete token
    await mongodb_access_token_db.delete(access_token_db)
    deleted_access_token = await mongodb_access_token_db.get_by_token(
        access_token_db.token
    )
    assert deleted_access_token is None
