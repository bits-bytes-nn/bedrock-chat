# CDK

The infrastructure of Bedrock Chat. See [Deploy using CDK](../README.md#deploy-using-cdk) for parameters and deployment, which uses `npx cdk deploy --all` because the app has several stacks.

- `npm run test`: run the jest tests
- `npx cdk diff --all`: compare the deployed stacks with the code
- `npx cdk synth`: synthesize the CloudFormation templates
