# Standard
from dataclasses import asdict, dataclass
from typing import Dict, Optional
import uuid

_DEFAULT_BUILD_ID = "exp"


@dataclass
class TaskRunCard:
    """This class is intended to hold the all information regarding the experiment being run"""

    task_name: str  # name of task
    databuilder_name: str  # name of databuilder associated with task
    task_spec: Optional[Dict] = None  # json string for task settings
    databuilder_spec: Optional[Dict] = None  # json string for databuilder settings
    build_id: Optional[str] = None  # id of entity executing the task
    run_id: Optional[str] = None  # unique ID for the experiment
    save_formatted_output: Optional[bool] = None  # will save formatted output

    def __post_init__(self):
        if self.run_id is None:
            self.run_id = str(uuid.uuid4())
        if self.build_id is None:
            self.build_id = _DEFAULT_BUILD_ID  #  default to something generic
        if self.save_formatted_output is None:
            self.save_formatted_output = False

    def to_dict(self):
        return asdict(self)
