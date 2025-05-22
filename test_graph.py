import os
import asyncio
from dotenv import load_dotenv
from azure.identity import ClientSecretCredential
from msgraph import GraphServiceClient
import traceback

load_dotenv()

async def test_graph_connection():
    # Print configuration details for debugging
    print("Loaded environment variables:")
    print(f"CLIENT_ID: {os.getenv('CLIENT_ID')}")
    print(f"TENANT_ID: {os.getenv('TENANT_ID')}")
    print(f"CLIENT_SECRET exists: {bool(os.getenv('CLIENT_SECRET'))}")
    
    # Attempt connection with explicit configuration
    try:
        # Create the credential
        credential = ClientSecretCredential(
            tenant_id=os.getenv('TENANT_ID'),
            client_id=os.getenv('CLIENT_ID'),
            client_secret=os.getenv('CLIENT_SECRET')
        )
        
        # Initialize Graph with explicit configuration
        graph_client = GraphServiceClient(
            credentials=credential,
            scopes=["https://graph.microsoft.com/.default"]
        )
        
        # Test the connection by requesting something simple
        print("\nTesting connection...")
        result = await graph_client.solutions.booking_businesses.get()
        
        if result and hasattr(result, 'value'):
            print(f"\nConnection successful! Found {len(result.value)} businesses:")
            for business in result.value:
                print(f"- {getattr(business, 'display_name', 'Unnamed')} (ID: {getattr(business, 'id', 'No ID')})")
        else:
            print("\nConnection successful, but no businesses found.")
            
        return True
    except Exception as e:
        print(f"\nError connecting to Microsoft Graph API: {str(e)}")
        print("\nDetailed traceback:")
        traceback.print_exc()
        return False

if __name__ == "__main__":
    asyncio.run(test_graph_connection()) 