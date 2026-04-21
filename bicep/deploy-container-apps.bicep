@description('Azure region for all resources.')
param location string = resourceGroup().location

@description('Name of the Azure Container Registry.')
param acrName string

@description('Name of the Container Apps Environment.')
param containerAppsEnvName string

@description('Name of the backend Container App.')
param backendAppName string

@description('Name of the frontend Container App.')
param frontendAppName string

@description('Full image reference for the backend, e.g. myacr.azurecr.io/backend:latest')
param backendImage string

@description('Full image reference for the frontend, e.g. myacr.azurecr.io/frontend:latest')
param frontendImage string

// ── Environment variables for the backend ───────────────────────────────────

@description('Azure AI Foundry project endpoint.')
param azureProjectEndpoint string

@description('AI Search connection name in AI Foundry.')
param aiSearchConnectionName string

@description('AI Search index name.')
param aiSearchIndexName string

@description('Bing connection name in AI Foundry.')
param bingConnectionName string

@description('Agent name.')
param agentName string

// ── Role definition IDs ───────────────────────────────────────────────────────

var cognitiveServicesUserRoleId    = 'a97b65f3-24c7-4388-baec-2e87135dc908'    // Cognitive Services User
var azureAIDeveloperRoleId         = '64702f94-c441-49e6-a78b-ef80e0188fee'    // Azure AI Developer
var searchIndexDataReaderRoleId    = '1407120a-92aa-4202-b7e9-c0e197c71c8f'    // Search Index Data Reader
var searchServiceContributorRoleId = '7ca78c08-252a-4471-8644-bb5ff32d4ba0' // Search Service Contributor
var acrPullRoleId                  = '7f951dda-4ed3-4680-a7ca-43fe172d538d'    // AcrPull

// ── Log Analytics ─────────────────────────────────────────────────────────────

resource logAnalytics 'Microsoft.OperationalInsights/workspaces@2023-09-01' = {
  name: '${containerAppsEnvName}-logs'
  location: location
  properties: {
    sku: { name: 'PerGB2018' }
    retentionInDays: 30
  }
}

// ── Container Registry ────────────────────────────────────────────────────────

resource acr 'Microsoft.ContainerRegistry/registries@2023-07-01' = {
  name: acrName
  location: location
  sku: { name: 'Basic' }
  properties: {
    adminUserEnabled: true
  }
}

// ── Container Apps Environment ────────────────────────────────────────────────

resource env 'Microsoft.App/managedEnvironments@2024-03-01' = {
  name: containerAppsEnvName
  location: location
  properties: {
    appLogsConfiguration: {
      destination: 'log-analytics'
      logAnalyticsConfiguration: {
        customerId: logAnalytics.properties.customerId
        sharedKey: logAnalytics.listKeys().primarySharedKey
      }
    }
  }
}

// ── Backend Container App ─────────────────────────────────────────────────────

resource backend 'Microsoft.App/containerApps@2024-03-01' = {
  name: backendAppName
  location: location
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    managedEnvironmentId: env.id
    configuration: {
      ingress: {
        external: false        // Internal only — frontend calls it via internal FQDN
        targetPort: 8000
        transport: 'http'
        allowInsecure: true    // Allow HTTP from frontend within the environment
      }
      registries: [
        {
          server: acr.properties.loginServer
          username: acr.listCredentials().username
          passwordSecretRef: 'acr-password'
        }
      ]
      secrets: [
        {
          name: 'acr-password'
          value: acr.listCredentials().passwords[0].value
        }
      ]
    }
    template: {
      containers: [
        {
          name: 'backend'
          image: backendImage
          resources: {
            cpu: json('0.5')
            memory: '1Gi'
          }
          env: [
            { name: 'AZURE_PROJECT_ENDPOINT',   value: azureProjectEndpoint   }
            { name: 'AI_SEARCH_CONNECTION_NAME', value: aiSearchConnectionName }
            { name: 'AI_SEARCH_INDEX_NAME',      value: aiSearchIndexName      }
            { name: 'BING_CONNECTION_NAME',      value: bingConnectionName     }
            { name: 'AGENT_NAME',                value: agentName              }
          ]
          probes: [
            {
              type: 'Liveness'
              httpGet: {
                path: '/health'
                port: 8000
              }
              initialDelaySeconds: 15
              periodSeconds: 30
            }
          ]
        }
      ]
      scale: {
        minReplicas: 1
        maxReplicas: 3
      }
    }
  }
}

// Grant backend identity the Azure AI Developer role on the subscription scope
// (so it can reach the AI Foundry project endpoint)
resource backendAIDeveloperRole 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(resourceGroup().id, backend.id, azureAIDeveloperRoleId)
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', azureAIDeveloperRoleId)
    principalId: backend.identity.principalId
    principalType: 'ServicePrincipal'
  }
}

resource backendCognitiveServicesRole 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(resourceGroup().id, backend.id, cognitiveServicesUserRoleId)
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', cognitiveServicesUserRoleId)
    principalId: backend.identity.principalId
    principalType: 'ServicePrincipal'
  }
}

resource backendSearchDataReaderRole 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(resourceGroup().id, backend.id, searchIndexDataReaderRoleId)
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', searchIndexDataReaderRoleId)
    principalId: backend.identity.principalId
    principalType: 'ServicePrincipal'
  }
}

resource backendSearchContributorRole 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(resourceGroup().id, backend.id, searchServiceContributorRoleId)
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', searchServiceContributorRoleId)
    principalId: backend.identity.principalId
    principalType: 'ServicePrincipal'
  }
}

resource backendAcrPullRole 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(resourceGroup().id, backend.id, acrPullRoleId)
  scope: acr
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', acrPullRoleId)
    principalId: backend.identity.principalId
    principalType: 'ServicePrincipal'
  }
}

// ── Frontend Container App ────────────────────────────────────────────────────

resource frontend 'Microsoft.App/containerApps@2024-03-01' = {
  name: frontendAppName
  location: location
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    managedEnvironmentId: env.id
    configuration: {
      ingress: {
        external: true         // Publicly accessible
        targetPort: 8501
        transport: 'http'
        allowInsecure: false
      }
      registries: [
        {
          server: acr.properties.loginServer
          username: acr.listCredentials().username
          passwordSecretRef: 'acr-password'
        }
      ]
      secrets: [
        {
          name: 'acr-password'
          value: acr.listCredentials().passwords[0].value
        }
      ]
    }
    template: {
      containers: [
        {
          name: 'frontend'
          image: frontendImage
          resources: {
            cpu: json('0.25')
            memory: '0.5Gi'
          }
          env: [
            {
              name: 'BACKEND_URL'
              // Internal FQDN: http://<app-name>.<env-default-domain>
              value: 'http://${backend.properties.configuration.ingress.fqdn}'
            }
          ]
        }
      ]
      scale: {
        minReplicas: 1
        maxReplicas: 3
      }
    }
  }
}

// ── Outputs ───────────────────────────────────────────────────────────────────

resource frontendAcrPullRole 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(resourceGroup().id, frontend.id, acrPullRoleId)
  scope: acr
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', acrPullRoleId)
    principalId: frontend.identity.principalId
    principalType: 'ServicePrincipal'
  }
}

output frontendUrl string = 'https://${frontend.properties.configuration.ingress.fqdn}'
output backendInternalFqdn string = backend.properties.configuration.ingress.fqdn
output acrLoginServer string = acr.properties.loginServer
