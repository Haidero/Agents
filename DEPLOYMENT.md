# Cloud Deployment Guide

This guide explains how to deploy the Resume Screening System (with 3 Docker containers) to a cloud provider for free.

## 1. Prerequisites
- A Cloud Account (AWS, Google Cloud, Oracle Cloud, or Azure).
- Docker and Docker Compose installed on the remote server.
- Git installed on the remote server.

## 2. Get a Free Cloud Server (VPS)
Most providers offer a "Free Tier" that is sufficient for this app.

- **Oracle Cloud (Recommended)**: 'Always Free' Ampere instances (up to 4 OCPUs, 24GB RAM).
- **AWS**: EC2 `t2.micro` or `t3.micro` (Free for 12 months).
- **Google Cloud**: Compute Engine `e2-micro` (Always Free).

### Steps to create a server:
1. Log in to your cloud console.
2. Create a new Virtual Machine / Instance.
3. Choose **Ubuntu 20.04 LTS** or **22.04 LTS** as the Operating System.
4. **Important**: In the Security/Firewall settings, allow traffic on:
    - **Port 80** (HTTP) - For the Web App access.
    - **Port 22** (SSH) - For you to manage the server.

## 3. Server Setup
SSH into your new server:
```bash
ssh -i key.pem ubuntu@<YOUR_SERVER_IP>
```

Install Docker & Docker Compose:
```bash
# Update packages
sudo apt-get update
sudo apt-get install -y git

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Add your user to the docker group (avoids using sudo)
sudo usermod -aG docker $USER
# Log out and log back in for this to take effect
exit
ssh -i key.pem ubuntu@<YOUR_SERVER_IP>
```

## 4. Deploy the Application

1. **Clone your repository** (or copy files):
   If your code is on GitHub:
   ```bash
   git clone <YOUR_GITHUB_REPO_URL> app
   cd app
   ```
   *Alternatively, use `scp` to copy files from your local machine:*
   ```bash
   scp -i key.pem -r . ubuntu@<YOUR_SERVER_IP>:~/app
   ```

2. **Start the Containers**:
   ```bash
   docker compose up -d --build
   ```

3. **Verify Status**:
   ```bash
   docker compose ps
   ```
   You should see 3 containers running: `resume_screener_nginx`, `resume_screener_web`, and `resume_screener_agent`.

## 5. Access the App
Open your browser and visit:
`http://<YOUR_SERVER_IP>`

You should see the Resume Screening System!

---
## Troubleshooting
- **Cannot connect?** Check your Cloud Provider's "Security Groups" or "Firewall Rules". Ensure Inbound Rule for Port 80 (Source: 0.0.0.0/0) is enabled.
- **Logs?** Run `docker compose logs -f` to see what is happening inside the containers.
