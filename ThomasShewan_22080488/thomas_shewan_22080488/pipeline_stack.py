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
        
        # Unit Tests - runs before any deployment (fast, no AWS resources)
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
        

        # Optimized Pipeline: Test Early, Deploy Strategically ---------------------
        # Strategy: Run cheap tests first (unit), then deploy once for expensive tests
        
        # Add unit tests to the synth step (runs before any deployment)
        # This catches bugs early without wasting time/money on deployments
        pipeline.add_wave(
            "PreDeploymentValidation",
            pre=[unit_test]  # Must pass before ANY deployment happens
        )
        
        # ALPHA Stage - Testing Environment
        # Deploy once, run functional + integration tests
        # This validates the code works in a real AWS environment
        alpha = MyPipelineStage(self, 'alpha')
        pipeline.add_stage(
            alpha,
            post=[
                functional_test,    # Test Lambda functions in deployed environment
                integration_test    # Test complete end-to-end workflows
            ]
        )
        
        # PRODUCTION Stage - Manual Approval Required
        # Only deploy to production after all tests pass in alpha
        prod = MyPipelineStage(self, 'prod')
        pipeline.add_stage(
            prod,
            pre=[
                pipelines.ManualApprovalStep(
                    "ApproveProduction",
                    comment="✅ All tests passed in Alpha environment. Deploy to Production?"
                )
            ]
        )