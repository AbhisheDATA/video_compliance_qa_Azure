#!/bin/bash

# --- CONFIGURATION (Ensure these match your Azure environment) ---
RG_NAME="myResourceGroup"
LOCATION="centralindia"
ACR_NAME="brandguardianacr9294" # Use the name already created or a unique one
ACA_ENV="brand-guardian-env"
APP_NAME="brand-guardian-api"
KV_NAME="brand-kv-1643" # Use the one already created or a unique one
IDENTITY_NAME="brand-guardian-identity"

# Check if logged in
az account show > /dev/null 2>&1
if [ $? -ne 0 ]; then
    echo "❌ Please run 'az login' first."
    exit 1
fi

echo "🚀 Starting Azure Infrastructure Setup (Foundation Only)..."

# 1. Create Resource Group (Soft check)
if [ $(az group exists --name $RG_NAME) = false ]; then
    echo "Creating Resource Group $RG_NAME..."
    az group create --name $RG_NAME --location $LOCATION
else
    echo "Resource Group $RG_NAME exists."
fi

# 2. Create ACR (Idempotent)
echo "--- 2. Ensuring ACR $ACR_NAME ---"
az acr create --resource-group $RG_NAME --name $ACR_NAME --sku Basic --admin-enabled true

# 3. Create Container App Environment (Idempotent)
echo "--- 3. Ensuring Container App Env $ACA_ENV ---"
az containerapp env create \
  --name $ACA_ENV \
  --resource-group $RG_NAME \
  --location $LOCATION

# 4. Create Key Vault
echo "--- 4. Ensuring Key Vault $KV_NAME ---"
az keyvault create --name $KV_NAME --resource-group $RG_NAME --location $LOCATION --enable-rbac-authorization true

# 5. Create Managed Identity
echo "--- 5. Ensuring Managed Identity $IDENTITY_NAME ---"
az identity create --name $IDENTITY_NAME --resource-group $RG_NAME
IDENTITY_ID=$(az identity show --name $IDENTITY_NAME --resource-group $RG_NAME --query "id" --output tsv)
IDENTITY_PRINCIPAL_ID=$(az identity show --name $IDENTITY_NAME --resource-group $RG_NAME --query "principalId" --output tsv)

# 6. Grant Identity Access to Key Vault (RBAC)
echo "--- 6. Granting 'Key Vault Secrets User' role to Identity ---"
az role assignment create \
    --role "Key Vault Secrets User" \
    --assignee $IDENTITY_PRINCIPAL_ID \
    --scope "/subscriptions/$(az account show --query id --output tsv)/resourceGroups/$RG_NAME/providers/Microsoft.KeyVault/vaults/$KV_NAME"

echo "✅ Infrastructure Ready!"
echo "--------------------------------------------------"
echo "CONFIGURATION FOR GITHUB SECRETS:"
echo "ACR_NAME: $ACR_NAME"
echo "ACR_LOGIN_SERVER: $(az acr show --name $ACR_NAME --query loginServer -o tsv)"
echo "KV_NAME: $KV_NAME"
echo "IDENTITY_RESOURCE_ID: $IDENTITY_ID"
echo "--------------------------------------------------"
echo "NEXT STEP: Pushing code to GitHub will now trigger the Deploy workflow."
