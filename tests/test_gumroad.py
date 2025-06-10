import pytest
import os
import json
from unittest.mock import patch, mock_open, MagicMock

# Assuming gumroad.py is in the parent directory relative to the tests directory
# Adjust the import path if your structure is different.
# For a typical structure where tests/ is a subdirectory of the project root:
from gumroad import get_gumroad_api_key, create_product
import requests # For requests.exceptions

# Helper to create a MockResponse object for requests.post
def mock_response(status_code, json_data=None, text_data=None, raise_for_status_error=None):
    mock_resp = MagicMock()
    mock_resp.status_code = status_code
    if json_data:
        mock_resp.json = MagicMock(return_value=json_data)
    # If text_data is provided, or if json_data is None (to simulate non-json response)
    mock_resp.text = text_data if text_data is not None else json.dumps(json_data) if json_data else ""

    if raise_for_status_error:
        mock_resp.raise_for_status = MagicMock(side_effect=raise_for_status_error)
    else:
        # Default behavior for raise_for_status
        def rfs():
            if status_code >= 400:
                raise requests.exceptions.HTTPError(f"Mock HTTP Error {status_code}", response=mock_resp)
        mock_resp.raise_for_status = MagicMock(side_effect=rfs if status_code >=400 else None)

    return mock_resp

class TestGetGumroadApiKey:
    @patch.dict(os.environ, {"GUMROAD_API_KEY": "env_api_key"}, clear=True)
    def test_get_from_env_variable(self):
        assert get_gumroad_api_key() == "env_api_key"

    @patch.dict(os.environ, {}, clear=True)
    @patch("builtins.open", new_callable=mock_open, read_data="file_api_key")
    @patch("os.path.exists") # Mock os.path.exists if gumroad.py uses it before open
    def test_get_from_file(self, mock_exists, mock_file_open):
        # If gumroad.py uses os.path.exists before trying to open .gumroad_key
        mock_exists.return_value = True
        # Or, more commonly, it just tries to open and catches FileNotFoundError
        # If it uses `Path.exists()`, then patch `pathlib.Path.exists`
        assert get_gumroad_api_key() == "file_api_key"
        mock_file_open.assert_called_once_with(".gumroad_key", "r")

    @patch.dict(os.environ, {}, clear=True)
    @patch("builtins.open", side_effect=FileNotFoundError)
    def test_not_found_raises_value_error(self, mock_file_open):
        with pytest.raises(ValueError, match="Gumroad API key not found"):
            get_gumroad_api_key()

    @patch.dict(os.environ, {"GUMROAD_API_KEY": "env_key_takes_precedence"}, clear=True)
    @patch("builtins.open", new_callable=mock_open, read_data="file_api_key")
    def test_env_takes_precedence_over_file(self, mock_file):
        assert get_gumroad_api_key() == "env_key_takes_precedence"
        mock_file.assert_not_called()

    @patch.dict(os.environ, {}, clear=True)
    @patch("builtins.open", new_callable=mock_open, read_data="  stripped_key  ")
    @patch("os.path.exists", return_value=True)
    def test_key_from_file_is_stripped(self, mock_exists, mock_file):
        assert get_gumroad_api_key() == "stripped_key"


