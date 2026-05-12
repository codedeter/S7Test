import asyncio
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Any, Optional, Callable
from dataclasses import dataclass


@dataclass
class PipelineData:
    device_id: str
    data: List[Dict[str, Any]]
    timestamp: float
    metadata: Optional[Dict[str, Any]] = None
    processed: bool = False


class AsyncPipelineStage:
    def __init__(self, name: str, executor: ThreadPoolExecutor = None):
        self.name = name
        self._executor = executor
        self._next_stage: Optional['AsyncPipelineStage'] = None

    def set_next(self, stage: 'AsyncPipelineStage') -> 'AsyncPipelineStage':
        self._next_stage = stage
        return self

    async def process(self, data: PipelineData) -> Optional[PipelineData]:
        result = await self._process(data)
        if result is not None and self._next_stage is not None:
            return await self._next_stage.process(result)
        return result

    async def _process(self, data: PipelineData) -> Optional[PipelineData]:
        raise NotImplementedError


class AsyncDataBufferStage(AsyncPipelineStage):
    def __init__(self, max_size: int = 50):
        super().__init__('async_buffer')
        self._buffer = asyncio.Queue(maxsize=max_size)

    async def _process(self, data: PipelineData) -> Optional[PipelineData]:
        if self._buffer.full():
            await self._buffer.get()
        await self._buffer.put({
            'timestamp': data.timestamp,
            'device_id': data.device_id,
            'data': data.data,
            'metadata': data.metadata
        })
        return data

    async def get_latest(self, device_id: Optional[str] = None, count: int = 1) -> List[Dict]:
        items = []
        while not self._buffer.empty():
            items.append(await self._buffer.get())

        if device_id:
            filtered = [item for item in reversed(items) if item['device_id'] == device_id]
            result = filtered[:count]
        else:
            result = list(reversed(items))[:count]

        for item in items:
            await self._buffer.put(item)

        return result


class AsyncDataPipeline:
    def __init__(self, max_workers: int = 4):
        self._stages: List[AsyncPipelineStage] = []
        self._first_stage: Optional[AsyncPipelineStage] = None
        self._executor = ThreadPoolExecutor(max_workers=max_workers)

    def add_stage(self, stage: AsyncPipelineStage) -> 'AsyncDataPipeline':
        stage._executor = self._executor
        self._stages.append(stage)
        if self._first_stage is None:
            self._first_stage = stage
        else:
            last_stage = self._stages[-2]
            last_stage.set_next(stage)
        return self

    async def process(self, device_id: str, data: List[Dict[str, Any]],
                      metadata: Optional[Dict[str, Any]] = None) -> Optional[PipelineData]:
        pipeline_data = PipelineData(
            device_id=device_id,
            data=data,
            timestamp=time.time(),
            metadata=metadata
        )

        if self._first_stage:
            return await self._first_stage.process(pipeline_data)
        return pipeline_data

    async def process_batch(self, batch_data: List[tuple]) -> List[Optional[PipelineData]]:
        tasks = [self.process(device_id, data, metadata)
                 for device_id, data, metadata in batch_data]
        return await asyncio.gather(*tasks)