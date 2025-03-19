# ZeroEx Bill Upload

A solution for uploading bills via QR codes. Workers can scan QR codes in the field to upload bill photos with location metadata.

## Project Structure

- `static/` - Frontend HTML/CSS/JS for the bill upload form
- `api/` - Azure Functions for backend processing
  - `UploadBill/` - Function to handle file upload to Azure Blob Storage

## Setting Up the Storage Connection

For file uploads to work properly, the Azure Function needs access to the Azure Storage account. To set this up:

### 1. Add the Connection String to GitHub Secrets

1. Go to GitHub repository → Settings → Secrets and variables → Actions
2. Add a new secret with name `AZURE_STORAGE_CONNECTION_STRING`
3. For the value, use the connection string for your storage account (from Azure Portal → Storage Account → Access keys)

### 2. Add the Connection String to Azure Static Web App Configuration

1. In Azure Portal, go to your Static Web App
2. Go to Settings → Configuration
3. Add an application setting:
   - Name: `AZURE_STORAGE_CONNECTION_STRING`
   - Value: Your storage connection string

The connection string should look something like:
```
DefaultEndpointsProtocol=https;AccountName=yourstorageaccount;AccountKey=YourAccountKeyHere;EndpointSuffix=core.windows.net
```

### 3. Verify the Container Exists

Ensure the `uploaded-bills` container exists in your Azure Storage account:

1. Go to Azure Portal → Your Storage Account → Containers
2. Check if `uploaded-bills` container exists
3. If not, create a new container named `uploaded-bills`

You can also run the included test script to verify your connection:
```
# Set your connection string (Windows)
set AZURE_STORAGE_CONNECTION_STRING=your_connection_string_here

# Run the test script
python test_storage_connection.py
```

## Troubleshooting

If files are not appearing in the storage container:

1. **Check GitHub Actions**: Make sure the build workflow completed successfully
2. **Verify Environment Variables**: Ensure AZURE_STORAGE_CONNECTION_STRING is properly set
3. **Test Locally**: Run the test_storage_connection.py script to verify access
4. **Check Logs**: In Azure Portal → Static Web App → Functions → Monitor to see function execution logs

## QR Code Generation

To generate QR codes for field locations:

1. Use any QR code generator to create codes that point to:
   ```
   https://your-static-web-app-url/?location_id=YOUR_LOCATION_ID
   ```
   
2. Print these QR codes and place them at the appropriate field locations

3. When scanned, these codes will open the bill upload form with the location pre-filled

## Local Development

To develop locally:

1. Clone the repository
2. Make changes to the static files or API code
3. Run the test script to verify storage connection
4. Commit and push changes to trigger the GitHub Actions deployment
