import logging
import azure.functions as func
from azure.storage.blob import BlobServiceClient
import os
from datetime import datetime

def main(req: func.HttpRequest) -> func.HttpResponse:
    logging.info("UploadBill function processed a request.")

    # Attempt to read the form data. This is a multi-part form upload.
    try:
        form_data = req.form
    except ValueError:
        return func.HttpResponse("Expected multipart/form-data", status_code=400)

    location_id = form_data.get('location_id')
    truck_id = form_data.get('truck_id')
    bill_id = form_data.get('bill_id')
    file_item = req.files.get('file')  # The file input has name="file"

    if not location_id or not file_item:
        return func.HttpResponse("Error: location_id and file are required.", status_code=400)

    # Build a unique filename
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    filename_parts = [location_id, timestamp]
    if truck_id:
        filename_parts.append(truck_id)
    if bill_id:
        filename_parts.append(bill_id)

    filename = "_".join(filename_parts) + ".jpg"

    # Get the Azure storage connection string from environment variable
    connection_str = os.environ.get("AZURE_STORAGE_CONNECTION_STRING")
    if not connection_str:
        return func.HttpResponse(
            "Error: AZURE_STORAGE_CONNECTION_STRING is not set.",
            status_code=500
        )

    container_name = "uploaded-bills"  # Make sure this container exists in your Storage Account

    try:
        # Connect to Azure Blob Storage and upload
        blob_service_client = BlobServiceClient.from_connection_string(connection_str)
        blob_client = blob_service_client.get_blob_client(container=container_name, blob=filename)
        blob_client.upload_blob(file_item.stream, overwrite=True)

        return func.HttpResponse(
            f"File uploaded: {filename}",
            status_code=200
        )
    except Exception as e:
        logging.error(str(e))
        return func.HttpResponse(f"Error uploading file: {str(e)}", status_code=500)
