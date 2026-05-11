# Continumm Infrastructure - Main Configuration
# Provisions complete VM infrastructure for production deployment
# No manual setup required - terraform apply creates working environment

terraform {
  required_version = ">= 1.0"
  
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 3.0"
    }
  }
  
  # Backend configuration for state management
  # Uncomment and configure for production use
  # backend "azurerm" {
  #   resource_group_name  = "continumm-tfstate"
  #   storage_account_name = "continuummtfstate"
  #   container_name       = "tfstate"
  #   key                  = "production.terraform.tfstate"
  # }
}

provider "azurerm" {
  features {
    virtual_machine {
      delete_os_disk_on_deletion     = true
      graceful_shutdown              = true
      skip_shutdown_and_force_delete = false
    }
    
    resource_group {
      prevent_deletion_if_contains_resources = false
    }
  }
}

# Resource Group
resource "azurerm_resource_group" "continumm" {
  name     = "${var.project_name}-${var.environment}"
  location = var.location
  
  tags = local.common_tags
}

# Virtual Network
resource "azurerm_virtual_network" "continumm" {
  name                = "${var.project_name}-vnet"
  address_space       = ["10.0.0.0/16"]
  location            = azurerm_resource_group.continumm.location
  resource_group_name = azurerm_resource_group.continumm.name
  
  tags = local.common_tags
}

# Subnet
resource "azurerm_subnet" "continumm" {
  name                 = "${var.project_name}-subnet"
  resource_group_name  = azurerm_resource_group.continumm.name
  virtual_network_name = azurerm_virtual_network.continumm.name
  address_prefixes     = ["10.0.1.0/24"]
}

# Network Security Group
resource "azurerm_network_security_group" "continumm" {
  name                = "${var.project_name}-nsg"
  location            = azurerm_resource_group.continumm.location
  resource_group_name = azurerm_resource_group.continumm.name
  
  tags = local.common_tags
}

# Security Rules

# SSH Access - Restricted to allowed IPs only
resource "azurerm_network_security_rule" "ssh" {
  name                        = "AllowSSH"
  priority                    = 100
  direction                   = "Inbound"
  access                      = "Allow"
  protocol                    = "Tcp"
  source_port_range           = "*"
  destination_port_range      = "22"
  source_address_prefixes     = var.allowed_ssh_ips
  destination_address_prefix  = "*"
  resource_group_name         = azurerm_resource_group.continumm.name
  network_security_group_name = azurerm_network_security_group.continumm.name
}

# HTTP Access
resource "azurerm_network_security_rule" "http" {
  name                        = "AllowHTTP"
  priority                    = 110
  direction                   = "Inbound"
  access                      = "Allow"
  protocol                    = "Tcp"
  source_port_range           = "*"
  destination_port_range      = "80"
  source_address_prefix       = "*"
  destination_address_prefix  = "*"
  resource_group_name         = azurerm_resource_group.continumm.name
  network_security_group_name = azurerm_network_security_group.continumm.name
}

# HTTPS Access
resource "azurerm_network_security_rule" "https" {
  name                        = "AllowHTTPS"
  priority                    = 120
  direction                   = "Inbound"
  access                      = "Allow"
  protocol                    = "Tcp"
  source_port_range           = "*"
  destination_port_range      = "443"
  source_address_prefix       = "*"
  destination_address_prefix  = "*"
  resource_group_name         = azurerm_resource_group.continumm.name
  network_security_group_name = azurerm_network_security_group.continumm.name
}

# Deny all other inbound traffic
resource "azurerm_network_security_rule" "deny_all" {
  name                        = "DenyAllInbound"
  priority                    = 4096
  direction                   = "Inbound"
  access                      = "Deny"
  protocol                    = "*"
  source_port_range           = "*"
  destination_port_range      = "*"
  source_address_prefix       = "*"
  destination_address_prefix  = "*"
  resource_group_name         = azurerm_resource_group.continumm.name
  network_security_group_name = azurerm_network_security_group.continumm.name
}

