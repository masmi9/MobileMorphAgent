"""
MobileMorph Agent Integration for dyna.py

This module provides a Drozer-compatible interface for dyna.py to use
the MobileMorph Agent for dynamic Android analysis.

Usage in dyna.py:
    from core.mobilemorph_integration import MobileMorphAgent

    agent = MobileMorphAgent()
    if agent.connect():
        manifest = agent.get_manifest("com.example.app")
        attack_surface = agent.get_attack_surface("com.example.app")
        agent.disconnect()
"""

import sys
import os

# Add parent directory to path to import agent_client
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agent_client import AgentClient

class MobileMorphAgent:
    """
    Drozer-compatible wrapper for MobileMorph Agent

    This class provides the same interface that dyna.py expects from Drozer,
    but uses the MobileMorph Agent backend instead.
    """

    def __init__(self, host='localhost', port=31415, auto_forward=True):
        """
        Initialize MobileMorph Agent client

        Args:
            host: Agent host (default: localhost)
            port: Agent port (default: 31415)
            auto_forward: Automatically setup ADB port forwarding (default: True)
        """
        self.client = AgentClient(host=host, port=port)
        self.auto_forward = auto_forward
        self.connected = False

    def connect(self) -> bool:
        """
        Connect to the MobileMorph Agent

        Returns:
            True if connection successful, False otherwise
        """
        try:
            # Setup ADB forwarding if requested
            if self.auto_forward:
                if not self.client.setup_adb_forward():
                    print("[!] Failed to setup ADB port forwarding")
                    return False

            # Connect to agent
            if self.client.connect():
                self.connected = True
                return True

            return False

        except Exception as e:
            print(f"[!] Connection error: {e}")
            return False

    def disconnect(self):
        """Disconnect from agent"""
        if self.connected:
            self.client.disconnect()
            self.connected = False

    def get_manifest(self, package: str) -> dict:
        """
        Get AndroidManifest analysis for package

        Args:
            package: Package name to analyze

        Returns:
            Dictionary with manifest analysis results
        """
        if not self.connected:
            raise ConnectionError("Not connected to agent")

        response = self.client.manifest_analysis(package)
        if response and response.get("status") == "success":
            return response.get("data", {})
        else:
            error = response.get("error", "Unknown error") if response else "No response"
            raise Exception(f"Manifest analysis failed: {error}")

    def get_attack_surface(self, package: str) -> dict:
        """
        Get IPC attack surface for package

        Args:
            package: Package name to analyze

        Returns:
            Dictionary with attack surface analysis
        """
        if not self.connected:
            raise ConnectionError("Not connected to agent")

        response = self.client.exploit_ipc(package, "attack_surface")
        if response and response.get("status") == "success":
            return response.get("data", {})
        else:
            error = response.get("error", "Unknown error") if response else "No response"
            raise Exception(f"Attack surface analysis failed: {error}")

    def get_packages(self, filter_pkg=None, exported_only=True) -> list:
        """
        Enumerate installed packages

        Args:
            filter_pkg: Filter by package name substring
            exported_only: Only show packages with exported components

        Returns:
            List of packages with exported components
        """
        if not self.connected:
            raise ConnectionError("Not connected to agent")

        response = self.client.package_enum(
            include_system=False,
            exported_only=exported_only,
            filter_pkg=filter_pkg
        )

        if response and response.get("status") == "success":
            data = response.get("data", {})
            return data.get("packages", [])
        else:
            error = response.get("error", "Unknown error") if response else "No response"
            raise Exception(f"Package enumeration failed: {error}")

    def get_permissions(self, package: str) -> dict:
        """
        Get permission audit for package

        Args:
            package: Package name to audit

        Returns:
            Dictionary with permission audit results
        """
        if not self.connected:
            raise ConnectionError("Not connected to agent")

        response = self.client.permission_audit(package=package)
        if response and response.get("status") == "success":
            return response.get("data", {})
        else:
            error = response.get("error", "Unknown error") if response else "No response"
            raise Exception(f"Permission audit failed: {error}")

    def test_content_provider(self, authority: str, operation="query", path="") -> dict:
        """
        Test Content Provider vulnerabilities

        Args:
            authority: Content provider authority
            operation: Operation to perform (query, test_traversal, test_sqli)
            path: URI path

        Returns:
            Dictionary with test results
        """
        if not self.connected:
            raise ConnectionError("Not connected to agent")

        response = self.client.exploit_provider(
            authority=authority,
            operation=operation,
            path=path
        )

        if response and response.get("status") == "success":
            return response.get("data", {})
        else:
            error = response.get("error", "Unknown error") if response else "No response"
            raise Exception(f"Content provider test failed: {error}")

    def send_intent(self, package: str, component: str, intent_type="activity",
                   action=None, extras=None) -> dict:
        """
        Send crafted intent to component

        Args:
            package: Target package
            component: Target component
            intent_type: Type (activity, service, broadcast)
            action: Intent action
            extras: Intent extras dictionary

        Returns:
            Dictionary with exploit results
        """
        if not self.connected:
            raise ConnectionError("Not connected to agent")

        response = self.client.exploit_intent(
            package=package,
            component=component,
            intent_type=intent_type,
            action=action,
            extras=extras
        )

        if response and response.get("status") == "success":
            return response.get("data", {})
        else:
            error = response.get("error", "Unknown error") if response else "No response"
            raise Exception(f"Intent exploit failed: {error}")

    def execute_shell(self, command: str) -> str:
        """
        Execute shell command on device

        Args:
            command: Shell command to execute

        Returns:
            Command output as string
        """
        if not self.connected:
            raise ConnectionError("Not connected to agent")

        response = self.client.shell(command)
        if response and response.get("status") == "success":
            data = response.get("data", {})
            return data.get("output", "")
        else:
            error = response.get("error", "Unknown error") if response else "No response"
            raise Exception(f"Shell command failed: {error}")

    def run_full_scan(self, package: str) -> dict:
        """
        Run comprehensive security scan on package

        This performs all available tests and returns consolidated results.
        Designed for integration with dyna.py automated scanning.

        Args:
            package: Package name to scan

        Returns:
            Dictionary with comprehensive scan results
        """
        if not self.connected:
            raise ConnectionError("Not connected to agent")

        results = {
            "package": package,
            "manifest": None,
            "attack_surface": None,
            "permissions": None,
            "exported_components": [],
            "vulnerabilities": []
        }

        try:
            # 1. Manifest analysis
            print(f"[*] Analyzing manifest for {package}...")
            results["manifest"] = self.get_manifest(package)

            # 2. Attack surface analysis
            print(f"[*] Analyzing attack surface for {package}...")
            results["attack_surface"] = self.get_attack_surface(package)

            # 3. Permission audit
            print(f"[*] Auditing permissions for {package}...")
            results["permissions"] = self.get_permissions(package)

            # 4. Extract exported components for testing
            attack_surface = results["attack_surface"]
            if attack_surface and "vulnerable_components" in attack_surface:
                results["exported_components"] = attack_surface["vulnerable_components"]

            # 5. Test content providers if found
            manifest = results["manifest"]
            if manifest and "providers" in manifest:
                for provider in manifest["providers"]:
                    if provider.get("exported"):
                        authority = provider.get("authority")
                        if authority:
                            print(f"[*] Testing Content Provider: {authority}...")
                            try:
                                # Test path traversal
                                traversal_result = self.test_content_provider(
                                    authority,
                                    operation="test_traversal"
                                )
                                if traversal_result.get("vulnerable"):
                                    results["vulnerabilities"].append({
                                        "type": "Content Provider Path Traversal",
                                        "component": authority,
                                        "severity": "HIGH",
                                        "details": traversal_result
                                    })

                                # Test SQL injection
                                sqli_result = self.test_content_provider(
                                    authority,
                                    operation="test_sqli",
                                    path=""
                                )
                                if sqli_result.get("vulnerable"):
                                    results["vulnerabilities"].append({
                                        "type": "Content Provider SQL Injection",
                                        "component": authority,
                                        "severity": "CRITICAL",
                                        "details": sqli_result
                                    })
                            except Exception as e:
                                print(f"[!] Error testing provider {authority}: {e}")

            print(f"[+] Scan completed for {package}")
            return results

        except Exception as e:
            print(f"[!] Error during scan: {e}")
            results["error"] = str(e)
            return results


# Example usage for testing
if __name__ == "__main__":
    import json

    print("MobileMorph Agent Integration Test")
    print("="*60)

    agent = MobileMorphAgent()

    if agent.connect():
        print("[+] Connected to agent\n")

        # Test package enumeration
        print("[*] Enumerating packages with exported components...")
        packages = agent.get_packages(exported_only=True)
        print(f"[+] Found {len(packages)} packages with exported components\n")

        # Test on first package
        if packages:
            test_pkg = packages[0]["package"]
            print(f"[*] Running full scan on {test_pkg}...")
            results = agent.run_full_scan(test_pkg)

            print("\nScan Results:")
            print(json.dumps(results, indent=2))

        agent.disconnect()
        print("\n[+] Disconnected from agent")
    else:
        print("[!] Failed to connect to agent")
        sys.exit(1)
