# Continumm Infrastructure - Terraform Guide

Complete Infrastructure as Code for production VM provisioning.

## 📋 What This Provisions

- ✅ **Virtual Machine** - Ubuntu 22.04 LTS with Docker pre-installed
- ✅ **Security Groups** - SSH, HTTP, HTTPS access with configurable rules
- ✅ **SSH Access** - Key-based authentication, no password login
- ✅ **Disk Storage** - OS disk + optional data disk for persistent storage
- ✅ **Networking** - VNet, subnet, public IP, network security group
- ✅ **System Configuration** - Cloud-init automated setup

## 🚀 Quick Start

### Prerequisites

1. **Azure CLI** installed and logged in:
   ```powershell
   az login
   az account show
   ```

2. **Terraform** installed (>= 1.0):
   ```powershell
   terraform --version
   ```

3. **SSH Key Pair** generated:
   ```powershell
   ssh-keygen -t rsa -b 4096 -f ~/.ssh/continumm_key
   ```

### Deploy Infrastructure

```powershell
cd infra/terraform

# 1. Create terraform.tfvars from example
Copy-Item terraform.tfvars.example terraform.tfvars

# 2. Edit terraform.tfvars - add your SSH public key
notepad terraform.tfvars

# 3. Initialize Terraform
terraform init

# 4. Preview changes
terraform plan

# 5. Apply infrastructure
terraform apply
```

**Terraform will output the VM IP and SSH command when complete.**

## 📝 Configuration

### Required Variables

Edit `terraform.tfvars`:

```hcl
# REQUIRED: Your SSH public key
ssh_public_key = "ssh-rsa AAAAB3NzaC1... your-key-here"

# Get your public key:
# Windows: Get-Content ~/.ssh/continumm_key.pub
# Linux/Mac: cat ~/.ssh/continumm_key.pub
```

### Security Configuration

**IMPORTANT**: Restrict SSH access to your IP addresses:

```hcl
allowed_ssh_ips = [
  "203.0.113.42/32",    # Your office IP
  "198.51.100.0/24"     # Your VPN range
]
```

Never use `0.0.0.0/0` in production!

### VM Sizing

Choose appropriate VM size for your workload:

```hcl
# Development/Testing
vm_size = "Standard_B2s"    # 2 vCPUs, 4 GB RAM

# Production (recommended)
vm_size = "Standard_B2ms"   # 2 vCPUs, 8 GB RAM
vm_size = "Standard_D2s_v3" # 2 vCPUs, 8 GB RAM (better performance)
```

### Disk Configuration

```hcl
# OS Disk
os_disk_type = "StandardSSD_LRS"  # Standard SSD (recommended)
os_disk_size = 30                  # GB

# Data Disk (for Docker volumes, metrics, logs)
create_data_disk = true
data_disk_type   = "StandardSSD_LRS"
data_disk_size   = 50              # GB
```

## 🔧 What Gets Installed

Cloud-init automatically configures:

### Software
- Docker Engine (latest)
- Docker Compose (configurable version)
- Git
- Python 3
- System monitoring tools (htop, sysstat, iotop)

### System Configuration
- Firewall (UFW) configured for HTTP, HTTPS, SSH
- Log rotation for application logs
- System tuning for container workloads
- Security updates (unattended-upgrades)
- Docker daemon optimized settings

### Directories Created
- `/opt/continumm` - Application deployment
- `/var/log/continumm` - Application logs
- `/mnt/data` - Data disk mount (if created)

## 📊 Terraform Commands

```powershell
# Initialize (first time only)
terraform init

# Validate configuration
terraform validate

# Format code
terraform fmt

# Preview changes
terraform plan

# Apply changes
terraform apply

# Show current state
terraform show

# View outputs
terraform output

# SSH command
terraform output -raw ssh_command

# Destroy infrastructure
terraform destroy
```

## 🔗 After Provisioning

### 1. Wait for Cloud-Init

Cloud-init takes 2-5 minutes to complete setup.

```powershell
# SSH into VM (get command from output)
terraform output -raw ssh_command

# Check cloud-init status
cloud-init status --wait

# View cloud-init logs
sudo cat /var/log/cloud-init-output.log
```

### 2. Verify Installation

```bash
# Check Docker
docker --version
docker-compose --version

# Check system
htop
df -h
```

### 3. Deploy Application

```bash
# Clone repository
cd /opt/continumm
git clone <your-repo-url> .

# Deploy stack
cd deploy
./deploy.sh
```

