import aws_cdk as core
import aws_cdk.assertions as assertions

from thomas_shewan_22080488.thomas_shewan_22080488_stack import ThomasShewan22080488Stack

# example tests. To run these tests, uncomment this file along with the example
# resource in thomas_shewan_22080488/thomas_shewan_22080488_stack.py
def test_sqs_queue_created():
    app = core.App()
    stack = ThomasShewan22080488Stack(app, "thomas-shewan-22080488")
    template = assertions.Template.from_stack(stack)

#     template.has_resource_properties("AWS::SQS::Queue", {
#         "VisibilityTimeout": 300
#     })
