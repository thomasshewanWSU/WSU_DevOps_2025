    # Operations Runbook

## Quick Reference

### Alarm Response
**Website Down (Availability = 0)**
1. Check alarm in CloudWatch console
2. Verify website manually in browser
3. Check Lambda logs for errors

**High Latency (> 5000ms)** 
1. Review latency trends in dashboard
2. Test website response time manually
3. Check if issue affects all sites

**Low Throughput (< 1000 bytes/sec)**
1. Check Lambda logs for small responses
2. Verify website returns normal content
3. Monitor for recovery

### Maintenance Tasks

**Adding Websites**
1. Edit `websites` array in `MonitoringLambda.py`
2. Run `cdk deploy`
3. Verify new alarms appear in CloudWatch

**Changing Thresholds**
1. Edit alarm thresholds in `ThomasShewan22080488Stack.py`
2. Run `cdk deploy`
3. Check updated alarm configurations

**Troubleshooting**
- **No data in dashboard**: Wait 15 minutes after deployment
- **Lambda errors**: Check CloudWatch logs
- **Missing alarms**: Verify CDK deployment completed successfully