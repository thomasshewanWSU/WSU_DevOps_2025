from aws_cdk import (
    Stage,
)

from constructs import Construct
from .thomas_shewan_22080488_stack import ThomasShewan22080488Stack

class MyPipelineStage(Stage):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)
        
        ThomasShewan22080488Stack(self, "ThomasShewan22080488Stack")