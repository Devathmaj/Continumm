# Continumm Infrastructure - Variables
# Define all configurable parameters for infrastructure provisioning

variable "project_name" {
  description = "Project name used for resource naming"
  type        = string
  default     = "continumm"
}

variable "environment" {
  description = "Environment name (production, staging, development)"
  type        = string
  default     = "production"
  
  validation {
    condition     = contains(["production", "staging", "development"], var.environment)
    error_message = "Environment must be production, staging, or development."
  }
}

variable "location" {
  description = "Azure region for resources"
  type        = string
  default     = "eastus"
}

variable "vm_size" {
  description = "Size of the virtual machine"
  type        = string
  default     = "Standard_B2s"
  
  # Standard_B2s: 2 vCPUs, 4 GB RAM - Good for small production
  # Standard_B2ms: 2 vCPUs, 8 GB RAM - Better for production
  # Standard_D2s_v3: 2 vCPUs, 8 GB RAM - Production recommended
}

variable "admin_username" {
  description = "Admin username for SSH access"
  type        = string
  default     = "continumm"
}

variable "ssh_public_key" {
  description = "SSH public key for VM access (required)"
  type        = string
  
  validation {
    condition     = length(var.ssh_public_key) > 0
    error_message = "SSH public key is required for VM access."
  }
}

variable "allowed_ssh_ips" {
  description = "List of IP addresses allowed to SSH into the VM"
  type        = list(string)
  default     = ["0.0.0.0/0"]
  
  # IMPORTANT: In production, restrict to specific IPs
  # Example: ["203.0.113.0/24", "198.51.100.42/32"]
}

# Disk Configuration

variable "os_disk_type" {
  description = "Type of OS disk (Standard_LRS, StandardSSD_LRS, Premium_LRS)"
  type        = string
  default     = "StandardSSD_LRS"
}

variable "os_disk_size" {
  description = "Size of OS disk in GB"
  type        = number
  default     = 30
}

variable "create_data_disk" {
  description = "Whether to create and attach a data disk"
  type        = bool
  default     = true
}

variable "data_disk_type" {
  description = "Type of data disk (Standard_LRS, StandardSSD_LRS, Premium_LRS)"
  type        = string
  default     = "StandardSSD_LRS"
}

variable "data_disk_size" {
  description = "Size of data disk in GB (for Docker volumes, logs, etc.)"
  type        = number
  default     = 50
}

# Software versions

variable "docker_compose_version" {
  description = "Docker Compose version to install"
  type        = string
  default     = "2.24.0"
}

# Tags

variable "additional_tags" {
  description = "Additional tags to apply to all resources"
  type        = map(string)
  default     = {}
}
