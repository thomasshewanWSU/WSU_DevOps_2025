# AWS CDK Canary Monitor Project

This project uses AWS Cloud Development Kit (CDK) with Python to deploy a Lambda function that monitors the availability, latency, and response size of a website (`https://westernsydney.edu.au`). The Lambda runs every 5 minutes triggered by an EventBridge scheduled rule.

---

## Project Overview

- The Lambda function performs an HTTP GET request to the target URL and reports:
  - HTTP status code
  - Latency (response time in seconds)
  - Response size in bytes
- The CDK stack provisions:
  - The Lambda function
  - A scheduled EventBridge rule that triggers the Lambda every 5 minutes

---

## Getting Started

This project is set up like a standard Python CDK project. It includes a virtual environment for managing dependencies.


