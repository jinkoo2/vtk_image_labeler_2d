import requests

class ServerError(Exception):
    """Custom exception for server errors."""
    pass

def get_ping(BASE_URL):
    """
    Ping the server and return the response.
    """
    url = f"{BASE_URL}/ping"
    print(f'pinging the server at {url}')
    
    try:
        response = requests.get(url)
        
        if response.status_code == 200:
            return response.json()
        else:
            error_message = f"Failed to ping server: {response.status_code}, {response.text}"
            print(error_message)
            raise ServerError(error_message)  # Raise a custom exception for server errors
    except requests.exceptions.RequestException as e:
        # Handle network-related errors (e.g., connection issues)
        print(f"An error occurred while pinging the server: {e}")
        raise  # Re-raise the exception to forward it
    