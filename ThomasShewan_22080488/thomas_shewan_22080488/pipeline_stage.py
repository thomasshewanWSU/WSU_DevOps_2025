from aws_cdk import (
    Stage,
)

from constructs import Construct
from .thomas_shewan_22080488_stack import ThomasShewan22080488Stack

class MyPipelineStage(Stage):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)
        
        # Pass the stage name to the stack so resources get unique names
        ThomasShewan22080488Stack(
            self, 
            "ThomasShewan22080488Stack",
            stage_name=construct_id  # 'alpha', 'beta', 'gamma', or 'prod'
        )