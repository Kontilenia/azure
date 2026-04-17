@description('Azure region for all resources.')
param location string = resourceGroup().location

@description('Name for the Azure AI Services account (AI Foundry hub).')
@minLength(2)
@maxLength(64)
param accountName string

@description('Name for the Azure AI Foundry project.')
@minLength(2)
@maxLength(64)
param projectName string

@description('Tokens-per-minute capacity (in thousands) for the model deployment.')
@minValue(1)
param deploymentCapacity int = 10

var modelName = 'text-embedding-3-small'
var modelVersion = '1'
var deploymentName = 'text-embedding-3-small'

// AIServices kind is required for Azure AI Foundry projects
resource aiServices 'Microsoft.CognitiveServices/accounts@2024-10-01' = {
  name: accountName
  location: location
  kind: 'AIServices'
  identity: {
    type: 'SystemAssigned'
  }
  sku: {
    name: 'S0'
  }
  properties: {
    customSubDomainName: accountName
    disableLocalAuth: false
    publicNetworkAccess: 'Enabled'
    networkAcls: {
      defaultAction: 'Allow'
      bypass: 'AzureServices'
    }
  }
}

resource project 'Microsoft.CognitiveServices/accounts/projects@2025-06-01' = {
  parent: aiServices
  name: projectName
  location: location
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    displayName: projectName
  }
}

resource modelDeployment 'Microsoft.CognitiveServices/accounts/deployments@2024-10-01' = {
  parent: aiServices
  name: deploymentName
  sku: {
    name: 'GlobalStandard'
    capacity: deploymentCapacity
  }
  properties: {
    model: {
      format: 'OpenAI'
      name: modelName
      version: modelVersion
    }
    versionUpgradeOption: 'OnceCurrentVersionExpired'
  }
}

output accountEndpoint string = aiServices.properties.endpoint
output aiServicesId string = aiServices.id
output projectId string = project.id
output deploymentName string = modelDeployment.name
