# File Upload Insights Platform - Workers

This directory contains the worker components for processing uploaded files and generating insights.

## Architecture Overview

The workers are designed to run both as AWS Lambda functions in production and as local processes for development and testing.

## File Structure

### Lambda Function Handlers
*One handler per worker type for AWS Lambda deployment*

- **`video_summary_handler.py`** - Video summary Lambda function
- **`video_category_handler.py`** - Video categorization Lambda function  
- **`image_description_handler.py`** - Image description Lambda function

### Shared Utilities

- **`base_worker.py`** - Common worker functionality and base classes
- **`ai_client.py`** - AI service integration (OpenAI/Claude)
- **`s3_utils.py`** - S3 file download utilities
- **`models.py`** - Pydantic models for worker input/output

### Development & Testing

- **`worker_main.py`** - Local development and testing entry point
- **`sqs_worker.py`** - Base SQS message processing logic

## Usage

### Local Development
Use `worker_main.py` for local testing and development of worker functionality.

### Production Deployment
Each `*_handler.py` file serves as an entry point for its corresponding AWS Lambda function.
