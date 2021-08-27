MONGODB_CONTAINER_NAME := fastapi-users-db-mongodb-test-mongo

isort:
	isort ./fastapi_users_db_mongodb ./tests

format: isort
	black .

test:
	docker stop $(MONGODB_CONTAINER_NAME) || true
	docker run -d --rm --name $(MONGODB_CONTAINER_NAME) -p 27017:27017 mongo:4.2
	pytest --cov=fastapi_users_db_mongodb/ --cov-report=term-missing --cov-fail-under=100
	docker stop $(MONGODB_CONTAINER_NAME)

bumpversion-major:
	bumpversion major

bumpversion-minor:
	bumpversion minor

bumpversion-patch:
	bumpversion patch
