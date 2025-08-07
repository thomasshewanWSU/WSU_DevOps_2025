#!/usr/bin/env python3
import os

import aws_cdk as cdk

from thomas_shewan_22080488.cloudWatchStack import WebCrawlerStack  # example import
from thomas_shewan_22080488.thomas_shewan_22080488_stack import ThomasShewan22080488Stack

app = cdk.App()

WebCrawlerStack(app, "Week3Stack",
    env=cdk.Environment(
        account=os.getenv('CDK_DEFAULT_ACCOUNT'),
        region='ap-southeast-2'
    )
)

ThomasShewan22080488Stack(app, "ThomasShewan22080488Stack",
    env=cdk.Environment(
        account=os.getenv('CDK_DEFAULT_ACCOUNT'),
        region='ap-southeast-2'
    )
)

app.synth()
