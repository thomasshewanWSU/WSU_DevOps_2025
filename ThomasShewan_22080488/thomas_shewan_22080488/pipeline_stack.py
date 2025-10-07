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
        
        # Unit Tests - basic validation before any deployment
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
        

        # Multi-Stage Pipeline with Progressive Testing ---------------------
        # Each stage runs different tests and provides increasing confidence
        
        # ALPHA Stage - Unit Tests
        # Tests basic functionality before any AWS deployment
        alpha = MyPipelineStage(self, 'alpha')
        pipeline.add_stage(
            alpha,
            pre=[unit_test]  # Only unit tests (fast, no AWS resources needed)
        )
        
        # BETA Stage - Functional Tests
        # Tests Lambda functions in a deployed environment
        beta = MyPipelineStage(self, 'beta')
        pipeline.add_stage(
            beta,
            pre=[functional_test]  # Functional tests run against beta deployment
        )
        
        # GAMMA Stage - Integration Tests
        # Tests complete end-to-end workflows
        gamma = MyPipelineStage(self, 'gamma')
        pipeline.add_stage(
            gamma,
            pre=[integration_test]  # Integration tests run against gamma deployment
        )
        
        # PRODUCTION Stage - Manual Approval Required
        # Final production deployment after all automated tests pass
        prod = MyPipelineStage(self, 'prod')
        pipeline.add_stage(
            prod,
            pre=[
                pipelines.ManualApprovalStep(
                    "ApproveProduction",
                    comment="All tests passed. Approve deployment to production?"
                )
            ]
        )