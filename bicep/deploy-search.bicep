@description('Azure region for the search service.')
param location string = resourceGroup().location

@description('Name for the Azure AI Search service.')
@minLength(2)
@maxLength(60)
param searchServiceName string

@description('Name of the existing AI Services account to connect to.')
param accountName string

resource searchService 'Microsoft.Search/searchServices@2023-11-01' = {
  name: searchServiceName
  location: location
  identity: {
    type: 'SystemAssigned'
  }
  sku: {
    name: 'basic'
  }
  properties: {
    replicaCount: 1
    partitionCount: 1
    publicNetworkAccess: 'enabled'
    // Allow both AAD and API key so AI Foundry can connect via managed identity
    authOptions: {
      aadOrApiKey: {
        aadAuthFailureMode: 'http403'
      }
    }
    // Enable free semantic search tier (needed for RAG re-ranking)
    semanticSearch: 'free'
  }
}

resource existingAccount 'Microsoft.CognitiveServices/accounts@2024-10-01' existing = {
  name: accountName
}

// Grant the AI Services account's identity access to the search service
var searchIndexDataContributorRoleId = '8ebe5a00-799e-43f5-93ac-243d3dce84a7'
var searchServiceContributorRoleId = '7ca78c08-252a-4471-8644-bb5ff32d4ba0'

resource roleAssignmentIndexData 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  scope: searchService
  name: guid(searchService.id, existingAccount.id, searchIndexDataContributorRoleId)
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', searchIndexDataContributorRoleId)
    principalId: existingAccount.identity.principalId
    principalType: 'ServicePrincipal'
  }
}

resource roleAssignmentServiceContributor 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  scope: searchService
  name: guid(searchService.id, existingAccount.id, searchServiceContributorRoleId)
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', searchServiceContributorRoleId)
    principalId: existingAccount.identity.principalId
    principalType: 'ServicePrincipal'
  }
}

// Register the search service as a connection in the Foundry project
resource searchConnection 'Microsoft.CognitiveServices/accounts/connections@2025-09-01' = {
  parent: existingAccount
  name: '${searchServiceName}-connection'
  properties: {
    category: 'CognitiveSearch'
    target: 'https://${searchService.name}.search.windows.net'
    authType: 'AAD'
    isSharedToAll: false
    metadata: {
      ApiVersion: '2024-05-01-preview'
      ApiType: 'azure'
      ResourceId: searchService.id
    }
  }
}

output searchEndpoint string = 'https://${searchService.name}.search.windows.net'
output searchServiceId string = searchService.id
output connectionName string = searchConnection.name
