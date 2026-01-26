from typing import Any, Optional, Sequence, Tuple
from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.base import BaseCheckpointSaver, Checkpoint, CheckpointMetadata, CheckpointTuple
from motor.motor_asyncio import AsyncIOMotorDatabase
import pickle

class AsyncMongoDBSaver(BaseCheckpointSaver):
    """A checkpoint saver that stores checkpoints in a MongoDB database asynchronously."""

    def __init__(self, db: AsyncIOMotorDatabase, collection_name: str = "checkpoints"):
        super().__init__()
        self.collection = db[collection_name]
        self.writes_collection = db[f"{collection_name}_writes"]

    async def aget_tuple(self, config: RunnableConfig) -> Optional[CheckpointTuple]:
        """Get a checkpoint tuple from the database."""
        
        configurable = config.get("configurable", {})
        thread_id = configurable.get("thread_id")
        checkpoint_id = configurable.get("checkpoint_id")
        
        if checkpoint_id:
            query = {"thread_id": thread_id, "checkpoint_id": checkpoint_id}
        else:
            query = {"thread_id": thread_id}
        
        sort_order = [("checkpoint_id", -1)]
        doc = await self.collection.find_one(query, sort=sort_order)
        
        if not doc:
            return None
            
        config_values: RunnableConfig = RunnableConfig(
            configurable={
                "thread_id": doc["thread_id"],
                "checkpoint_id": doc["checkpoint_id"],
            }
        )
        
        checkpoint = pickle.loads(doc["checkpoint"])
        metadata = pickle.loads(doc["metadata"]) if doc.get("metadata") else None
        if metadata is not None and isinstance(metadata, dict):
            metadata = CheckpointMetadata(**metadata)
        if metadata is None:
            metadata = CheckpointMetadata()  # Provide default values as needed
        parent_config = doc.get("parent_config")
        if parent_config:
            parent_config = pickle.loads(parent_config)

        return CheckpointTuple(config_values, checkpoint, metadata, parent_config)

    async def aput_writes(
        self,
        config: RunnableConfig,
        writes: Sequence[Tuple[str, Any]],
        task_id: str,
    ) -> None:
        """Store intermediate writes."""
        configurable = config.get("configurable", {})
        thread_id = configurable.get("thread_id")
        checkpoint_id = configurable.get("checkpoint_id")
        
        # We store writes mainly to allow resuming from a specific step if needed.
        # For this usage, valid storage is expected.
        for idx, (channel, value) in enumerate(writes):
            doc = {
                "thread_id": thread_id,
                "checkpoint_id": checkpoint_id,
                "task_id": task_id,
                "idx": idx,
                "channel": channel,
                "value": pickle.dumps(value)
            }
            await self.writes_collection.insert_one(doc)

    async def aput(
        self,
        config: RunnableConfig,
        checkpoint: Checkpoint,
        metadata: CheckpointMetadata,
        new_versions: dict[str, Any],
    ) -> RunnableConfig:
        """Save a checkpoint to the database."""
        configurable = config.get("configurable", {})
        thread_id = configurable.get("thread_id")
        checkpoint_id = checkpoint["id"]
        
        doc = {
            "thread_id": thread_id,
            "checkpoint_id": checkpoint_id,
            "checkpoint": pickle.dumps(checkpoint),
            "metadata": pickle.dumps(metadata),
            "parent_config": pickle.dumps(config)
        }
        
        await self.collection.replace_one(
            {"thread_id": thread_id, "checkpoint_id": checkpoint_id},
            doc,
            upsert=True
        )
        
        return {
            "configurable": {
                "thread_id": thread_id,
                "checkpoint_id": checkpoint_id,
            }
        }
