import typing
import datetime

import pydantic
from fastapi import APIRouter

from open_bus_stride_db.model.siri_snapshot import SiriSnapshot, SiriSnapshotEtlStatusEnum

from . import common


router = APIRouter()


class SiriSnapshotPydanticModel(pydantic.BaseModel):
    id: int
    snapshot_id: str
    etl_status: SiriSnapshotEtlStatusEnum
    etl_start_time: datetime.datetime
    etl_end_time: datetime.datetime = None
    error: str = None
    num_successful_parse_vehicle_locations: int = None
    num_failed_parse_vehicle_locations: int = None


@router.get("/list", tags=['siri_snapshots'], response_model=typing.List[SiriSnapshotPydanticModel])
def list_(limit: int = None, offset: int = None,
          snapshot_id_prefix: str = None):
    return common.get_list(
        SiriSnapshot, limit, offset,
        [
            {'type': 'prefix', 'field': SiriSnapshot.snapshot_id, 'value': snapshot_id_prefix},
        ]
    )


@router.get('/get', tags=['siri_snapshots'], response_model=SiriSnapshotPydanticModel)
def get_(id: int):
    return common.get_item(SiriSnapshot, SiriSnapshot.id, id)
