import unittest
from ui_utils import validate_proxy, validate_rate_limit, validate_url


class TestUIUtilsExtended(unittest.TestCase):
    def test_validate_proxy(self):
        # Valid
        self.assertTrue(validate_proxy("http://user:pass@127.0.0.1:8080"))
        self.assertTrue(validate_proxy("socks5://192.168.1.1:1080"))
        self.assertTrue(validate_proxy("https://myproxy.com:3128"))
        self.assertTrue(validate_proxy(""))  # Empty is valid (no proxy)
        self.assertTrue(validate_proxy(None))  # None is valid

        # Invalid
        self.assertFalse(validate_proxy("ftp://127.0.0.1:21"))  # Wrong scheme
        self.assertFalse(validate_proxy("http://127.0.0.1"))  # No port
        self.assertFalse(validate_proxy("justastring"))
        self.assertFalse(validate_proxy("http://:8080"))  # No host
        self.assertFalse(validate_proxy("http://127.0.0.1:99999"))  # Bad port

    def test_validate_rate_limit(self):
        # Valid
        self.assertTrue(validate_rate_limit("50K"))
        self.assertTrue(validate_rate_limit("1.5M"))
        self.assertTrue(validate_rate_limit("1000"))
        self.assertTrue(validate_rate_limit("500"))
        self.assertTrue(validate_rate_limit(""))
        self.assertTrue(validate_rate_limit(None))

        # Invalid
        self.assertFalse(validate_rate_limit("0"))
        self.assertFalse(validate_rate_limit("abc"))
        self.assertFalse(validate_rate_limit("-50"))
        self.assertFalse(
            validate_rate_limit("50.5")
        )  # Decimals need unit in our regex logic currently?
        # Let's check regex: ^[1-9]\d*(\.\d+)?[KMGT](?:/s)?$ OR ^[1-9]\d*(?:/s)?$
        # So "50.5" without unit fails the second regex (no dot allowed) and fails first (no unit). Correct.

    def test_validate_url(self):
        self.assertTrue(validate_url("https://youtube.com/watch?v=123"))
        self.assertTrue(validate_url("http://localhost:8080"))
        self.assertFalse(validate_url("ftp://example.com"))
        self.assertFalse(validate_url("javascript:alert(1)"))
        self.assertFalse(validate_url("http://"))


if __name__ == "__main__":
    unittest.main()
