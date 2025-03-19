import logging
import azure.functions as func
from azure.storage.blob import BlobServiceClient, BlobClient
from azure.core.exceptions import ResourceExistsError, ServiceRequestError, HttpResponseError
import os
from datetime import datetime
import traceback
import time

def main(req: func.HttpRequest) -> func.HttpResponse:
    start_time = time.time()
    request_id = f"req_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
    logging.info(f"[{request_id}] UploadBill function processing request")

    # Log environment variables (excluding actual connection string values for security)
    env_vars = {k: "PRESENT" if (k.startswith("AZURE") and "CONNECTION" in k) or "KEY" in k.upper() 
                else v[:10] + "..." if isinstance(v, str) and len(v) > 10 else v
                for k, v in os.environ.items()}
    logging.info(f"[{request_id}] Environment variables: {env_vars}")

    # Attempt to read the form data. This is a multi-part form upload.
    try:
        form_data = req.form
        logging.info(f"[{request_id}] Form data keys: {list(form_data.keys())}")
    except ValueError as e:
        logging.error(f"[{request_id}] Form data error: {str(e)}")
        return func.HttpResponse("Expected multipart/form-data", status_code=400)

    location_id = form_data.get('location_id', '')
    truck_id = form_data.get('truck_id', '')
    bill_id = form_data.get('bill_id', '')
    file_item = req.files.get('file')  # The file input has name="file"

    logging.info(f"[{request_id}] Received request - location_id: '{location_id}', truck_id: '{truck_id}', bill_id: '{bill_id}'")
    
    if not location_id:
        logging.warning(f"[{request_id}] Missing location_id")
        return func.HttpResponse("Error: location_id is required.", status_code=400)
    
    if not file_item:
        logging.warning(f"[{request_id}] No file was uploaded")
        return func.HttpResponse("Error: No file was uploaded.", status_code=400)
    
    try:
        file_size = len(file_item.stream.read())
        file_item.stream.seek(0)  # Reset pointer after reading
        logging.info(f"[{request_id}] File received: {file_item.filename}, Size: {file_size} bytes, Content type: {file_item.content_type}")
    except Exception as e:
        logging.error(f"[{request_id}] Error reading file: {str(e)}")
        return func.HttpResponse(f"Error reading uploaded file: {str(e)}", status_code=400)

    # Build a unique filename
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    filename_parts = [location_id, timestamp]
    if truck_id:
        filename_parts.append(truck_id)
    if bill_id:
        filename_parts.append(bill_id)

    filename = "_".join(filename_parts) + ".jpg"
    logging.info(f"[{request_id}] Generated filename: {filename}")

    # Get the Azure storage connection string from environment variable
    # First try direct environment variable
    connection_str = os.environ.get("AZURE_STORAGE_CONNECTION_STRING")
    
    # If not found, try alternative environment variable names
    if not connection_str:
        # Check for other possible names
        alt_keys = [k for k in os.environ.keys() if "STORAGE" in k and "CONNECTION" in k]
        logging.warning(f"[{request_id}] AZURE_STORAGE_CONNECTION_STRING not found. Alternative keys: {alt_keys}")
        
        # Try to use a fallback if available
        if alt_keys:
            connection_str = os.environ.get(alt_keys[0])
            logging.info(f"[{request_id}] Using alternative connection string key: {alt_keys[0]}")
    
    if not connection_str:
        error_msg = "Error: Storage connection string is not set in environment variables."
        logging.error(f"[{request_id}] {error_msg}")
        return func.HttpResponse(error_msg, status_code=500)

    # Manually set container name to match the one in your Azure Storage
    container_name = "uploaded-bills"
    logging.info(f"[{request_id}] Using container: {container_name}")

    try:
        # Specify timeout for operations
        timeout = 30  # seconds
        
        # Connect to Azure Blob Storage and upload
        logging.info(f"[{request_id}] Connecting to Blob Storage...")
        blob_service_client = BlobServiceClient.from_connection_string(connection_str, connection_timeout=timeout, read_timeout=timeout)
        
        # Check if the container exists
        container_client = blob_service_client.get_container_client(container_name)
        
        try:
            container_properties = container_client.get_container_properties()
            logging.info(f"[{request_id}] Container exists: {container_name}")
        except HttpResponseError as e:
            if "ContainerNotFound" in str(e):
                logging.warning(f"[{request_id}] Container '{container_name}' does not exist. Creating it...")
                container_client.create_container()
                logging.info(f"[{request_id}] Container '{container_name}' created.")
            else:
                raise
        
        # Get blob client and upload
        logging.info(f"[{request_id}] Creating blob client for {filename}")
        blob_client = container_client.get_blob_client(filename)
        
        # Upload with extended timeout and retry
        logging.info(f"[{request_id}] Starting blob upload")
        blob_client.upload_blob(
            file_item.stream, 
            overwrite=True,
            timeout=timeout,
            max_concurrency=1
        )
        
        elapsed_time = time.time() - start_time
        success_msg = f"File uploaded successfully: {filename} (in {elapsed_time:.2f}s)"
        logging.info(f"[{request_id}] {success_msg}")
        return func.HttpResponse(success_msg, status_code=200)
    
    except Exception as e:
        elapsed_time = time.time() - start_time
        error_details = traceback.format_exc()
        logging.error(f"[{request_id}] Error during upload (after {elapsed_time:.2f}s): {str(e)}\n{error_details}")
        
        # Provide a meaningful error message based on the exception type
        error_msg = f"Error uploading file: {str(e)}"
        
        # Check for common connection string issues
        if "AuthenticationFailed" in str(e):
            error_msg = "Authentication failed. The storage account key may be invalid or expired."
        elif "ContainerNotFound" in str(e):
            error_msg = f"Container '{container_name}' not found in the storage account."
        elif "NameNotResolved" in str(e) or "ConnectFailure" in str(e):
            error_msg = "Could not connect to Azure Storage. Network issue or invalid storage account name."
        elif "Timeout" in str(e) or "timed out" in str(e).lower():
            error_msg = "Upload timed out. Please try again with a smaller file or check your connection."
        elif "Invalid" in str(e) and "Connection" in str(e):
            error_msg = "Invalid storage connection string. Please check your Azure Storage configuration."
        
        return func.HttpResponse(error_msg, status_code=500)
