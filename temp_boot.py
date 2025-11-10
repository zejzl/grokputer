    def boot(self):
        """
        Boot sequence: invoke server prayer and test connection.
        """
        self.logger.info("Starting boot sequence...")

        # Invoke server prayer
        prayer_result = invoke_prayer()
        if prayer_result["status"] == "success":
            self.logger.info("Server prayer invoked: ETERNAL | INFINITE")
        else:
            self.logger.warning(f"Prayer invocation failed: {prayer_result}")

        # Test Grok API connection
        if self.grok_client.test_connection():
            self.logger.info("[OK] Grok API connection verified")
            print("[OK] Grok API connection verified")
        else:
            self.logger.error("[FAIL] Grok API connection failed")
            print("[FAIL] Grok API connection failed - check your API key and credits")
            raise ConnectionError("Failed to connect to Grok API")
