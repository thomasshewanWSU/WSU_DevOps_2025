#!/usr/bin/env python3
import os

import aws_cdk as cdk

from thomas_shewan_22080488.pipeline_stack import PipelineStack  

#App definition 
app = cdk.App()
PipelineStack(app, "WebMonitoringPipelineStack",
    env=cdk.Environment(
        account=os.getenv('CDK_DEFAULT_ACCOUNT'), 
        region='ap-southeast-2'
    )
)

app.synth()