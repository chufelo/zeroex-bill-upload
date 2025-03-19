import logging
import azure.functions as func
from azure.storage.blob import BlobServiceClient
import os
from datetime import datetime

def main(req: func.HttpRequest) -> func.HttpResponse:
    """
    Simple function to upload a file to Azure Blob Storage.
    """
    logging.info('Processing bill upload request')
    
    try:
        # Extract form data
        form = req.form
        location_id = form.get('location_id', '')
        truck_id = form.get('truck_id', '')
        bill_id = form.get('bill_id', '')
        file_data = req.files.get('file')
        
        logging.info(f'Upload requested with location_id: {location_id}')
        
        # Validate required fields
        if not location_id:
            return func.HttpResponse("Location ID is required", status_code=400)
        
        if not file_data:
            return func.HttpResponse("No file was uploaded", status_code=400)
            
        # Get connection string
        connection_string = os.environ.get('AZURE_STORAGE_CONNECTION_STRING')
        if not connection_string:
            logging.error('AZURE_STORAGE_CONNECTION_STRING environment variable not set')
            return func.HttpResponse(
                "Server configuration error: Storage connection string not set",
                status_code=500
            )
        
        # Create unique filename
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        filename_parts = [location_id, timestamp]
        
        if truck_id:
            filename_parts.append(truck_id)
        if bill_id:
            filename_parts.append(bill_id)
            
        filename = "_".join(filename_parts) + ".jpg"
        
        # Upload to blob storage
        blob_service_client = BlobServiceClient.from_connection_string(connection_string)
        container_name = "uploaded-bills"
        
        # Get container client
        container_client = blob_service_client.get_container_client(container_name)
        
        # Create container if it doesn't exist
        if not container_client.exists():
            logging.info(f'Creating container: {container_name}')
            container_client.create_container()
        
        # Get blob client
        blob_client = container_client.get_blob_client(filename)
        
        # Upload the file
        blob_client.upload_blob(file_data.stream, overwrite=True)
        
        logging.info(f'Successfully uploaded: {filename}')
        return func.HttpResponse(f"File uploaded successfully: {filename}", status_code=200)
        
    except Exception as e:
        logging.exception(f'Error in upload: {str(e)}')
        return func.HttpResponse(f"Error processing upload: {str(e)}", status_code=500)
