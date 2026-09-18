#!/usr/bin/env node
import * as cdk from 'aws-cdk-lib';
import { AwsInstancesStack } from '../lib/aws-instances-stack';

const app = new cdk.App();

new AwsInstancesStack(app, 'AwsInstancesStack', {
  env: {
    account: process.env.CDK_DEFAULT_ACCOUNT,
    region: process.env.CDK_DEFAULT_REGION ?? process.env.AWS_REGION ?? 'us-east-1',
  },
});
