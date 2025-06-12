import os
import requests
import json
import logging

logger = logging.getLogger(__name__)

class GumroadAPIKeyError(ValueError):
    """Custom exception for Gumroad API key errors."""
    pass

def get_gumroad_api_key():
    """
    Retrieves the Gumroad API key from GUMROAD_API_KEY environment variable
    or .gumroad_key file.
    Raises an error if the key is not found.
    """
    api_key = os.environ.get('GUMROAD_API_KEY')
    if api_key:
        logger.info("Gumroad API key found in environment variable.")
        return api_key

    try:
        with open('.gumroad_key', 'r') as f:
            api_key = f.read().strip()
        if api_key:
            logger.info("Gumroad API key found in .gumroad_key file.")
            return api_key
    except FileNotFoundError:
        logger.warning(".gumroad_key file not found.")
        # Fall through to raise error

    raise GumroadAPIKeyError("Gumroad API key not found. Set GUMROAD_API_KEY environment variable or create a .gumroad_key file with the key.")

# The __main__ block for testing get_gumroad_api_key and create_product can remain,
# but it should catch GumroadAPIKeyError specifically now.
# For brevity in this diff, I'll omit the full __main__ block if only the exception type changes there.
# Let's assume the __main__ block is updated to catch GumroadAPIKeyError.

if __name__ == '__main__':
    # Example usage (for testing purposes)
    logging.basicConfig(level=logging.INFO)
    try:
        key = get_gumroad_api_key()
        logger.info(f"Successfully retrieved API key: {key[:5]}...") # Log first 5 chars for privacy
    except GumroadAPIKeyError as e: # Catch specific error
        logger.error(f"API Key Error: {e}")
    except ValueError as e: # Catch other ValueErrors if any
        logger.error(f"General ValueError: {e}")
    # Test with a dummy key in .gumroad_key
    # Create a dummy .gumroad_key for testing if it doesn't exist
    # and GUMROAD_API_KEY is not set.
    api_key_env = os.environ.get('GUMROAD_API_KEY')
    if not api_key_env and not os.path.exists('.gumroad_key'):
        logger.info("Creating a dummy .gumroad_key for testing get_gumroad_api_key.")
        with open('.gumroad_key', 'w') as f:
            f.write('test_key_from_file_123')
        try:
            key = get_gumroad_api_key()
            logger.info(f"Successfully retrieved API key from dummy file: {key[:10]}...")
        except ValueError as e:
            logger.error(e)
        finally:
            os.remove('.gumroad_key') # Clean up dummy file
            logger.info("Cleaned up dummy .gumroad_key file.")
    elif not api_key_env and os.path.exists('.gumroad_key'):
        # If .gumroad_key exists and no env var, test with existing file
        try:
            key = get_gumroad_api_key()
            logger.info(f"Successfully retrieved API key from existing .gumroad_key file: {key[:10]}...")
        except ValueError as e:
            logger.error(e)
    elif api_key_env:
        # If env var is set, test with it
        try:
            key = get_gumroad_api_key()
            logger.info(f"Successfully retrieved API key from env var: {key[:10]}...")
        except ValueError as e:
            logger.error(e)


