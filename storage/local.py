from contextlib import contextmanager
from langgraph.checkpoint.base import (
    BaseCheckpointSaver,
    CheckpointTuple,
    Checkpoint,
    CheckpointMetadata,
    ChannelVersions,
    get_checkpoint_metadata
)
from langchain_core.runnables import RunnableConfig
from typing import Optional, Iterator, AsyncIterator, Any, Sequence
from datetime import datetime, timezone
import json

from pathlib import Path
from loguru import logger


class LocalCheckpointSaver(BaseCheckpointSaver):
    def __init__(self, db_path: str):
        self.db_path = db_path

        if not self.db_path:
            raise ValueError("db_path must be provided")

        # Check if the database folder exists, if not create it
        db_folder = Path(self.db_path)
        if not db_folder.exists():
            logger.info(
                f"Database folder does not exist. Creating: `{db_folder}`")
            db_folder.mkdir(parents=True, exist_ok=True)
            logger.info(
                f"Database folder created successfully at: `{db_folder}`")

        logger.info(f"Using database path: `{self.db_path}`")

    def dump_json_messages(self, messages):
        json_messages = []
        for msg in messages:
            if isinstance(msg, dict):
                json_messages.append(msg)
            elif hasattr(msg, "model_dump"):
                json_messages.append(msg.model_dump())
            else:
                logger.warning(f"Message of unsupported type: {type(msg)}")
        return json_messages

    def put(
        self,
        config: RunnableConfig,
        checkpoint: Checkpoint,
        metadata: CheckpointMetadata,
        new_versions: ChannelVersions = None,
    ) -> RunnableConfig:

        thread_id = config["configurable"]["thread_id"]

        checkpoint_id = config["configurable"].get("checkpoint_id")
        checkpoint_ns = config["configurable"].get("checkpoint_ns")

        db_file_path = Path(self.db_path) / f"{thread_id}.json"

        checkpoints = []
        # Check if database file exists
        if not db_file_path.exists():
            logger.info(
                f"Database file does not exist. Creating: `{db_file_path}`")
            logger.info(
                f"Database file created successfully at: `{db_file_path}`")

        else:
            logger.info(f"Loading existing database file: `{db_file_path}`")
            with open(db_file_path, "r") as db_file:
                try:
                    checkpoints = json.load(db_file)
                    logger.info(
                        f"Loaded {len(checkpoints)} existing checkpoints from database.")
                except json.JSONDecodeError:
                    logger.warning(
                        f"Database file `{db_file_path}` is empty or corrupted. Starting fresh.")
                    checkpoints = []

        logger.info(
            f"Storing checkpoint for thread_id `{thread_id}` at `{db_file_path}`...")

        next_config = {
            "configurable": {
                "thread_id": thread_id,
                "checkpoint_id": checkpoint["id"],
                "checkpoint_ns": checkpoint_ns
            }
        }

        copy = checkpoint.copy()
        copy["channel_values"] = copy["channel_values"].copy()

        # inline primitive values in checkpoint table
        # others are stored in blobs table
        blob_values = {}
        for k, v in checkpoint["channel_values"].items():
            if v is None or isinstance(v, (str, int, float, bool)):
                pass
            else:
                if k == "tool_message":
                    copy["channel_values"]["tool_message"] = copy["channel_values"]["tool_message"].tool_calls
                # elif k == "messages":
                #     copy["channel_values"]["messages"] = self.dump_json_messages(copy["channel_values"]["messages"])
                else:
                    blob_values[k] = copy["channel_values"].pop(k)

        logger.debug(f"Blob values: {blob_values}")
        logger.info(copy)
        checkpoints.append({
            "thread_id": thread_id,
            "checkpoint_id": checkpoint_id,
            "checkpoint_ns": checkpoint_ns,
            "checkpoint": copy,
            "metadata": metadata
        })

        # Write checkpoint and metadata to the file
        with open(db_file_path, "w") as db_file:
            json.dump(checkpoints, db_file, indent=4, ensure_ascii=False)

        logger.info(
            f"Checkpoint stored successfully for thread_id {thread_id}.")

        return next_config

    async def aput(
        self,
        config: RunnableConfig,
        checkpoint: Checkpoint,
        metadata: CheckpointMetadata,
        new_versions: ChannelVersions = None,
    ) -> RunnableConfig:
        """Asynchronously store a checkpoint with its metadata.

        Args:
            config: Configuration of the checkpoint.
            checkpoint: The checkpoint to store.
            metadata: Metadata of the checkpoint.
            new_versions: Optional channel versions.

        Returns:
            RunnableConfig: Updated configuration.
        """
        import asyncio

        thread_id = config["configurable"]["thread_id"]
        checkpoint_id = config["configurable"].get("checkpoint_id")
        checkpoint_ns = config["configurable"].get("checkpoint_ns")

        db_file_path = Path(self.db_path) / f"{thread_id}.json"

        # Run file I/O operations in a thread pool to avoid blocking
        def _read_existing_data():
            checkpoints = []
            if db_file_path.exists():
                logger.info(
                    f"Loading existing database file: `{db_file_path}`")
                with open(db_file_path, "r") as db_file:
                    try:
                        checkpoints = json.load(db_file)
                        logger.info(
                            f"Loaded {len(checkpoints)} existing checkpoints from database.")
                    except json.JSONDecodeError:
                        logger.warning(
                            f"Database file `{db_file_path}` is empty or corrupted. Starting fresh.")
                        checkpoints = []
            else:
                logger.info(
                    f"Database file does not exist. Creating: `{db_file_path}`")
                logger.info(
                    f"Database file created successfully at: `{db_file_path}`")
            return checkpoints

        checkpoints = await asyncio.get_running_loop().run_in_executor(None, _read_existing_data)

        logger.info(
            f"Storing checkpoint for thread_id `{thread_id}` at `{db_file_path}`...")

        next_config = {
            "configurable": {
                "thread_id": thread_id,
                "checkpoint_id": checkpoint["id"],
                "checkpoint_ns": checkpoint_ns
            }
        }

        copy = checkpoint.copy()
        copy["channel_values"] = copy["channel_values"].copy()

        # inline primitive values in checkpoint table
        # others are stored in blobs table
        blob_values = {}
        for k, v in checkpoint["channel_values"].items():
            if v is None or isinstance(v, (str, int, float, bool)):
                pass
            else:
                if k == "tool_message":
                    copy["channel_values"]["tool_message"] = copy["channel_values"]["tool_message"].tool_calls
                # elif k == "messages":
                #     copy["channel_values"]["messages"] = self.dump_json_messages(copy["channel_values"]["messages"])
                else:
                    blob_values[k] = copy["channel_values"].pop(k)

        logger.debug(f"Blob values: {blob_values}")

        checkpoints.append({
            "thread_id": thread_id,
            "checkpoint_id": checkpoint_id,
            "checkpoint_ns": checkpoint_ns,
            "checkpoint": copy,
            "metadata": metadata
        })

        # Run write operation in a thread pool to avoid blocking
        def _write_data():
            with open(db_file_path, "w") as db_file:
                json.dump(checkpoints, db_file, indent=4, ensure_ascii=False)

        await asyncio.get_running_loop().run_in_executor(None, _write_data)

        logger.info(
            f"Checkpoint stored successfully for thread_id {thread_id}.")

        return next_config

    def put_writes(
        self,
        config: RunnableConfig,
        writes: Sequence[tuple[str, Any]],
        task_id: str,
        task_path: str = "",
    ) -> None:
        """Store intermediate writes linked to a checkpoint.

        Args:
            config: Configuration of the related checkpoint.
            writes: List of writes to store.
            task_id: Identifier for the task creating the writes.
            task_path: Path of the task creating the writes.

        Raises:
            NotImplementedError: Implement this method in your custom checkpoint saver.
        """

        # logger.info(f"Task ID: {task_id}")
        # logger.info(f"Task Path: {task_path}")
        # logger.info(f"Writes received: {writes}")

        pass

    async def aput_writes(
        self,
        config: RunnableConfig,
        writes: Sequence[tuple[str, Any]],
        task_id: str,
        task_path: str = "",
    ) -> None:
        """Asynchronously store intermediate writes linked to a checkpoint.

        Args:
            config: Configuration of the related checkpoint.
            writes: List of writes to store.
            task_id: Identifier for the task creating the writes.
            task_path: Path of the task creating the writes.
        """
        # import asyncio

        # # Run logging operations asynchronously if needed
        # def _log_writes():
        #     logger.info(f"Task ID: {task_id}")
        #     logger.info(f"Task Path: {task_path}")
        #     logger.info(f"Writes received: {writes}")

        # await asyncio.get_running_loop().run_in_executor(None, _log_writes)
        pass

    def get_tuple(self, config: RunnableConfig) -> CheckpointTuple | None:
        thread_id = config["configurable"]["thread_id"]
        db_file_path = Path(self.db_path) / f"{thread_id}.json"

        if not db_file_path.exists():
            logger.warning(f"Database file does not exist: `{db_file_path}`")
            return None

        with open(db_file_path, "r") as db_file:
            try:
                checkpoints = json.load(db_file)
                logger.info(
                    f"Loaded {len(checkpoints)} checkpoints from database.")
            except json.JSONDecodeError:
                logger.warning(
                    f"Database file `{db_file_path}` is empty or corrupted.")
                return None

        if not checkpoints:
            logger.info(
                f"No checkpoints found in database file: `{db_file_path}`")
            return None

        latest_entry = checkpoints[-1]
        checkpoint = latest_entry.get("checkpoint")
        metadata = latest_entry.get("metadata")

        if checkpoint is None or metadata is None:
            logger.warning(
                f"Incomplete checkpoint data in database file: `{db_file_path}`")
            return None

        return CheckpointTuple(
            config=config,
            checkpoint=checkpoint,
            metadata=metadata
        )

    async def aget_tuple(self, config: RunnableConfig) -> CheckpointTuple | None:
        """Asynchronously fetch a checkpoint tuple using the given configuration.

        Args:
            config: Configuration specifying which checkpoint to retrieve.

        Returns:
            Optional[CheckpointTuple]: The requested checkpoint tuple, or None if not found.
        """
        import asyncio

        thread_id = config["configurable"]["thread_id"]
        db_file_path = Path(self.db_path) / f"{thread_id}.json"

        if not db_file_path.exists():
            logger.warning(f"Database file does not exist: `{db_file_path}`")
            return None

        # Run file I/O operations in a thread pool to avoid blocking
        def _read_file():
            with open(db_file_path, "r") as db_file:
                try:
                    checkpoints = json.load(db_file)
                    logger.info(
                        f"Loaded {len(checkpoints)} checkpoints from database.")
                    return checkpoints
                except json.JSONDecodeError:
                    logger.warning(
                        f"Database file `{db_file_path}` is empty or corrupted.")
                    return None

        checkpoints = await asyncio.get_running_loop().run_in_executor(None, _read_file)

        if checkpoints is None:
            return None

        if not checkpoints:
            logger.info(
                f"No checkpoints found in database file: `{db_file_path}`")
            return None

        latest_entry = checkpoints[-1]
        checkpoint = latest_entry.get("checkpoint")
        metadata = latest_entry.get("metadata")

        if checkpoint is None or metadata is None:
            logger.warning(
                f"Incomplete checkpoint data in database file: `{db_file_path}`")
            return None

        return CheckpointTuple(
            config=config,
            checkpoint=checkpoint,
            metadata=metadata
        )

    def list(
        self,
        config: RunnableConfig | None,
        *,
        filter: dict[str, Any] | None = None,
        before: RunnableConfig | None = None,
        limit: int | None = None,
    ) -> Iterator[CheckpointTuple]:

        thread_id = config["configurable"]["thread_id"]
        db_file_path = Path(self.db_path) / f"{thread_id}.json"

        if not db_file_path.exists():
            logger.warning(f"Database file does not exist: `{db_file_path}`")
            return iter([])

        with open(db_file_path, "r") as db_file:
            try:
                checkpoints = json.load(db_file)
                logger.info(
                    f"Loaded {len(checkpoints)} checkpoints from database.")
            except json.JSONDecodeError:
                logger.warning(
                    f"Database file `{db_file_path}` is empty or corrupted.")
                return iter([])

        for entry in checkpoints:
            checkpoint_id = entry.get("checkpoint_id")
            checkpoint_ns = entry.get("checkpoint_ns")
            checkpoint = entry.get("checkpoint")
            metadata = entry.get("metadata")

            if checkpoint is None or metadata is None:
                logger.warning(
                    f"Incomplete checkpoint data in database file: `{db_file_path}`")
                continue

            # Apply filter if provided
            if filter:
                should_include = True
                for key, value in filter.items():
                    if key == "checkpoint_id":
                        if checkpoint_id != value:
                            should_include = False
                            break
                    elif key == "checkpoint_ns":
                        if checkpoint_ns == "" or checkpoint_ns not in value:
                            should_include = False
                            break
                    elif key in metadata:
                        if metadata.get(key) != value:
                            should_include = False
                            break
                    elif key in checkpoint:
                        if checkpoint.get(key) != value:
                            should_include = False
                            break
                    else:
                        # Check in channel_values for custom fields
                        channel_values = checkpoint.get("channel_values", {})
                        if key not in channel_values or channel_values.get(key) != value:
                            should_include = False
                            break

                if not should_include:
                    continue

            yield CheckpointTuple(
                config=config,
                checkpoint=checkpoint,
                metadata=metadata
            )

    async def alist(
        self,
        config: RunnableConfig | None,
        *,
        filter: dict[str, Any] | None = None,
        before: RunnableConfig | None = None,
        limit: int | None = None,
    ) -> AsyncIterator[CheckpointTuple]:
        """Asynchronously list checkpoint tuples using the given configuration.

        Args:
            config: Configuration specifying which checkpoints to list.
            filter: Optional filter criteria.
            before: Optional configuration to list checkpoints before.
            limit: Optional limit on number of checkpoints to return.

        Returns:
            AsyncIterator[CheckpointTuple]: An async iterator of checkpoint tuples.
        """
        import asyncio

        thread_id = config["configurable"]["thread_id"]
        db_file_path = Path(self.db_path) / f"{thread_id}.json"

        if not db_file_path.exists():
            logger.warning(f"Database file does not exist: `{db_file_path}`")
            return

        # Run file I/O operations in a thread pool to avoid blocking
        def _read_file():
            with open(db_file_path, "r") as db_file:
                try:
                    checkpoints = json.load(db_file)
                    logger.info(
                        f"Loaded {len(checkpoints)} checkpoints from database.")
                    return checkpoints
                except json.JSONDecodeError:
                    logger.warning(
                        f"Database file `{db_file_path}` is empty or corrupted.")
                    return []

        checkpoints = await asyncio.get_running_loop().run_in_executor(None, _read_file)

        for entry in checkpoints:
            checkpoint_id = entry.get("checkpoint_id")
            checkpoint_ns = entry.get("checkpoint_ns")
            checkpoint = entry.get("checkpoint")
            metadata = entry.get("metadata")

            if checkpoint is None or metadata is None:
                logger.warning(
                    f"Incomplete checkpoint data in database file: `{db_file_path}`")
                continue

            # Apply filter if provided
            if filter:
                should_include = True
                for key, value in filter.items():
                    if key == "checkpoint_id":
                        if checkpoint_id != value:
                            should_include = False
                            break
                    elif key == "checkpoint_ns":
                        if checkpoint_ns == "" or checkpoint_ns not in value:
                            should_include = False
                            break
                    elif key in metadata:
                        if metadata.get(key) != value:
                            should_include = False
                            break
                    elif key in checkpoint:
                        if checkpoint.get(key) != value:
                            should_include = False
                            break
                    else:
                        # Check in channel_values for custom fields
                        channel_values = checkpoint.get("channel_values", {})
                        if key not in channel_values or channel_values.get(key) != value:
                            should_include = False
                            break

                if not should_include:
                    continue

            yield CheckpointTuple(
                config=config,
                checkpoint=checkpoint,
                metadata=metadata
            )

    def delete_thread(
        self,
        thread_id: str,
    ) -> None:
        db_file_path = Path(self.db_path) / f"{thread_id}.json"

        if db_file_path.exists():
            db_file_path.unlink()
            logger.info(f"Deleted database file: `{db_file_path}`")
        else:
            logger.warning(f"Database file does not exist: `{db_file_path}`")

    async def adelete_thread(
        self,
        thread_id: str,
    ) -> None:
        """Asynchronously delete a thread and its associated checkpoint data.

        Args:
            thread_id: The ID of the thread to delete.
        """
        import asyncio

        db_file_path = Path(self.db_path) / f"{thread_id}.json"

        # Run file operations in a thread pool to avoid blocking
        def _delete_file():
            if db_file_path.exists():
                db_file_path.unlink()
                logger.info(f"Deleted database file: `{db_file_path}`")
                return True
            else:
                logger.warning(
                    f"Database file does not exist: `{db_file_path}`")
                return False

        await asyncio.get_running_loop().run_in_executor(None, _delete_file)

    def delete_all(self) -> None:
        db_folder = Path(self.db_path)
        if not db_folder.exists():
            logger.warning(f"Database folder does not exist: `{db_folder}`")
            return

        for db_file in db_folder.glob("*.json"):
            db_file.unlink()
            logger.info(f"Deleted database file: `{db_file}`")

    async def adelete_all(self) -> None:
        """Asynchronously delete all threads and their associated checkpoint data."""
        import asyncio
        from pathlib import Path

        db_folder = Path(self.db_path)
        if not db_folder.exists():
            logger.warning(f"Database folder does not exist: `{db_folder}`")
            return

        # Run file operations in a thread pool to avoid blocking
        def _delete_files():
            for db_file in db_folder.glob("*.json"):
                db_file.unlink()
                logger.info(f"Deleted database file: `{db_file}`")

        await asyncio.get_running_loop().run_in_executor(None, _delete_files)
