from aws_cdk import (
    Stack,
    Stage,
    SecretValue,
    pipelines,
    aws_iam as iam
)
from constructs import Construct
from .pipeline_stage import MyPipelineStage


class PipelineStack(Stack):
    """
    Defines the CI/CD pipeline infrastructure.
    
    Pipeline Flow:
    1. Source Stage: Pull code from GitHub
    2. Build Stage: Run CDK synth via CodeBuild
    3. Pre-deployment: Run unit tests
    4. Alpha Stage: Deploy to test environment
    5. Post-alpha: Run functional and integration tests
    6. Production Stage: Deploy to production (with manual approval)
    """
    
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # SOURCE STAGE: GitHub Repository Integration
        # CodePipeline monitors the repository for changes and triggers builds
        # Documentation: https://docs.aws.amazon.com/cdk/api/v2/python/aws_cdk.pipelines/CodePipelineSource.html#aws_cdk.pipelines.CodePipelineSource.git_hub
        source = pipelines.CodePipelineSource.git_hub(
            repo_string="thomasshewanWSU/WSU_DevOps_2025",
            branch="main",
            # GitHub token stored in AWS Secrets Manager for secure authentication
            # Secrets Manager documentation: https://docs.aws.amazon.com/secretsmanager/latest/userguide/intro.html
            authentication=SecretValue.secrets_manager("github-token"),
        )

        # BUILD STAGE: CDK Synthesis via CodeBuild
        # Synthesizes CDK code into CloudFormation templates
        # This step runs in a CodeBuild environment with Python and Node.js installed
        # Documentation: https://docs.aws.amazon.com/cdk/api/v2/python/aws_cdk.pipelines/ShellStep.html
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
        
        # PIPELINE DEFINITION: Create CodePipeline
        # This construct creates the actual AWS CodePipeline resource
        # Documentation: https://docs.aws.amazon.com/cdk/api/v2/python/aws_cdk.pipelines/CodePipeline.html
        pipeline = pipelines.CodePipeline(
            self, "MonitoringPipeline",
            pipeline_name="WebMonitoringPipeline",
            synth=synth_step
        )
        

        # TEST STAGES: Automated Testing Steps
        # Tests run in CodeBuild containers with AWS credentials for live testing
        # ShellStep documentation: https://docs.aws.amazon.com/cdk/api/v2/python/aws_cdk.pipelines/ShellStep.html
        
        # UNIT TESTS: Fast, isolated tests with mocked AWS services
        # These tests verify individual functions without requiring deployed resources
        # Run before deployment to catch bugs early
        # pytest documentation: https://docs.pytest.org/
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
        
        # FUNCTIONAL TESTS: Test Lambda functions in deployed AWS environment
        # These tests invoke actual Lambda functions and verify their behavior
        # Requires resources to be deployed (runs after alpha deployment)
        functional_test = pipelines.ShellStep(
            "FunctionalTests",
            input=source,
            commands=[
                "cd ThomasShewan_22080488",
                "python -m pip install --upgrade pip",
                "python -m pip install -r requirements-dev.txt",
                "python -m pytest tests/functional/ -v"
            ],
            # Grant permissions to read CloudFormation stacks and invoke Lambda functions
            role_policy_statements=[
                iam.PolicyStatement(
                    actions=[
                        "cloudformation:DescribeStacks",
                        "cloudformation:ListStacks"
                    ],
                    resources=["*"]
                ),
                iam.PolicyStatement(
                    actions=[
                        "lambda:InvokeFunction",
                        "lambda:GetFunction",
                        "lambda:ListEventSourceMappings"
                    ],
                    resources=["*"]
                ),
                iam.PolicyStatement(
                    actions=[
                        "cloudwatch:ListMetrics",
                        "cloudwatch:GetMetricData"
                    ],
                    resources=["*"]
                )
            ]
        )
        
        # INTEGRATION TESTS: End-to-end workflow validation
        # Tests complete user journeys through API Gateway, Lambda, DynamoDB, CloudWatch
        # Validates that all services work together correctly
        integration_test = pipelines.ShellStep(
            "IntegrationTests",
            input=source,
            commands=[
                "cd ThomasShewan_22080488",
                "python -m pip install --upgrade pip",
                "python -m pip install -r requirements-dev.txt",
                "python -m pytest tests/integration/ -v"
            ],
            # Grant permissions to interact with deployed resources
            role_policy_statements=[
                iam.PolicyStatement(
                    actions=[
                        "cloudformation:DescribeStacks",
                        "cloudformation:ListStacks"
                    ],
                    resources=["*"]
                ),
                iam.PolicyStatement(
                    actions=[
                        "dynamodb:GetItem",
                        "dynamodb:PutItem",
                        "dynamodb:DeleteItem",
                        "dynamodb:Scan"
                    ],
                    resources=["*"]
                ),
                iam.PolicyStatement(
                    actions=[
                        "cloudwatch:DescribeAlarms",
                        "cloudwatch:ListMetrics"
                    ],
                    resources=["*"]
                )
            ]
        )
        

        # DEPLOYMENT PIPELINE: Multi-Stage Deployment Strategy
        # Optimized pipeline that runs fast tests first, then deploys to test environment
        # Pipeline Waves documentation: https://docs.aws.amazon.com/cdk/api/v2/python/aws_cdk.pipelines/CodePipeline.html#aws_cdk.pipelines.CodePipeline.add_wave
        # Pipeline Stages documentation: https://docs.aws.amazon.com/cdk/api/v2/python/aws_cdk.pipelines/CodePipeline.html#aws_cdk.pipelines.CodePipeline.add_stage
        
        # PRE-DEPLOYMENT VALIDATION: Run unit tests before any deployment
        # This wave executes before deploying to any environment
        # Wave documentation: https://docs.aws.amazon.com/cdk/api/v2/python/aws_cdk.pipelines/CodePipeline.html#aws_cdk.pipelines.CodePipeline.add_wave
        pipeline.add_wave(
            "PreDeploymentValidation",
            pre=[unit_test]
        )
        
        # ALPHA STAGE: Test Environment Deployment
        # Deploys the full stack to a test environment for validation
        # Post-deployment tests verify the system works correctly in AWS
        # Stage documentation: https://docs.aws.amazon.com/cdk/api/v2/python/aws_cdk/Stage.html
        alpha = MyPipelineStage(self, 'alpha')
        pipeline.add_stage(
            alpha,
            post=[
                # Run tests against deployed resources in alpha environment
                functional_test,    
                integration_test    
            ]
        )
        
        # PRODUCTION STAGE: Production Environment Deployment
        # Requires manual approval before deploying to production
        # Only proceeds if all tests pass in alpha environment
        # Manual Approval documentation: https://docs.aws.amazon.com/cdk/api/v2/python/aws_cdk.pipelines/ManualApprovalStep.html
        prod = MyPipelineStage(self, 'prod')
        pipeline.add_stage(
            prod,
            pre=[
                pipelines.ManualApprovalStep(
                    "ApproveProduction",
                    comment="All tests passed in Alpha environment. Approve deployment to Production?"
                )
            ]
        )
        