import * as fs from 'node:fs';
import * as path from 'node:path';
import * as cdk from 'aws-cdk-lib';
import { Construct } from 'constructs';
import * as ec2 from 'aws-cdk-lib/aws-ec2';
import * as events from 'aws-cdk-lib/aws-events';
import * as targets from 'aws-cdk-lib/aws-events-targets';
import * as iam from 'aws-cdk-lib/aws-iam';
import * as lambda from 'aws-cdk-lib/aws-lambda';

export class AwsInstancesStack extends cdk.Stack {
  constructor(scope: Construct, id: string, props?: cdk.StackProps) {
    super(scope, id, props);

    const projectName = this.node.tryGetContext('projectName') ?? 'aws-instances-bot';
    const instanceType = this.node.tryGetContext('instanceType') ?? 't3.micro';
    const rootVolumeSizeGb = Number(this.node.tryGetContext('rootVolumeSizeGb') ?? 40);
    const autoStopEnabled = this.node.tryGetContext('autoStopEnabled') !== false;
    const autoStopSchedule = this.node.tryGetContext('autoStopSchedule') ?? 'rate(15 minutes)';
    const autoStopCpuThreshold = String(this.node.tryGetContext('autoStopCpuThreshold') ?? 5);
    const autoStopIdleMinutes = String(this.node.tryGetContext('autoStopIdleMinutes') ?? 30);
    const sshCidrBlocks = this.node.tryGetContext('sshCidrBlocks') ?? [];

    const vpc = ec2.Vpc.fromLookup(this, 'DefaultVpc', { isDefault: true });
    const subnet = vpc.publicSubnets[0];

    const gameSecurityGroup = new ec2.SecurityGroup(this, 'GameServerSecurityGroup', {
      vpc,
      securityGroupName: `${projectName}-game-server`,
      description: 'Access rules for the game server',
      allowAllOutbound: true,
    });

    for (const cidr of sshCidrBlocks) {
      gameSecurityGroup.addIngressRule(ec2.Peer.ipv4(cidr), ec2.Port.tcp(22), 'SSH administration');
    }
    gameSecurityGroup.addIngressRule(ec2.Peer.anyIpv4(), ec2.Port.tcp(16261), 'Project Zomboid game port');
    gameSecurityGroup.addIngressRule(ec2.Peer.anyIpv4(), ec2.Port.udp(16261), 'Project Zomboid game port');
    gameSecurityGroup.addIngressRule(ec2.Peer.anyIpv4(), ec2.Port.udp(16262), 'Project Zomboid query port');
    cdk.Tags.of(gameSecurityGroup).add('Name', `${projectName}-game-server-sg`);
    cdk.Tags.of(gameSecurityGroup).add('Project', projectName);

    const ec2Role = new iam.Role(this, 'Ec2Role', {
      roleName: `${projectName}-ec2-role`,
      assumedBy: new iam.ServicePrincipal('ec2.amazonaws.com'),
      managedPolicies: [
        iam.ManagedPolicy.fromAwsManagedPolicyName('AmazonSSMManagedInstanceCore'),
      ],
    });

    const automationRole = new iam.Role(this, 'AutomationRole', {
      roleName: `${projectName}-automation-role`,
      assumedBy: new iam.ServicePrincipal('lambda.amazonaws.com'),
      inlinePolicies: {
        AutomationPolicy: new iam.PolicyDocument({
          statements: [
            new iam.PolicyStatement({
              actions: ['ec2:DescribeInstances', 'ec2:StartInstances', 'ec2:StopInstances', 'cloudwatch:GetMetricStatistics'],
              resources: ['*'],
            }),
            new iam.PolicyStatement({
              actions: ['logs:CreateLogGroup', 'logs:CreateLogStream', 'logs:PutLogEvents'],
              resources: ['arn:aws:logs:*:*:*'],
            }),
          ],
        }),
      },
    });

    const userData = fs.readFileSync(path.join(__dirname, '../../../scripts/ec2-user-data.sh'), 'utf8');
    const gameServer = new ec2.Instance(this, 'GameServer', {
      instanceName: `${projectName}-game-server`,
      instanceType: new ec2.InstanceType(instanceType),
      machineImage: ec2.MachineImage.lookup({
        name: 'ubuntu/images/hvm-ssd-gp3/ubuntu-noble-24.04-amd64-server-*',
        owners: ['099720109477'],
      }),
      vpc,
      vpcSubnets: { subnets: [subnet] },
      securityGroup: gameSecurityGroup,
      role: ec2Role,
      userData: ec2.UserData.custom(userData),
      blockDevices: [{
        deviceName: '/dev/sda1',
        volume: ec2.BlockDeviceVolume.ebs(rootVolumeSizeGb, {
          volumeType: ec2.EbsDeviceVolumeType.GP3,
          encrypted: true,
          deleteOnTermination: true,
        }),
      }],
    });
    cdk.Tags.of(gameServer).add('Project', projectName);
    cdk.Tags.of(gameServer).add('Role', 'game-server');
    cdk.Tags.of(gameServer).add('AutoStop', String(autoStopEnabled));

    const autoStopLambda = new lambda.Function(this, 'AutoStopLambda', {
      functionName: `${projectName}-auto-stop`,
      runtime: lambda.Runtime.PYTHON_3_12,
      handler: 'auto_stop.lambda_handler',
      code: lambda.Code.fromAsset(path.join(__dirname, '../../../lambdas')),
      role: automationRole,
      timeout: cdk.Duration.seconds(30),
      environment: {
        PROJECT_NAME: projectName,
        CPU_THRESHOLD: autoStopCpuThreshold,
        IDLE_MINUTES: autoStopIdleMinutes,
      },
    });

    const autoStopRule = new events.Rule(this, 'AutoStopRule', {
      ruleName: `${projectName}-auto-stop`,
      description: 'Checks tagged instances and stops those with low CPU usage.',
      schedule: events.Schedule.expression(autoStopSchedule),
      enabled: autoStopEnabled,
    });
    autoStopRule.addTarget(new targets.LambdaFunction(autoStopLambda, {
      event: events.RuleTargetInput.fromObject({ source: 'aws-instances-bot' }),
    }));

    new cdk.CfnOutput(this, 'InstanceId', { value: gameServer.instanceId });
    new cdk.CfnOutput(this, 'InstancePublicIp', { value: gameServer.instancePublicIp });
    new cdk.CfnOutput(this, 'SecurityGroupId', { value: gameSecurityGroup.securityGroupId });
    new cdk.CfnOutput(this, 'AutoStopLambdaName', { value: autoStopLambda.functionName });
  }
}