def create_product(name: str, price_in_cents: int, description: str, file_path: str, currency: str = 'USD'):
    """
    Creates a new product on Gumroad.

    Args:
        name: The name of the product.
        price_in_cents: The price of the product in cents (e.g., 500 for $5.00).
        description: A description of the product.
        file_path: Path to the product file. (Handling of actual file upload TBD)
        currency: The currency code (e.g., 'USD').

    Returns:
        The public URL of the created product.

    Raises:
        GumroadAPIKeyError: If the API key cannot be found.
        requests.exceptions.RequestException: For network or API request errors.
        ValueError: For issues like invalid JSON response or missing critical data in response.
    """
    api_key = get_gumroad_api_key() # Can raise GumroadAPIKeyError

    # The API documentation (GET /products) shows 'price' in cents (e.g., price: 100 for $1.00).
    # The prompt initially suggested converting to currency units (e.g., 5.00 for 500 cents),
    # but using cents directly seems more consistent with the API.

    payload = {
        'access_token': api_key,
        'name': name,
        'price': price_in_cents, # API expects price in cents
        'description': description,
        'currency': currency,
        # 'url': '', # Placeholder for external URL if not uploading a file directly.
                       # The API docs suggest 'url' is for the product content, e.g., a link to a file.
                       # If uploading a file, this might be handled differently or set by the API.
        # 'product_variant_categories': [], # Optional: for product variants
    }

    # Regarding file upload:
    # The Gumroad API docs for POST /v2/products are not explicit on file uploads.
    # It might be a multipart/form-data request, or a two-step process:
    # 1. Create product with details.
    # 2. Upload file to the created product.
    # For now, this function will focus on creating the product with metadata.
    # The `file_path` argument is present, but its content won't be directly uploaded yet.
    # If the API expects a link to the file, `file_path` could be a URL.
    # If `file_path` is a local path, we'd need to figure out the upload mechanism.
    # The prompt mentions `url_params[external_url]` but API docs show `url`.
    # Let's assume for now that if `file_path` is a URL, it should be passed in 'url'.
    # If `file_path` is a local file, actual file upload logic is needed here,
    # likely using `files` argument in `requests.post`.

    files_payload = None
    if os.path.exists(file_path): # Check if it's a local file path that exists
        # This is where multipart/form-data for file upload would be prepared.
        # For example: files_payload = {'file': (os.path.basename(file_path), open(file_path, 'rb'))}
        # However, the API endpoint /v2/products might not support direct file upload this way.
        # The API might require 'url' to be a link to the content, or a separate upload step.
        # For this iteration, we'll pass 'url' as the file_path if it looks like a URL,
        # or as a placeholder if it's a local file path (actual upload TBD).
        if file_path.startswith('http://') or file_path.startswith('https://'):
            payload['url'] = file_path
            logger.info(f"Using provided file_path as a URL: {file_path}")
        else:
            # This is a local file path. How to upload is the question.
            # For now, we are not uploading the file content directly in this call.
            # We could set 'url' to a placeholder or omit it.
            # Let's try setting a placeholder name for 'url' if it's a local file,
            # as Gumroad might require 'url' or it will auto-generate one.
            # Or, it might be better to create the product without 'url' and update it later with file.
            # The API examples for GET product has "url": "http://sahillavingia.com/pencil.psd"
            # This implies 'url' is the link to the content.
            # The task states "assume we need to upload the file".
            # If `requests` handles `files` by adding it to `multipart/form-data` along with `data`,
            # this might work.
            # The cURL examples use -d for data, not -F for forms. This suggests JSON/data payload.
            # Let's try with `files` argument for `requests` if file_path is local.
            files_payload = {'content': (os.path.basename(file_path), open(file_path, 'rb'))}
            logger.info(f"Preparing to upload local file: {file_path}")
            # If 'content' is the field name for the file part. This is a guess.
            # Gumroad documentation does not specify this for the /products endpoint.
            # It is more likely that 'url' should be set to a link, or file uploaded separately.
            # For the initial attempt, let's try with 'files' if local file.
            # If this fails, the next step would be to assume 'url' must be a link, or file upload is separate.
    else:
        # If file_path doesn't exist locally, assume it might be an intentional non-file product or error.
        logger.warning(f"File path '{file_path}' does not exist locally. Product will be created without a direct file link or upload.")
        payload['url'] = '' # Or some other default, or omit.

    api_url = "https://api.gumroad.com/v2/products"

    logger.info(f"Creating Gumroad product: {name} with price {price_in_cents} {currency}")
    logger.debug(f"Request payload (excluding file content): {json.dumps(payload, indent=2)}")

    try:
        if files_payload:
            # If attempting a file upload, send data and files
            response = requests.post(api_url, data=payload, files=files_payload)
        else:
            # Otherwise, send just data (which might include a URL to the content)
            response = requests.post(api_url, data=payload)

        response.raise_for_status()  # Raise HTTPError for bad responses (4XX or 5XX)

        response_data = response.json()

        if response_data.get("success"):
            product_url = response_data.get("product", {}).get("short_url")
            if product_url:
                logger.info(f"Product created successfully: {name} - {product_url}")
                return product_url
            else:
                # This case means success was true, but product or short_url was missing.
                logger.error(f"Gumroad API success true, but 'short_url' not in product data: {response_data}")
                raise ValueError("Product creation succeeded according to API, but 'short_url' was not found in the response.")
        else:
            # success is false or not present
            message = response_data.get("message", "Unknown error during product creation (success flag false or missing).")
            logger.error(f"Gumroad API indicated failure: {message} - Full response: {response_data}")
            # We raise HTTPError here to signal a failed API operation, even if HTTP status was 2xx.
            # This is consistent with how requests.raise_for_status() works for 4xx/5xx.
            # If response object is not available, we can't pass it.
            # Create a generic HTTPError or a custom one.
            # For now, let's ensure it's an HTTPError if possible, or re-raise if one was already created by raise_for_status.
            # If raise_for_status() didn't trigger (e.g. 200 OK but success:false), we make one.
            # This part is already inside a try-except for HTTPError, so if raise_for_status() made one, it's caught below.
            # If it's a 200 with success:false, we should raise a new one.
            custom_error = requests.exceptions.HTTPError(f"Gumroad API error (success:false): {message}", response=response)
            custom_error.response = response # Ensure response is attached
            raise custom_error

    except requests.exceptions.HTTPError as e:
        # This will catch errors from response.raise_for_status() and the custom one above for "success":false
        # Log detailed error, including response if available
        response_text = ""
        if e.response is not None:
            try:
                response_text = e.response.text
            except Exception:
                response_text = "Could not retrieve response text."
        logger.error(f"HTTP error creating product '{name}': {e}. Response: {response_text}")
        raise # Re-raise the original or custom HTTPError
    except requests.exceptions.Timeout as e: # More specific than RequestException
        logger.error(f"Timeout creating product '{name}': {e}")
        raise
    except requests.exceptions.ConnectionError as e: # More specific than RequestException
        logger.error(f"Connection error creating product '{name}': {e}")
        raise
    except requests.exceptions.RequestException as e: # Catch other request-related errors
        logger.error(f"Network or request error creating product '{name}': {e}")
        raise
    except json.JSONDecodeError as e:
        # response.text might not be defined if response itself is problematic
        response_text_for_json_error = response.text if 'response' in locals() and hasattr(response, 'text') else "N/A"
        logger.error(f"Failed to decode JSON response for product '{name}': {e}. Response text: {response_text_for_json_error}")
        raise ValueError(f"Invalid JSON response from Gumroad API: {response_text_for_json_error}") # Keep as ValueError or make custom
    except Exception as e: # Catch any other unexpected error during the process
        logger.error(f"Unexpected error creating product '{name}': {e}", exc_info=True)
        raise # Re-raise to signal failure
    finally:
        if files_payload:
            # Ensure the file is closed if it was opened
            for _, file_tuple in files_payload.items():
                if hasattr(file_tuple[1], 'close'):
                    file_tuple[1].close()

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    # Create a dummy .gumroad_key for testing if it doesn't exist and GUMROAD_API_KEY is not set.
    API_KEY_PRESENT = bool(os.environ.get('GUMROAD_API_KEY'))
    if not API_KEY_PRESENT and not os.path.exists('.gumroad_key'):
        logger.info("Creating a dummy .gumroad_key for testing main execution.")
        with open('.gumroad_key', 'w') as f:
            f.write('dummy_api_key_for_testing_12345') # Replace with a real key for actual testing

    try:
        # Test get_gumroad_api_key
        retrieved_key = get_gumroad_api_key() # This will now raise GumroadAPIKeyError if key is missing
        logger.info(f"get_gumroad_api_key() successful, key starts with: {retrieved_key[:5]}")

        # Test create_product
        # To fully test create_product, a valid API key with 'edit_products' scope is needed.
        # And a dummy file.
        dummy_file_path = "dummy_product_file.txt"
        with open(dummy_file_path, "w") as f:
            f.write("This is a dummy file for a Gumroad product.")

        logger.info(f"Attempting to create a product. THIS WILL LIKELY FAIL WITHOUT A VALID API KEY.")
        logger.info("If .gumroad_key contains 'dummy_api_key_for_testing_12345', expect a 401 Unauthorized.")

        try:
            product_url = create_product(
                name="Test Product from Script",
                price_in_cents=199, # $1.99
                description="This is a test product created via the API.",
                file_path=dummy_file_path, # Local file path
                currency="USD"
            )
            logger.info(f"Dummy product created successfully! URL: {product_url}")
        except GumroadAPIKeyError as apike: # Specific error for API key
            logger.error(f"Gumroad API Key Error: {apike}")
        except ValueError as ve: # For JSON errors or missing short_url
            logger.error(f"ValueError during product creation: {ve}")
        except requests.exceptions.HTTPError as he:
            if he.response is not None:
                logger.error(f"HTTPError during product creation: Status {he.response.status_code} - {he.response.text}")
            else:
                logger.error(f"HTTPError during product creation: {he}")
        except requests.exceptions.RequestException as re: # For other network errors like ConnectionError, Timeout
            logger.error(f"RequestException during product creation: {re}")
        except Exception as e: # Catch-all for other unexpected errors
            logger.error(f"Unexpected error during product creation test: {e}", exc_info=True)
        finally:
            if os.path.exists(dummy_file_path):
                os.remove(dummy_file_path)
                logger.info(f"Cleaned up dummy file: {dummy_file_path}")

    except GumroadAPIKeyError as e: # Catch API key error for get_gumroad_api_key() test
        logger.error(f"Main execution API Key Error: {e}")
    except ValueError as e: # Catch other ValueErrors
        logger.error(f"Main execution ValueError: {e}")
    except Exception as e: # Catch-all for other unexpected errors in main
        logger.error(f"Main execution unexpected error: {e}", exc_info=True)
    finally:
        # Clean up dummy .gumroad_key if it was created by this test script
        if not API_KEY_PRESENT and os.path.exists('.gumroad_key'):
            with open('.gumroad_key', 'r') as f:
                content = f.read().strip()
            if content == 'dummy_api_key_for_testing_12345':
                os.remove('.gumroad_key')
                logger.info("Cleaned up dummy .gumroad_key created by main execution.")
            elif 'test_key_from_file_123' in content: # from previous test block
                 os.remove('.gumroad_key')
                 logger.info("Cleaned up dummy .gumroad_key (from get_api_key test block).")
