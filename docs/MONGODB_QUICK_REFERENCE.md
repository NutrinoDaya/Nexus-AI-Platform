# MongoDB Quick Reference for NexusAIPlatform Backend

## Common Patterns

### 1. Database Connection
```python
from motor.motor_asyncio import AsyncIOMotorDatabase
from backend.core.mongodb import get_database

# In route handlers
async def my_endpoint(db: AsyncIOMotorDatabase = Depends(get_db)):
    # db is ready to use
    users = await db.users.find().to_list(length=100)
```

### 2. CRUD Operations

#### Create (INSERT)
```python
from uuid import uuid4
from datetime import datetime

# Single document
document = {
    "_id": str(uuid4()),
    "name": "Example",
    "status": "active",
    "created_at": datetime.utcnow(),
}
result = await db.collection_name.insert_one(document)
inserted_id = result.inserted_id

# Multiple documents
documents = [{"_id": str(uuid4()), ...}, ...]
result = await db.collection_name.insert_many(documents)
```

#### Read (SELECT)
```python
# Find one
doc = await db.users.find_one({"_id": user_id})

# Find many with filter
users = await db.users.find({"role": "admin"}).to_list(length=100)

# Find with projection (select specific fields)
users = await db.users.find({}, {"name": 1, "email": 1}).to_list(length=100)

# Count
total = await db.users.count_documents({"is_active": True})
```

#### Update (UPDATE)
```python
# Update one
await db.users.update_one(
    {"_id": user_id},
    {"$set": {"status": "active", "updated_at": datetime.utcnow()}}
)

# Update many
await db.users.update_many(
    {"role": "user"},
    {"$set": {"tier": "free"}}
)

# Upsert (update or insert)
await db.settings.update_one(
    {"key": "theme"},
    {"$set": {"value": "dark"}},
    upsert=True
)
```

#### Delete (DELETE)
```python
# Delete one
await db.users.delete_one({"_id": user_id})

# Delete many
result = await db.inference_jobs.delete_many({
    "created_at": {"$lt": cutoff_date}
})
deleted_count = result.deleted_count
```

### 3. Pagination
```python
async def list_items(page: int = 1, page_size: int = 20):
    skip = (page - 1) * page_size
    
    # Get total count
    total = await db.items.count_documents(filter_query)
    
    # Get items for current page
    cursor = db.items.find(filter_query).skip(skip).limit(page_size)
    items = await cursor.to_list(length=page_size)
    
    total_pages = (total + page_size - 1) // page_size
    
    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages,
    }
```

### 4. Filtering & Searching

#### Simple Filters
```python
# Equality
{"status": "active"}

# Multiple conditions (AND)
{"status": "active", "role": "admin"}

# IN operator
{"status": {"$in": ["active", "pending"]}}

# Comparison operators
{"age": {"$gte": 18, "$lt": 65}}
{"price": {"$gt": 100}}
```

#### Complex Filters
```python
# OR conditions
{
    "$or": [
        {"name": {"$regex": search, "$options": "i"}},
        {"email": {"$regex": search, "$options": "i"}}
    ]
}

# AND + OR combination
{
    "status": "active",
    "$or": [
        {"role": "admin"},
        {"role": "moderator"}
    ]
}

# Nested fields
{"config.enabled": True}
{"analytics_config.detection_threshold": {"$gte": 0.5}}
```

#### Case-Insensitive Search
```python
# Regex search (case-insensitive)
{
    "name": {"$regex": search_term, "$options": "i"}
}

# Multiple fields
{
    "$or": [
        {"name": {"$regex": search, "$options": "i"}},
        {"description": {"$regex": search, "$options": "i"}}
    ]
}
```

### 5. Sorting
```python
# Sort by one field
cursor = db.users.find().sort("created_at", -1)  # -1 = descending, 1 = ascending

# Sort by multiple fields
cursor = db.models.find().sort([
    ("status", 1),
    ("created_at", -1)
])

# With pagination
cursor = db.items.find(filter_query)\
    .sort("created_at", -1)\
    .skip(skip)\
    .limit(page_size)
items = await cursor.to_list(length=page_size)
```

