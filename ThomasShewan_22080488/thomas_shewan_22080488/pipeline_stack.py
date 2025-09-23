from aws_cdk import (
    Stack,
    Stage,
    SecretValue,
    pipelines
)
from constructs import Construct
from .pipeline_stage import MyPipelineStage

class PipelineStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)
        
        source = pipelines.CodePipelineSource.git_hub(
            repo_string="thomasshewanWSU/WSU_DevOps_2025",  
            branch="main",
            authentication=SecretValue.secrets_manager("github-token"),
        )
        
        synth_step = pipelines.ShellStep(
            "CodeBuild",
            input=source,
            commands=[
                "cd ThomasShewan_22080488", 
                "npm install -g aws-cdk",
                "pip install aws-cdk.pipelines",
                "pip install -r requirements.txt",
                "cdk synth"
            ],
            primary_output_directory="ThomasShewan_22080488/cdk.out"
        )
        
        pipeline = pipelines.CodePipeline(
            self, "MonitoringPipeline",
            pipeline_name="WebMonitoringPipeline",
            synth=synth_step
        )
        
        unit_test = pipelines.ShellStep( 
            "UnitTests",
            input=source,
            commands=["cd ThomasShewan_22080488",
                      "pip install -r requirements-dev.txt",
                      "pytest"]
        )


        alpha = MyPipelineStage(self, 'alpha')
        pipeline.add_stage(alpha, pre=[unit_test, pipelines.ManualApprovalStep("Approve-Deploy-To-Alpha")])

    
