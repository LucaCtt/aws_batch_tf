# aws-batch-tf

A batteries-included template for running containerised Python jobs on **AWS Batch EC2** (on-demand or Spot), with infrastructure managed by Terraform and job results delivered over SQS.

## How it works

```
┌─────────────────────────────────────────────────────────────┐
│  Your machine                                               │
│                                                             │
│  launcher.py  ──submit──▶  AWS Batch job queue              │
│       │                         │                           │
│       │                         ▼                           │
│       │                   EC2 instance                      │
│       │                   └─ Docker container               │
│       │                      └─ job.py ──push──▶ SQS queue  │
│       │                                              │      │
│       └──────────────poll────────────────────────────┘      │
└─────────────────────────────────────────────────────────────┘
```

1. **`launcher.py`** submits one or more jobs to an AWS Batch job queue, passing per-job configuration as container environment variables.
2. Each job runs inside a Docker container on an EC2 (or Spot) instance. The container entry point is **`job.py`**, which does its work and pushes a result message to an SQS queue.
3. `launcher.py` polls the SQS queue until it receives results from all submitted jobs (or times out).

All AWS infrastructure — the Batch compute environment, job queue, job definition, IAM roles, and SQS queue — is provisioned by Terraform.

## Repository layout

```
.
├── terraform/              # Infrastructure (Batch, SQS, IAM, networking)
│   ├── main.tf
│   ├── network.tf          # Default VPC fallback logic
│   ├── sqs.tf              # SQS queue + IAM policy for EC2 instances
│   ├── variable.tf
│   ├── outputs.tf
│   └── versions.tf
├── src/aws_batch_tf/
│   ├── launcher.py         # Entry point: submits jobs, polls results
│   ├── launcher_settings.py
│   ├── aws/
│   │   ├── job_submitter.py    # Thin boto3 wrapper for Batch job submission
│   │   └── messages_queue.py   # SQS push/pop wrapper
│   └── job/
│       ├── job.py              # Container entry point — replace with your logic
│       └── job_settings.py
├── Dockerfile
├── .env.default            # Template — copy to .env and fill in
└── .github/workflows/
    └── dockerhub-push.yml  # Builds and pushes the Docker image on push to main
```

## Prerequisites