### 6. Aggregation
```python
# Get distinct values
categories = await db.settings.distinct("category")

# Group and count
pipeline = [
    {"$group": {
        "_id": "$status",
        "count": {"$sum": 1}
    }}
]
result = await db.models.aggregate(pipeline).to_list(length=100)

# Complex aggregation with match and group
pipeline = [
    {"$match": {"status": "active"}},
    {"$group": {
        "_id": "$user_id",
        "total_models": {"$sum": 1},
        "latest_created": {"$max": "$created_at"}
    }},
    {"$sort": {"total_models": -1}},
    {"$limit": 10}
]
top_users = await db.models.aggregate(pipeline).to_list(length=10)
```

### 7. Array Operations
```python
# Add to array
await db.models.update_one(
    {"_id": model_id},
    {"$push": {"tags": "production"}}
)

# Remove from array
await db.models.update_one(
    {"_id": model_id},
    {"$pull": {"tags": "draft"}}
)

# Add to array only if not exists
await db.models.update_one(
    {"_id": model_id},
    {"$addToSet": {"tags": "production"}}
)
```

### 8. Transactions (for multi-document operations)
```python
async with await client.start_session() as session:
    async with session.start_transaction():
        # Multiple operations in transaction
        await db.users.update_one(
            {"_id": from_user_id},
            {"$inc": {"balance": -amount}},
            session=session
        )
        await db.users.update_one(
            {"_id": to_user_id},
            {"$inc": {"balance": amount}},
            session=session
        )
```

## MongoDB Operators Reference

### Comparison Operators
- `$eq` - Equal to
- `$ne` - Not equal to
- `$gt` - Greater than
- `$gte` - Greater than or equal to
- `$lt` - Less than
- `$lte` - Less than or equal to
- `$in` - Matches any value in array
- `$nin` - Matches no value in array

### Logical Operators
- `$and` - Joins query clauses with AND
- `$or` - Joins query clauses with OR
- `$not` - Inverts query expression
- `$nor` - Joins query clauses with NOR

### Update Operators
- `$set` - Set field value
- `$unset` - Remove field
- `$inc` - Increment field value
- `$mul` - Multiply field value
- `$rename` - Rename field
- `$push` - Add to array
- `$pull` - Remove from array
- `$addToSet` - Add to array if not exists

### Array Query Operators
- `$all` - Match all array values
- `$elemMatch` - Match array element with conditions
- `$size` - Match array size

## Error Handling

```python
from pymongo.errors import DuplicateKeyError, PyMongoError

try:
    await db.users.insert_one(user_doc)
except DuplicateKeyError:
    raise HTTPException(
        status_code=400,
        detail="User with this email already exists"
    )
except PyMongoError as e:
    logger.error(f"Database error: {e}")
    raise HTTPException(
        status_code=500,
        detail="Internal server error"
    )
```

## Indexes

### Creating Indexes
```python
# backend/core/mongodb.py - init_mongodb()

# Simple index
await db.users.create_index("email", unique=True)

# Compound index
await db.models.create_index([("user_id", 1), ("status", 1)])

# Text index for search
await db.models.create_index([("name", "text"), ("description", "text")])

# TTL index (auto-delete after time)
await db.sessions.create_index(
    "created_at",
    expireAfterSeconds=3600  # 1 hour
)
```

### Using Text Search
```python
# Search with text index
results = await db.models.find(
    {"$text": {"$search": "yolo detection"}},
    {"score": {"$meta": "textScore"}}
).sort([("score", {"$meta": "textScore"})]).to_list(length=10)
```

## Best Practices

### 1. Always Use UUID Strings for _id
```python
from uuid import uuid4

document = {
    "_id": str(uuid4()),  # Always convert to string
    ...
}
```