class TestCreateProduct:
    DUMMY_API_KEY = "test_api_key"
    PRODUCT_NAME = "Test Product"
    PRODUCT_PRICE = 1000
    PRODUCT_DESC = "A great test product."
    PRODUCT_CURRENCY = "USD"

    @pytest.fixture(autouse=True)
    def patch_get_api_key(self):
        with patch("gumroad.get_gumroad_api_key", return_value=self.DUMMY_API_KEY) as _mock:
            yield _mock

    @pytest.fixture
    def dummy_local_file(self, tmp_path):
        file_content = "This is a dummy file."
        p = tmp_path / "dummy_product.txt"
        p.write_text(file_content)
        return str(p)

    @patch("gumroad.requests.post")
    def test_create_product_local_file_success(self, mock_post, dummy_local_file):
        expected_url = "https://gum.co/prod123"
        mock_post.return_value = mock_response(
            201, {"success": True, "product": {"id": "prod_123", "short_url": expected_url}}
        )

        result_url = create_product(
            name=self.PRODUCT_NAME,
            price_in_cents=self.PRODUCT_PRICE,
            description=self.PRODUCT_DESC,
            file_path=dummy_local_file,
            currency=self.PRODUCT_CURRENCY
        )

        assert result_url == expected_url
        args, kwargs = mock_post.call_args
        assert args[0] == "https://api.gumroad.com/v2/products"
        assert kwargs["data"]["access_token"] == self.DUMMY_API_KEY
        assert kwargs["data"]["name"] == self.PRODUCT_NAME
        assert "files" in kwargs
        assert "content" in kwargs["files"] # Based on current gumroad.py implementation

    @patch("gumroad.requests.post")
    def test_create_product_url_success(self, mock_post):
        file_url = "http://example.com/product.pdf"
        expected_gumroad_url = "https://gum.co/prod456"
        mock_post.return_value = mock_response(
            201, {"success": True, "product": {"id": "prod_456", "short_url": expected_gumroad_url}}
        )

        result_url = create_product(
            name=self.PRODUCT_NAME,
            price_in_cents=self.PRODUCT_PRICE,
            description=self.PRODUCT_DESC,
            file_path=file_url, # This is a URL
            currency=self.PRODUCT_CURRENCY
        )
        assert result_url == expected_gumroad_url
        args, kwargs = mock_post.call_args
        assert kwargs["data"]["url"] == file_url
        assert "files" not in kwargs or kwargs["files"] is None


    @patch("gumroad.requests.post")
    def test_create_product_api_error_401(self, mock_post):
        mock_post.return_value = mock_response(
            401, {"success": False, "message": "Invalid access token"}
        )
        with pytest.raises(requests.exceptions.HTTPError, match="Mock HTTP Error 401"):
             create_product(
                name=self.PRODUCT_NAME,
                price_in_cents=self.PRODUCT_PRICE,
                description=self.PRODUCT_DESC,
                file_path="dummy.txt" # File existence check is part of the function, provide a name
            )

    @patch("gumroad.requests.post")
    def test_create_product_api_error_gumroad_false_success(self, mock_post):
        # Gumroad might return 200 OK but with "success": false
        mock_post.return_value = mock_response(
            200, {"success": False, "message": "Product validation failed"}
        )
        # This should raise an HTTPError because create_product itself raises it for success:false
        with pytest.raises(requests.exceptions.HTTPError, match="Gumroad API error: Product validation failed"):
            create_product(
                name=self.PRODUCT_NAME,
                price_in_cents=self.PRODUCT_PRICE,
                description=self.PRODUCT_DESC,
                file_path="dummy.txt"
            )

    @patch("gumroad.requests.post", side_effect=requests.exceptions.ConnectionError("Network issue"))
    def test_create_product_network_error(self, mock_post):
        with pytest.raises(requests.exceptions.ConnectionError, match="Network issue"):
            create_product(
                name=self.PRODUCT_NAME,
                price_in_cents=self.PRODUCT_PRICE,
                description=self.PRODUCT_DESC,
                file_path="dummy.txt"
            )

    @patch("gumroad.requests.post")
    def test_create_product_invalid_json_response(self, mock_post):
        mock_post.return_value = mock_response(200, text_data="<not_json>")
        with pytest.raises(ValueError, match="Invalid JSON response from Gumroad API"):
            create_product(
                name=self.PRODUCT_NAME,
                price_in_cents=self.PRODUCT_PRICE,
                description=self.PRODUCT_DESC,
                file_path="dummy.txt"
            )

    @patch("gumroad.requests.post")
    def test_create_product_missing_short_url_in_response(self, mock_post):
        mock_post.return_value = mock_response(
            201, {"success": True, "product": {"id": "prod_789"}} # Missing short_url
        )
        with pytest.raises(ValueError, match="Product created, but 'short_url' not found in API response"):
            create_product(
                name=self.PRODUCT_NAME,
                price_in_cents=self.PRODUCT_PRICE,
                description=self.PRODUCT_DESC,
                file_path="dummy.txt"
            )

    @patch("os.path.exists", return_value=False) # Ensure file_path for local file does not exist
    @patch("gumroad.requests.post")
    def test_create_product_local_file_not_exists_handled(self, mock_post, mock_os_exists):
        # This test assumes that if file_path is local and doesn't exist,
        # it should pass an empty 'url' or similar to gumroad, not 'files'
        # The current gumroad.py has a logger.warning and sets payload['url'] = ''
        expected_gumroad_url = "https://gum.co/prod_no_file"
        mock_post.return_value = mock_response(
            201, {"success": True, "product": {"id": "prod_no_file_id", "short_url": expected_gumroad_url}}
        )

        result_url = create_product(
            name=self.PRODUCT_NAME,
            price_in_cents=self.PRODUCT_PRICE,
            description=self.PRODUCT_DESC,
            file_path="non_existent_local_file.txt",
            currency=self.PRODUCT_CURRENCY
        )

        assert result_url == expected_gumroad_url
        args, kwargs = mock_post.call_args
        assert kwargs['data']['url'] == '' # As per current gumroad.py logic
        assert 'files' not in kwargs or kwargs.get('files') is None


    @patch("gumroad.requests.post")
    def test_create_product_file_handle_closed_after_upload(self, mock_post, dummy_local_file):
        expected_url = "https://gum.co/prod_file_closed"
        mock_post.return_value = mock_response(
            201, {"success": True, "product": {"id": "file_closed_id", "short_url": expected_url}}
        )

        # To check if the file handle is closed, we need to spy on the `open` call
        # and then check the `closed` attribute of the file object.
        # The `files_payload` dictionary in `create_product` holds the file object.
        # This is a bit tricky to test without refactoring `create_product` for better testability
        # or more complex mocking.
        # However, the `finally` block in `create_product` should ensure it.
        # We can mock `open` to return a MagicMock that we can inspect.

        mock_file_object = MagicMock()
        mock_file_object.name = os.path.basename(dummy_local_file)
        mock_file_object.closed = False # Simulate it's open initially

        # We want to ensure it's closed by the `finally` block in `create_product`
        def custom_close():
            mock_file_object.closed = True
        mock_file_object.close = MagicMock(side_effect=custom_close)

        # Patch `open` specifically for the file path being used
        with patch("builtins.open", mock_open(mock=mock_file_object)) as mocked_open_call:
            # This is not quite right. We need `open` to return our mock_file_object
            # when called with dummy_local_file.
            # Let's refine this:
            pass # This test needs a better way to inject the mock file object or check it.

        # Alternative: Trust the `finally` block for now, or refactor create_product
        # For now, let's assume the `finally` block works as intended.
        # A more direct test would involve inspecting the `files` dict passed to `requests.post`
        # and then ensuring its file handle's `close()` method was called.

        # Simpler check for now: ensure the function runs without error and the file is used.
        create_product(
            name=self.PRODUCT_NAME,
            price_in_cents=self.PRODUCT_PRICE,
            description=self.PRODUCT_DESC,
            file_path=dummy_local_file,
            currency=self.PRODUCT_CURRENCY
        )
        # This doesn't directly test file.close() but ensures the path with file handling is taken.
        # A full test for file.close() would require more intricate mocking of the file object lifecycle.
        # The current structure of `create_product` makes this hard to test without
        # also mocking `os.path.basename` and how `files_payload` is constructed.

        # For the sake of moving forward, we'll assume the `finally` block is correct.
        # A more robust test would be:
        # 1. Patch `open` to return a MagicMock file object.
        # 2. Call `create_product`.
        # 3. Assert `mock_file_object.close.assert_called_once()`.

        # Let's try that specific mock for `open`
        m = mock_open()
        with patch('builtins.open', m):
            create_product(
                name="Test File Close",
                price_in_cents=100,
                description="Testing file closure",
                file_path=dummy_local_file # This needs to be seen as a local file
            )
            # Check if open was called with the dummy_local_file
            m.assert_called_with(dummy_local_file, 'rb')
            # Check if the returned handle (from the first call to open) had close called
            # This assumes `open` is only called once for the file content.
            handle = m.return_value
            handle.close.assert_called_once()

# To run these tests:
# Ensure pytest and requests are installed.
# Navigate to the directory containing `gumroad.py` and `tests/`.
# Run `PYTHONPATH=. pytest tests/test_gumroad.py`
# (PYTHONPATH ensures `from gumroad import ...` works)
