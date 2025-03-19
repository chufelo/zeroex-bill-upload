import logging
import azure.functions as func
from azure.storage.blob import BlobServiceClient
import os
from datetime import datetime
import traceback

def main(req: func.HttpRequest) -> func.HttpResponse:
    logging.info("UploadBill function processed a request.")

    # Log environment variables (excluding actual connection string values for security)
    env_vars = {k: "PRESENT" if k.startswith("AZURE") and "CONNECTION" in k else v[:10] + "..." 
                for k, v in os.environ.items() if isinstance(v, str) and len(v) > 10}
    logging.info(f"Environment variables: {env_vars}")

    # Attempt to read the form data. This is a multi-part form upload.
    try:
        form_data = req.form
        logging.info(f"Form data keys: {list(form_data.keys())}")
    except ValueError as e:
        logging.error(f"Form data error: {str(e)}")
        return func.HttpResponse("Expected multipart/form-data", status_code=400)

    location_id = form_data.get('location_id')
    truck_id = form_data.get('truck_id', '')
    bill_id = form_data.get('bill_id', '')
    file_item = req.files.get('file')  # The file input has name="file"

    logging.info(f"Received request - location_id: {location_id}, truck_id: {truck_id}, bill_id: {bill_id}")
    
    if not location_id:
        return func.HttpResponse("Error: location_id is required.", status_code=400)
    
    if not file_item:
        return func.HttpResponse("Error: No file was uploaded.", status_code=400)
    
    logging.info(f"File received: {file_item.filename}, Content type: {file_item.content_type}")

    # Build a unique filename
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    filename_parts = [location_id, timestamp]
    if truck_id:
        filename_parts.append(truck_id)
    if bill_id:
        filename_parts.append(bill_id)

    filename = "_".join(filename_parts) + ".jpg"
    logging.info(f"Generated filename: {filename}")

    # Get the Azure storage connection string from environment variable
    # First try direct environment variable
    connection_str = os.environ.get("AZURE_STORAGE_CONNECTION_STRING")
    
    # If not found, try alternative environment variable names
    if not connection_str:
        # Check for other possible names
        alt_keys = [k for k in os.environ.keys() if "STORAGE" in k and "CONNECTION" in k]
        logging.warning(f"AZURE_STORAGE_CONNECTION_STRING not found. Alternative keys: {alt_keys}")
        
        # Try to use a fallback if available
        if alt_keys:
            connection_str = os.environ.get(alt_keys[0])
            logging.info(f"Using alternative connection string key: {alt_keys[0]}")
    
    if not connection_str:
        error_msg = "Error: Storage connection string is not set in environment variables."
        logging.error(error_msg)
        return func.HttpResponse(error_msg, status_code=500)

    # Manually set container name to match the one in your Azure Storage
    container_name = "uploaded-bills"
    logging.info(f"Using container: {container_name}")

    try:
        # Connect to Azure Blob Storage and upload
        logging.info("Connecting to Blob Storage...")
        blob_service_client = BlobServiceClient.from_connection_string(connection_str)
        
        # Verify container exists or create it
        container_client = blob_service_client.get_container_client(container_name)
        if not container_client.exists():
            logging.warning(f"Container '{container_name}' does not exist. Creating it...")
            container_client.create_container()
            logging.info(f"Container '{container_name}' created.")
        
        # Get blob client and upload
        logging.info(f"Uploading blob: {filename}")
        blob_client = container_client.get_blob_client(filename)
        blob_client.upload_blob(file_item.stream, overwrite=True)
        
        success_msg = f"File uploaded successfully: {filename}"
        logging.info(success_msg)
        return func.HttpResponse(success_msg, status_code=200)
    
    except Exception as e:
        error_details = traceback.format_exc()
        logging.error(f"Error during upload: {str(e)}\n{error_details}")
        
        # Provide a meaningful error message based on the exception type
        error_msg = f"Error uploading file: {str(e)}"
        
        # Check for common connection string issues
        if "AuthenticationFailed" in str(e):
            error_msg = "Authentication failed. The storage account key may be invalid or expired."
        elif "ContainerNotFound" in str(e):
            error_msg = f"Container '{container_name}' not found in the storage account."
        elif "NameNotResolved" in str(e) or "ConnectFailure" in str(e):
            error_msg = "Could not connect to Azure Storage. Network issue or invalid storage account name."
        
        return func.HttpResponse(error_msg, status_code=500)
