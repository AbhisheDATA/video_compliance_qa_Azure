az cognitiveservices account create \
  --name abhi-openai-9741 \
  --resource-group myResourceGroup \
  --location southeastasia \
  --kind OpenAI \
  --sku S0 \
  --yes


az search service create \
  --name abhi-search-service \
  --resource-group myResourceGroup \
  --location southeastasia \
  --sku basic



az monitor app-insights component create \
  --app abhi-appinsights \
  --location southeastasia \
  --resource-group myResourceGroup \
  --application-type web
