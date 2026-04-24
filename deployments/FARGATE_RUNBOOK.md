# ECS / Fargate Runbook

This runbook describes the recommended cloud deployment shape for the self-hosted TradeNodeX control center.

## Services

- `tradenodex-api`: FastAPI application and React frontend hosting.
- `tradenodex-worker`: queue consumer, private account listeners, reconciliation, and execution runtime.

The worker is required for automatic copy trading. Running only the web service is not enough.

## Required AWS resources

- RDS PostgreSQL
- ElastiCache Redis
- SQS FIFO queues for normal, risk, and recovery execution paths
- Secrets Manager for database URL, Redis URL, queue URLs, and runtime secrets
- KMS key for secret encryption
- ECR repository
- CloudWatch log groups
- NAT Gateway or equivalent fixed outbound IP

## Networking

- Put ECS tasks in private subnets.
- Route outbound exchange API traffic through NAT.
- Add the NAT EIP to exchange API IP allowlists.
- Expose only the API service through an ALB.
- Do not expose Redis, database, or worker tasks publicly.

## Deployment

```bash
aws ecr get-login-password --region ap-northeast-1 | docker login --username AWS --password-stdin <ACCOUNT_ID>.dkr.ecr.ap-northeast-1.amazonaws.com
docker build -f deployments/Dockerfile -t tradenodex:latest .
docker tag tradenodex:latest <ACCOUNT_ID>.dkr.ecr.ap-northeast-1.amazonaws.com/tradenodex:latest
docker push <ACCOUNT_ID>.dkr.ecr.ap-northeast-1.amazonaws.com/tradenodex:latest
aws ecs register-task-definition --cli-input-json file://deployments/ecs-task-api.json
aws ecs register-task-definition --cli-input-json file://deployments/ecs-task-worker.json
```

## Runtime checks

- `GET /v1/dashboard`
- `GET /v1/health/exchanges`
- CloudWatch logs for worker startup
- SQS visible message count near zero during normal conditions
- Web UI header shows API, realtime stream, and worker state
- `Audit Logs` receives signal, execution, warning, error, and reconcile entries

## Pre-release validation

1. Deploy to test environment.
2. Add one master signal source and one follower.
3. Validate both credentials.
4. Create one `EXACT` copy route.
5. Execute a test open and close flow.
6. Confirm signal, task, attempt, exchange response, and position snapshot are linked.
7. Run 88, 120, and 200 account simulations before production rollout.

## Security requirements

- Trade permission only.
- Withdrawal permission disabled.
- Production credentials stored in Secrets Manager or equivalent secret storage.
- Fixed outbound IP allowlisted on each exchange.
- No `.env`, local databases, screenshots with secrets, or raw API keys in the repository.