### 2. Add Timestamps
```python
from datetime import datetime

document = {
    "_id": str(uuid4()),
    "created_at": datetime.utcnow(),
    "updated_at": datetime.utcnow(),
    ...
}

# On update
await db.collection.update_one(
    {"_id": doc_id},
    {"$set": {"updated_at": datetime.utcnow(), ...}}
)
```

### 3. Use Projection to Limit Fields
```python
# Only get needed fields
user = await db.users.find_one(
    {"_id": user_id},
    {"name": 1, "email": 1, "role": 1}  # Only return these fields
)
```

### 4. Limit Query Results
```python
# Always use .to_list(length=max_items) instead of .to_list()
items = await cursor.to_list(length=100)  # Prevents memory issues
```

### 5. Handle None Results
```python
doc = await db.users.find_one({"_id": user_id})
if not doc:
    raise HTTPException(status_code=404, detail="User not found")
```

### 6. Use Enums for Status Fields
```python
from backend.models.mongodb_models import ModelStatus

# When creating
document = {
    "status": ModelStatus.DRAFT.value,  # "DRAFT"
}

# When querying
models = await db.models.find({"status": ModelStatus.ACTIVE.value}).to_list(length=100)
```

## Debugging Tips

### 1. Log Queries
```python
from backend.core.logging_config import get_logger
logger = get_logger(__name__)

filter_query = {"user_id": user_id, "status": "active"}
logger.debug(f"Query: {filter_query}")
items = await db.items.find(filter_query).to_list(length=100)
logger.debug(f"Results: {len(items)} items")
```

### 2. Check Query Execution Plan
```python
# Use explain() to see query performance
explain = await db.users.find({"email": "test@example.com"}).explain()
print(explain)
```

### 3. Monitor Slow Queries
```bash
# In MongoDB shell
db.setProfilingLevel(1, { slowms: 100 })  # Log queries slower than 100ms
db.system.profile.find().pretty()
```

## Common Gotchas

### 1. Cursor Must Be Awaited
```python
# [TODO] WRONG
items = db.items.find()  # This is a cursor, not items!

# [DONE] CORRECT
items = await db.items.find().to_list(length=100)
```

### 2. Dict Access vs. Object Attributes
```python
# MongoDB documents are dicts
user = await db.users.find_one({"_id": user_id})

# [TODO] WRONG
print(user.name)  # AttributeError

# [DONE] CORRECT
print(user["name"])
print(user.get("name", "Unknown"))
```

### 3. UUID vs. String
```python
from uuid import uuid4

# CORRECT - MongoDB _id as string
doc = {"_id": str(uuid4())}

# WRONG - UUID objects not JSON serializable
doc = {"_id": uuid4()}
```

### 4. Update Operators Required
```python
# WRONG - Missing $set
await db.users.update_one({"_id": id}, {"name": "New Name"})

# CORRECT - Use $set
await db.users.update_one({"_id": id}, {"$set": {"name": "New Name"}})
```

---

## Quick Command Reference

```python
# Find one
doc = await db.collection.find_one({"field": "value"})

# Find many
docs = await db.collection.find({"field": "value"}).to_list(length=100)

# Count
count = await db.collection.count_documents({"field": "value"})

# Insert one
result = await db.collection.insert_one(document)

# Insert many
result = await db.collection.insert_many(documents)

# Update one
await db.collection.update_one({"_id": id}, {"$set": {"field": "value"}})

# Update many
await db.collection.update_many(filter_query, {"$set": {"field": "value"}})

# Delete one
await db.collection.delete_one({"_id": id})

# Delete many
result = await db.collection.delete_many(filter_query)

# Distinct values
values = await db.collection.distinct("field")

# Sort and limit
docs = await db.collection.find().sort("created_at", -1).limit(10).to_list(length=10)
```

---

**For more details, see:**
- Motor Documentation: https://motor.readthedocs.io/
- MongoDB Query Operators: https://www.mongodb.com/docs/manual/reference/operator/query/
- PyMongo API: https://pymongo.readthedocs.io/

