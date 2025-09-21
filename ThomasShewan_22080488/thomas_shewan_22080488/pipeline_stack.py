from aws_cdk import (
    Stack,
    Stage,
    aws_cdk as cdk,
    pipelines
)
from constructs import Construct
from .thomas_shewan_22080488_stack import ThomasShewan22080488Stack

class MonitoringStage(Stage):
    """Stage that contains the monitoring stack"""
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)
        
        ThomasShewan22080488Stack(self, "ThomasShewan22080488Stack")

class PipelineStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)
        
        source = pipelines.CodePipelineSource.git_hub(
            repo_string="Thomas_Shewan_WSU/WSU_DevOps_2025",  
            branch="main",
            authentication=cdk.SecretValue.secrets_manager("github-token"),
        )
        
        synth_step = pipelines.ShellStep(
            "Synth",
            input=source,
            install_commands=[
                "cd ThomasShewan_22080488",
                "pip install -r requirements.txt"
            ],
            commands=[
                "cd ThomasShewan_22080488", 
                "npx cdk synth"
            ],
            primary_output_directory="ThomasShewan_22080488/cdk.out"
        )
        
        pipeline = pipelines.CodePipeline(
            self, "MonitoringPipeline",
            pipeline_name="WebMonitoringPipeline",
            synth=synth_step,
            cross_account_keys=False
        )
        
        dev_stage = MonitoringStage(
            self, "Dev",
            env=cdk.Environment(
                account=self.account,
                region="ap-southeast-2"
            )
        )
        
        pipeline.add_stage(dev_stage)