#!/bin/bash
set -euo pipefail

exec > >(tee /var/log/aws-instances-bot-bootstrap.log | logger -t aws-instances-bot-bootstrap -s 2>/dev/console) 2>&1

apt-get update
apt-get install -y ca-certificates curl unzip

mkdir -p /opt/aws-instances-bot
cat > /opt/aws-instances-bot/README <<'EOF'
EC2 bootstrap completed. Project Zomboid installation will be added in the game-server setup step.
EOF

systemctl enable amazon-ssm-agent || true
systemctl start amazon-ssm-agent || true