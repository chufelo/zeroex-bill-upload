"""
This script tests the connection to Azure Blob Storage.
Run it with the connection string to verify access to the container.

Usage:
python test_storage_connection.py
"""

import os
import sys
from azure.storage.blob import BlobServiceClient

def test_connection(connection_string, container_name="uploaded-bills"):
    """Test connection to Azure Blob Storage and list blobs in the container."""
    try:
        print(f"Testing connection to Azure Blob Storage...")
        print(f"Connecting to container: {container_name}")
        
        # Create blob service client
        blob_service_client = BlobServiceClient.from_connection_string(connection_string)
        
        # Get container client
        container_client = blob_service_client.get_container_client(container_name)
        
        # Check if container exists
        if not container_client.exists():
            print(f"Container '{container_name}' does not exist.")
            print("Creating container...")
            container_client.create_container()
            print(f"Container '{container_name}' created successfully.")
        else:
            print(f"Container '{container_name}' exists.")
            
            # List blobs in container
            print("Listing blobs in container:")
            blobs = list(container_client.list_blobs())
            
            if blobs:
                for blob in blobs:
                    print(f" - {blob.name} ({blob.size} bytes)")
            else:
                print(" - No blobs found in container")
        
        # Create a test blob
        test_blob_name = "connection_test.txt"
        print(f"Creating test blob: {test_blob_name}")
        
        blob_client = container_client.get_blob_client(test_blob_name)
        blob_client.upload_blob("This is a connection test file.", overwrite=True)
        
        print("Test blob created successfully.")
        print("Connection test completed successfully!")
        return True
        
    except Exception as e:
        print(f"Error: {str(e)}")
        return False

if __name__ == "__main__":
    # Check if connection string is provided as environment variable
    connection_string = os.environ.get("AZURE_STORAGE_CONNECTION_STRING")
    
    if not connection_string:
        print("ERROR: AZURE_STORAGE_CONNECTION_STRING environment variable not set.")
        print("Please set the environment variable with your Azure Storage connection string:")
        print("  Windows: set AZURE_STORAGE_CONNECTION_STRING=your_connection_string")
        print("  PowerShell: $env:AZURE_STORAGE_CONNECTION_STRING='your_connection_string'")
        print("  Linux/Mac: export AZURE_STORAGE_CONNECTION_STRING='your_connection_string'")
        sys.exit(1)
    
    success = test_connection(connection_string)
    if not success:
        sys.exit(1)
