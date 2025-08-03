#!/usr/bin/env python3
import os

import aws_cdk as cdk

from thomas_shewan_22080488.thomas_shewan_22080488_stack import ThomasShewan22080488Stack


app = cdk.App()
ThomasShewan22080488Stack(app, "ThomasShewan22080488Stack",
    # Specify Sydney region (ap-southeast-2)
    env=cdk.Environment(
        account=os.getenv('CDK_DEFAULT_ACCOUNT'), 
        region='ap-southeast-2'
    ),

    # For more information, see https://docs.aws.amazon.com/cdk/latest/guide/environments.html
    )

app.synth()
