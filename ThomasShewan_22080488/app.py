#!/usr/bin/env python3
import os
import aws_cdk as cdk
from thomas_shewan_22080488.pipeline_stack import PipelineStack

# Initialize CDK application
# The App is the root construct that contains all stacks
# Documentation: https://docs.aws.amazon.com/cdk/api/v2/python/aws_cdk/App.html
app = cdk.App()

# Create the CI/CD Pipeline Stack
# This stack defines the CodePipeline that deploys to multiple stages (alpha, prod)
# Documentation: https://docs.aws.amazon.com/cdk/api/v2/python/aws_cdk/Stack.html
PipelineStack(
    app, 
    "WebMonitoringPipelineStack",
    env=cdk.Environment(
        # Account and region are retrieved from environment variables or AWS CLI config
        # Documentation: https://docs.aws.amazon.com/cdk/v2/guide/environments.html
        account=os.getenv('CDK_DEFAULT_ACCOUNT'),
        region='ap-southeast-2'  # Sydney region
    )
)

# Synthesize CloudFormation templates
# This generates JSON template files in the cdk.out directory
# Documentation: https://docs.aws.amazon.com/cdk/v2/guide/apps.html#apps_synth
app.synth()