### 4. Access Application

```
HTTP:       http://<VM-IP>
Grafana:    http://<VM-IP>:3000
Prometheus: http://<VM-IP>:9090
```

Get VM IP: `terraform output public_ip_address`

## 🔒 Security Features

### Network Security
- Network Security Group with explicit rules
- SSH restricted to allowed IPs only
- Deny-all rule for unspecified traffic
- Public IP with DDoS protection

### VM Security
- SSH key authentication only (no passwords)
- Firewall (UFW) enabled by default
- Automatic security updates
- Non-root user for applications

### Data Protection
- Encrypted disks (Azure default)
- Separate data disk for persistent storage
- Regular backups recommended

## 📈 Monitoring and Maintenance

### Check VM Status

```powershell
# From local machine
az vm show --resource-group continumm-production --name continumm-vm --show-details

# Check if running
az vm get-instance-view --resource-group continumm-production --name continumm-vm
```

### View Costs

```powershell
az consumption usage list --start-date 2025-01-01 --end-date 2025-01-31
```

### Backup and Recovery

```powershell
# Create VM backup
az backup protection enable-for-vm \
  --resource-group continumm-production \
  --vault-name continumm-vault \
  --vm continumm-vm \
  --policy-name DefaultPolicy
```

## 🗑️ Cleanup

### Destroy Infrastructure

```powershell
terraform destroy
```

This removes:
- Virtual Machine
- Disks
- Network interfaces
- Public IP
- Security groups
- Virtual network
- Resource group

**WARNING**: This is irreversible. Backup data first!

## 🔍 Troubleshooting

### SSH Connection Failed

```powershell
# Verify public IP
terraform output public_ip_address

# Check NSG rules
az network nsg rule list --resource-group continumm-production --nsg-name continumm-nsg

# Verify your IP is allowed
curl ifconfig.me
```

### Cloud-Init Failed

```bash
# SSH into VM
ssh continumm@<VM-IP>

# Check status
cloud-init status

# View logs
sudo cat /var/log/cloud-init.log
sudo cat /var/log/cloud-init-output.log
```

### Terraform State Issues

```powershell
# Refresh state
terraform refresh

# Unlock state (if locked)
terraform force-unlock <LOCK_ID>

# Re-import resource
terraform import azurerm_linux_virtual_machine.continumm /subscriptions/.../resourceGroups/.../providers/Microsoft.Compute/virtualMachines/continumm-vm
```

## 📁 File Structure

```
infra/terraform/
├── main.tf                      # Main infrastructure configuration
├── variables.tf                 # Variable definitions
├── outputs.tf                   # Output definitions
├── cloud-init.yaml             # VM initialization script
├── terraform.tfvars.example    # Example configuration
├── .gitignore                  # Git ignore rules
└── README.md                   # This file
```

## 🎯 Production Checklist

Before deploying to production:

- [ ] Replace default SSH public key
- [ ] Restrict `allowed_ssh_ips` to specific IPs
- [ ] Choose appropriate VM size
- [ ] Configure backup strategy
- [ ] Set up remote state storage (Azure Storage)
- [ ] Enable monitoring and alerting
- [ ] Review and adjust disk sizes
- [ ] Configure DNS records
- [ ] Set up SSL/TLS certificates
- [ ] Review security group rules
- [ ] Document access procedures
- [ ] Plan for scaling (if needed)

## 🔄 State Management

### Remote State (Recommended for Production)

Uncomment backend configuration in `main.tf`:

```hcl
terraform {
  backend "azurerm" {
    resource_group_name  = "continumm-tfstate"
    storage_account_name = "continuummtfstate"
    container_name       = "tfstate"
    key                  = "production.terraform.tfstate"
  }
}
```

Create storage account:

```powershell
# Create resource group for state
az group create --name continumm-tfstate --location eastus

# Create storage account
az storage account create --resource-group continumm-tfstate --name continuummtfstate --sku Standard_LRS --encryption-services blob

# Create container
az storage container create --name tfstate --account-name continuummtfstate
```

## 📚 Additional Resources

- [Terraform Azure Provider](https://registry.terraform.io/providers/hashicorp/azurerm/latest/docs)
- [Azure VM Sizes](https://docs.microsoft.com/en-us/azure/virtual-machines/sizes)
- [Cloud-init Documentation](https://cloudinit.readthedocs.io/)

---

**No manual setup. No clicking in console. `terraform apply` == working VM.**
