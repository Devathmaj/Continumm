# Continumm Infrastructure - Outputs
# Display important information after infrastructure provisioning

output "resource_group_name" {
  description = "Name of the resource group"
  value       = azurerm_resource_group.continumm.name
}

output "vm_name" {
  description = "Name of the virtual machine"
  value       = azurerm_linux_virtual_machine.continumm.name
}

output "vm_id" {
  description = "ID of the virtual machine"
  value       = azurerm_linux_virtual_machine.continumm.id
}

output "public_ip_address" {
  description = "Public IP address of the VM"
  value       = azurerm_public_ip.continumm.ip_address
}

output "private_ip_address" {
  description = "Private IP address of the VM"
  value       = azurerm_network_interface.continumm.private_ip_address
}

output "ssh_command" {
  description = "SSH command to connect to the VM"
  value       = "ssh ${var.admin_username}@${azurerm_public_ip.continumm.ip_address}"
}

output "vm_size" {
  description = "Size of the virtual machine"
  value       = azurerm_linux_virtual_machine.continumm.size
}

output "os_disk_size" {
  description = "Size of OS disk in GB"
  value       = azurerm_linux_virtual_machine.continumm.os_disk[0].disk_size_gb
}

output "data_disk_id" {
  description = "ID of the data disk (if created)"
  value       = var.create_data_disk ? azurerm_managed_disk.continumm_data[0].id : null
}

output "nsg_id" {
  description = "ID of the network security group"
  value       = azurerm_network_security_group.continumm.id
}

output "vnet_id" {
  description = "ID of the virtual network"
  value       = azurerm_virtual_network.continumm.id
}

# Connection details for convenience
output "connection_info" {
  description = "Complete connection information"
  value = {
    ssh           = "ssh ${var.admin_username}@${azurerm_public_ip.continumm.ip_address}"
    public_ip     = azurerm_public_ip.continumm.ip_address
    http          = "http://${azurerm_public_ip.continumm.ip_address}"
    https         = "https://${azurerm_public_ip.continumm.ip_address}"
  }
}

# Post-deployment instructions
output "next_steps" {
  description = "Instructions for next steps after infrastructure is ready"
  value = <<-EOT
    
    Infrastructure provisioned successfully!
    
    Next steps:
    1. SSH into the VM:
       ${output.ssh_command.value}
    
    2. Wait for cloud-init to complete (check status):
       cloud-init status --wait
    
    3. Verify Docker is installed:
       docker --version
       docker-compose --version
    
    4. Clone your repository:
       git clone <your-repo-url>
    
    5. Deploy the stack:
       cd deploy
       ./deploy.sh
    
    6. Access your application:
       http://${azurerm_public_ip.continumm.ip_address}
    
    Grafana: http://${azurerm_public_ip.continumm.ip_address}:3000
    Prometheus: http://${azurerm_public_ip.continumm.ip_address}:9090
  EOT
}
