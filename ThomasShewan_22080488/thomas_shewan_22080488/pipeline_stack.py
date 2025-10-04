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

        # Source from GitHub
        source = pipelines.CodePipelineSource.git_hub(
            repo_string="thomasshewanWSU/WSU_DevOps_2025",  
            branch="main",
            authentication=SecretValue.secrets_manager("github-token"),
        )

        # Synth step - builds CDK asset
        synth_step = pipelines.ShellStep(
            "CodeBuild",
            input=source,
            commands=[
                "cd ThomasShewan_22080488", 
                "npm install -g aws-cdk",
                "python -m pip install --upgrade pip",
                "python -m pip install aws-cdk.pipelines",
                "python -m pip install -r requirements.txt",
                "cdk synth"
            ],
            primary_output_directory="ThomasShewan_22080488/cdk.out"
        )
        
        # Create the pipeline
        pipeline = pipelines.CodePipeline(
            self, "MonitoringPipeline",
            pipeline_name="WebMonitoringPipeline",
            synth=synth_step
        )
        

        # Test Steps ----------------
        
        # Unit Tests - run before any deployment
        unit_test = pipelines.ShellStep( 
            "UnitTests",
            input=source,
            commands=[
                "cd ThomasShewan_22080488",
                "python -m pip install --upgrade pip",
                "python -m pip install -r requirements-dev.txt",
                "python -m pytest tests/unit/ -v"
            ]
        )
        
        # Functional Tests - test Lambda behavior in deployed environment
        functional_test = pipelines.ShellStep(
            "FunctionalTests",
            input=source,
            commands=[
                "cd ThomasShewan_22080488",
                "python -m pip install --upgrade pip",
                "python -m pip install -r requirements-dev.txt",
                "python -m pytest tests/functional/ -v"
            ]
        )
        
        # Integration Tests - test end-to-end workflows
        integration_test = pipelines.ShellStep(
            "IntegrationTests",
            input=source,
            commands=[
                "cd ThomasShewan_22080488",
                "python -m pip install --upgrade pip",
                "python -m pip install -r requirements-dev.txt",
                "python -m pytest tests/integration/ -v"
            ]
        )
        

        # Single Production Stage with All Tests as Quality Gates  ---------------------
        # Combined into one stage due to free tier limits

        # Tests run sequentially as pre-deployment checks
        # If any test fails, deployment stops
        
        prod = MyPipelineStage(self, 'prod')
        pipeline.add_stage(
            prod, 
            pre=[
                unit_test,           # Step 1: Unit tests must pass
                functional_test,     # Step 2: Functional tests must pass
                integration_test,    # Step 3: Integration tests must pass
                pipelines.ManualApprovalStep("Approve-Deploy-To-Prod")  # Step 4: Manual approval
            ]
        )