# Public IP
resource "azurerm_public_ip" "continumm" {
  name                = "${var.project_name}-pip"
  location            = azurerm_resource_group.continumm.location
  resource_group_name = azurerm_resource_group.continumm.name
  allocation_method   = "Static"
  sku                 = "Standard"
  
  tags = local.common_tags
}

# Network Interface
resource "azurerm_network_interface" "continumm" {
  name                = "${var.project_name}-nic"
  location            = azurerm_resource_group.continumm.location
  resource_group_name = azurerm_resource_group.continumm.name
  
  ip_configuration {
    name                          = "internal"
    subnet_id                     = azurerm_subnet.continumm.id
    private_ip_address_allocation = "Dynamic"
    public_ip_address_id          = azurerm_public_ip.continumm.id
  }
  
  tags = local.common_tags
}

# Associate NSG with Network Interface
resource "azurerm_network_interface_security_group_association" "continumm" {
  network_interface_id      = azurerm_network_interface.continumm.id
  network_security_group_id = azurerm_network_security_group.continumm.id
}

# SSH Key for VM access
resource "azurerm_ssh_public_key" "continumm" {
  name                = "${var.project_name}-ssh-key"
  resource_group_name = azurerm_resource_group.continumm.name
  location            = azurerm_resource_group.continumm.location
  public_key          = var.ssh_public_key
  
  tags = local.common_tags
}

# Virtual Machine
resource "azurerm_linux_virtual_machine" "continumm" {
  name                  = "${var.project_name}-vm"
  location              = azurerm_resource_group.continumm.location
  resource_group_name   = azurerm_resource_group.continumm.name
  network_interface_ids = [azurerm_network_interface.continumm.id]
  size                  = var.vm_size
  
  # Admin user configuration
  admin_username                  = var.admin_username
  disable_password_authentication = true
  
  admin_ssh_key {
    username   = var.admin_username
    public_key = var.ssh_public_key
  }
  
  # OS Disk
  os_disk {
    name                 = "${var.project_name}-osdisk"
    caching              = "ReadWrite"
    storage_account_type = var.os_disk_type
    disk_size_gb         = var.os_disk_size
  }
  
  # Source image - Ubuntu 22.04 LTS
  source_image_reference {
    publisher = "Canonical"
    offer     = "0001-com-ubuntu-server-jammy"
    sku       = "22_04-lts-gen2"
    version   = "latest"
  }
  
  # Custom data for initial setup
  custom_data = base64encode(templatefile("${path.module}/cloud-init.yaml", {
    docker_compose_version = var.docker_compose_version
    admin_username         = var.admin_username
  }))
  
  # Boot diagnostics
  boot_diagnostics {
    storage_account_uri = null
  }
  
  tags = local.common_tags
  
  depends_on = [
    azurerm_network_interface_security_group_association.continumm
  ]
}

# Data Disk (optional, for persistent data)
resource "azurerm_managed_disk" "continumm_data" {
  count = var.create_data_disk ? 1 : 0
  
  name                 = "${var.project_name}-datadisk"
  location             = azurerm_resource_group.continumm.location
  resource_group_name  = azurerm_resource_group.continumm.name
  storage_account_type = var.data_disk_type
  create_option        = "Empty"
  disk_size_gb         = var.data_disk_size
  
  tags = local.common_tags
}

# Attach Data Disk
resource "azurerm_virtual_machine_data_disk_attachment" "continumm_data" {
  count = var.create_data_disk ? 1 : 0
  
  managed_disk_id    = azurerm_managed_disk.continumm_data[0].id
  virtual_machine_id = azurerm_linux_virtual_machine.continumm.id
  lun                = 0
  caching            = "ReadWrite"
}

# Local variables
locals {
  common_tags = {
    Environment = var.environment
    Project     = var.project_name
    ManagedBy   = "Terraform"
    CreatedAt   = timestamp()
  }
}