| Tool | Purpose |
|---|---|
| [Terraform](https://developer.hashicorp.com/terraform/install) ≥ 1.14 | Provision AWS infrastructure |
| [uv](https://docs.astral.sh/uv/getting-started/installation/) | Python dependency management |
| [Docker](https://docs.docker.com/get-docker/) | Build the job container image |
| AWS credentials | With sufficient permissions (see below) |

### Required AWS permissions

Your IAM user/role needs permission to create and manage: Batch compute environments, job queues, job definitions, EC2 instances, SQS queues, IAM roles and policies, and (if using auto-networking) to read VPC/subnet/security group information.

## Setup

### 1. Configure environment

```bash
cp .env.default .env
```

Edit `.env`. At minimum set `TF_VAR_NAME_PREFIX` (must be unique per deployment) and `TF_VAR_JOB_IMAGE_URI`.

### 2. Provision infrastructure

```bash
cd terraform
terraform init
source ../.env   # loads TF_VAR_* variables
terraform apply
```

If `TF_VAR_SUBNET_IDS` and `TF_VAR_SECURITY_GROUP_IDS` are left empty, Terraform will use the **AWS default VPC**, its subnets, and its default security group. See [Networking](#networking) for details.

On success, Terraform outputs the job queue name, job definition name, and SQS queue URL. These are already wired into `.env.default` using `TF_VAR_NAME_PREFIX` so no manual copy-paste is needed.

### 3. Build and push the Docker image

The image is built and pushed automatically by the GitHub Actions workflow on every push to `main` (if `src/` or `Dockerfile` changed). To push manually:

```bash
docker build -t your-dockerhub-user/your-repo:latest .
docker push your-dockerhub-user/your-repo:latest
```

Set `TF_VAR_JOB_IMAGE_URI` in `.env` to match.

### 4. Run the launcher

```bash
source .env
uv run python -m aws_batch_tf.launcher
```

The launcher submits jobs to Batch, then polls the SQS queue until results arrive.

### 5. Teardown

```bash
cd terraform
source ../.env
terraform destroy
```

This removes the Batch compute environment, job queue, job definition, SQS queue, and all IAM roles created by Terraform. It does not touch any VPC resources (those are read-only data sources).

## Configuration reference

All infrastructure and app settings are loaded from environment variables. Copy `.env.default` to `.env` to get started.

### Infrastructure (`TF_VAR_*`)

| Variable | Default | Description |
|---|---|---|
| `TF_VAR_REGION` | `us-east-1` | AWS region |
| `TF_VAR_NAME_PREFIX` | — | **Required.** Prefix for all resource names |
| `TF_VAR_SUBNET_IDS` | _(default VPC)_ | Comma-separated subnet IDs. Leave empty to use default VPC subnets |
| `TF_VAR_SECURITY_GROUP_IDS` | _(default SG)_ | Comma-separated SG IDs. Leave empty to use default VPC security group |
| `TF_VAR_COMP_ENV_USE_SPOT` | `1` | `1` to use Spot instances, `0` for on-demand |
| `TF_VAR_COMP_ENV_MAX_CONCURRENT_JOBS` | `4` | Maximum number of jobs running in parallel. Determines `max_vcpus` |
| `TF_VAR_COMP_ENV_INSTANCE_TYPES` | `["g4dn.xlarge", "g5.xlarge", ...]` | EC2 instance types for the compute environment |
| `TF_VAR_JOB_IMAGE_URI` | `busybox:latest` | Container image for job containers |
| `TF_VAR_JOB_EXECUTION_ROLE_ARN` | _(auto)_ | ECS task execution role ARN. Defaults to the account's `ecsInstanceRole` |
| `TF_VAR_JOB_GPUS` | `0` | GPUs per job. Instance types must support the requested count |
| `TF_VAR_JOB_VCPUS` | `4` | vCPUs per job |
| `TF_VAR_JOB_MEMORY_MIB` | `4096` | Memory per job in MiB |
| `TF_VAR_JOB_SHARED_MEMORY_SIZE_MIB` | `1024` | `/dev/shm` size in MiB (useful for PyTorch multi-worker dataloaders) |
| `TF_VAR_JOB_MAX_SWAP_MIB` | `1024` | Maximum swap space in MiB |
| `TF_VAR_JOB_SWAPPINESS` | `60` | Kernel swappiness (0–100) |
| `TF_VAR_JOB_ATTEMPT_DURATION_SECONDS` | `3600` | Per-attempt timeout. Also controls SQS visibility timeout |
| `TF_VAR_JOB_RETRY_ATTEMPTS` | `1` | Number of retry attempts on failure |

By default, Terraform looks up the **AWS default VPC** in the target region and uses all of its subnets and its default security group. No VPC resources are created or modified.

To use a specific VPC, set `TF_VAR_SUBNET_IDS` and `TF_VAR_SECURITY_GROUP_IDS` in `.env`. Both must be provided together.

Make sure whichever subnets you use have a route to the internet — Batch EC2 instances need outbound HTTPS to reach ECR (image pull), SQS, and CloudWatch.

### Launcher (`src/aws_batch_tf/launcher_settings.py`)

| Variable | Default | Description |
|---|---|---|
| `REGION_NAME` | `us-east-1` | AWS region |
| `JOB_QUEUE` | — | Batch job queue name |
| `JOB_DEFINITION` | — | Batch job definition name |
| `MESSAGES_QUEUE_NAME` | — | SQS queue name |
| `POLL_INTERVAL` | `30` | Seconds between SQS polls |
| `POLL_TIMEOUT` | `3600` | Total seconds before polling gives up |

### Job (`src/aws_batch_tf/job/job_settings.py`)

These are passed as container environment variables per job via `JobSubmitter.submit(config={...})`.

| Variable | Default | Description |
|---|---|---|
| `REGION_NAME` | `us-east-1` | AWS region |
| `MESSAGES_QUEUE_NAME` | — | SQS queue name to push results to |
| `HELLO_MESSAGE` | `"Default hello message from the job!"` | Example payload |

`src/aws_batch_tf/job/job.py` is the container entry point. Replace the body of `job()` with your actual workload. Use `JobSettings` to receive per-job parameters (add fields to `job_settings.py` and pass them in `launcher.py` via `config={"YOUR_PARAM": value}`). Push your result back to SQS using `MessagesQueue.push()`.

### CI/CD

The included GitHub Actions workflow (`.github/workflows/dockerhub-push.yml`) builds and pushes the Docker image to Docker Hub on every push to `main` that touches job-related code. It requires three repository secrets/variables:

| Name | Type | Description |
|---|---|---|
| `DOCKERHUB_USERNAME` | Secret | Docker Hub username |
| `DOCKERHUB_TOKEN` | Secret | Docker Hub access token |
| `DOCKERHUB_REPO` | Variable | Target image repository, e.g. `myuser/myrepo` |

## License

MIT. See [LICENSE](LICENSE)

## Author

Luca Cotti (<luca.cotti@unibs.it>)