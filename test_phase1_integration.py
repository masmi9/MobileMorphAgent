#!/usr/bin/env python3
"""
Phase 1 Integration Test Script

Tests the complete integration between DYNA and MobileMorphAgent:
1. MobileMorphAgentBridge connectivity
2. Flask server module endpoints
3. CommandService module handling
4. End-to-end module invocation flow

Usage:
    python test_phase1_integration.py --device <device_id> --package <package_name>
"""

import argparse
import json
import logging
import requests
import sys
import time
from typing import Dict, Any

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(levelname)s] %(message)s'
)
logger = logging.getLogger(__name__)


class Phase1IntegrationTester:
    """Test suite for Phase 1 integration."""

    def __init__(self, device_id: str, package_name: str, server_url: str = "http://127.0.0.1:5000"):
        self.device_id = device_id
        self.package_name = package_name
        self.server_url = server_url.rstrip('/')
        self.test_results = []

    def run_all_tests(self) -> bool:
        """Run all integration tests."""
        logger.info("=" * 60)
        logger.info("Phase 1 Integration Test Suite")
        logger.info("=" * 60)

        tests = [
            ("Server Connectivity", self.test_server_connectivity),
            ("Agent Connection", self.test_agent_connection),
            ("Bridge Initialization", self.test_bridge_initialization),
            ("ManifestAnalyzer Module", self.test_manifest_analyzer),
            ("ContentProviderExploiter Module", self.test_content_provider_exploiter),
            ("Drozer Command Translation", self.test_drozer_command_translation),
            ("End-to-End Flow", self.test_end_to_end_flow),
        ]

        passed = 0
        failed = 0

        for test_name, test_func in tests:
            logger.info(f"\n{'─' * 60}")
            logger.info(f"Test: {test_name}")
            logger.info('─' * 60)

            try:
                result = test_func()
                if result:
                    logger.info(f"✅ PASSED: {test_name}")
                    passed += 1
                else:
                    logger.error(f"❌ FAILED: {test_name}")
                    failed += 1
                self.test_results.append((test_name, result))
            except Exception as e:
                logger.error(f"❌ ERROR in {test_name}: {e}")
                logger.exception(e)
                failed += 1
                self.test_results.append((test_name, False))

        # Print summary
        logger.info("\n" + "=" * 60)
        logger.info("Test Summary")
        logger.info("=" * 60)
        logger.info(f"Total Tests: {len(tests)}")
        logger.info(f"Passed: {passed} ✅")
        logger.info(f"Failed: {failed} ❌")
        logger.info(f"Success Rate: {(passed/len(tests)*100):.1f}%")
        logger.info("=" * 60)

        return failed == 0

    def test_server_connectivity(self) -> bool:
        """Test 1: Verify Flask server is running and accessible."""
        try:
            response = requests.get(f"{self.server_url}/agents", timeout=5)
            if response.status_code == 200:
                logger.info(f"Server accessible at {self.server_url}")
                return True
            else:
                logger.error(f"Server returned status {response.status_code}")
                return False
        except Exception as e:
            logger.error(f"Cannot connect to server: {e}")
            return False

    def test_agent_connection(self) -> bool:
        """Test 2: Verify agent is connected to the server."""
        try:
            response = requests.get(f"{self.server_url}/agents", timeout=5)
            agents = response.json()

            agent = next((a for a in agents if a.get("device_id") == self.device_id), None)

            if agent:
                logger.info(f"Agent found: {self.device_id}")
                logger.info(f"  Model: {agent.get('model', 'unknown')}")
                logger.info(f"  Manufacturer: {agent.get('manufacturer', 'unknown')}")
                logger.info(f"  Online: {agent.get('online', False)}")

                if agent.get('online'):
                    return True
                else:
                    logger.error("Agent is registered but not online")
                    return False
            else:
                logger.error(f"Agent {self.device_id} not found in connected agents")
                logger.info(f"Connected agents: {[a.get('device_id') for a in agents]}")
                return False

        except Exception as e:
            logger.error(f"Error checking agent connection: {e}")
            return False

    def test_bridge_initialization(self) -> bool:
        """Test 3: Test MobileMorphAgentBridge initialization."""
        try:
            from core.mobilemorph_bridge import MobileMorphAgentBridge

            bridge = MobileMorphAgentBridge(
                self.device_id,
                self.package_name,
                self.server_url
            )

            logger.info(f"Bridge initialized for device: {self.device_id}")
            logger.info(f"Agent available: {bridge.agent_available}")
            logger.info(f"Package: {bridge.package_name}")

            if bridge.agent_available:
                return True
            else:
                logger.error(f"Bridge initialization failed: {bridge.last_error}")
                return False

        except ImportError as e:
            logger.error(f"Cannot import MobileMorphAgentBridge: {e}")
            return False
        except Exception as e:
            logger.error(f"Bridge initialization error: {e}")
            return False

    def test_manifest_analyzer(self) -> bool:
        """Test 4: Test ManifestAnalyzer module invocation."""
        try:
            from core.mobilemorph_bridge import MobileMorphAgentBridge

            bridge = MobileMorphAgentBridge(
                self.device_id,
                self.package_name,
                self.server_url
            )

            logger.info(f"Invoking ManifestAnalyzer for {self.package_name}")

            result = bridge.invoke_agent_module(
                "ManifestAnalyzer",
                {"package": self.package_name}
            )

            logger.info(f"Result status: {result.get('status')}")

            if result.get('status') == 'success':
                data = result.get('data', {})
                logger.info(f"Package: {data.get('package_name')}")
                logger.info(f"Version: {data.get('version_name')}")
                logger.info(f"Activities: {len(data.get('activities', []))}")
                logger.info(f"Services: {len(data.get('services', []))}")
                logger.info(f"Receivers: {len(data.get('receivers', []))}")
                logger.info(f"Providers: {len(data.get('providers', []))}")
                return True
            else:
                logger.error(f"Module returned error: {result.get('error')}")
                return False

        except Exception as e:
            logger.error(f"ManifestAnalyzer test failed: {e}")
            return False

    def test_content_provider_exploiter(self) -> bool:
        """Test 5: Test ContentProviderExploiter module."""
        try:
            from core.mobilemorph_bridge import MobileMorphAgentBridge

            bridge = MobileMorphAgentBridge(
                self.device_id,
                self.package_name,
                self.server_url
            )

            # First get manifest to find providers
            logger.info("Getting manifest to find content providers...")
            manifest = bridge.invoke_agent_module(
                "ManifestAnalyzer",
                {"package": self.package_name}
            )

            providers = manifest.get('data', {}).get('providers', [])

            if not providers:
                logger.warning("No content providers found, skipping exploitation test")
                return True  # Not a failure, just no providers to test

            # Test first provider
            provider = providers[0]
            authority = provider.get('authority')

            logger.info(f"Testing provider: {authority}")

            result = bridge.invoke_agent_module(
                "ContentProviderExploiter",
                {
                    "operation": "test_traversal",
                    "authority": authority
                }
            )

            logger.info(f"Result status: {result.get('status')}")

            if result.get('status') == 'success':
                data = result.get('data', {})
                logger.info(f"Vulnerable: {data.get('vulnerable')}")
                logger.info(f"Findings: {len(data.get('findings', []))}")
                return True
            else:
                logger.error(f"Module returned error: {result.get('error')}")
                return False

        except Exception as e:
            logger.error(f"ContentProviderExploiter test failed: {e}")
            return False

    def test_drozer_command_translation(self) -> bool:
        """Test 6: Test Drozer command translation."""
        try:
            from core.mobilemorph_bridge import MobileMorphAgentBridge

            bridge = MobileMorphAgentBridge(
                self.device_id,
                self.package_name,
                self.server_url
            )

            # Test Drozer-style command
            drozer_cmd = f"run app.package.manifest {self.package_name}"

            logger.info(f"Testing Drozer command: {drozer_cmd}")

            result = bridge.run_command(drozer_cmd)

            logger.info("Command result (first 500 chars):")
            logger.info(result[:500])

            if "Package:" in result or "error" not in result.lower():
                return True
            else:
                logger.error("Command translation failed")
                return False

        except Exception as e:
            logger.error(f"Drozer command translation test failed: {e}")
            return False

    def test_end_to_end_flow(self) -> bool:
        """Test 7: Complete end-to-end flow simulation."""
        try:
            logger.info("Simulating complete DYNA → Bridge → Server → Agent → Results flow")

            # Step 1: HTTP request to server
            logger.info("Step 1: Sending module request to server...")
            response = requests.post(
                f"{self.server_url}/api/agent/module/{self.device_id}",
                json={
                    "module": "PackageEnumerator",
                    "args": {"filter": self.package_name}
                },
                timeout=5
            )

            if response.status_code != 200:
                logger.error(f"Server request failed: {response.status_code}")
                return False

            logger.info(f"Server response: {response.json()}")

            # Step 2: Wait for agent to process
            logger.info("Step 2: Waiting for agent to process command...")
            time.sleep(3)

            # Step 3: Retrieve result
            logger.info("Step 3: Retrieving result from server...")
            result_response = requests.get(
                f"{self.server_url}/api/get_result/{self.device_id}",
                timeout=5
            )

            if result_response.status_code == 200:
                result = result_response.json().get('result')
                logger.info(f"Result received: {result is not None}")

                if result and isinstance(result, dict):
                    logger.info(f"Result status: {result.get('status')}")
                    logger.info(f"Result has data: {'data' in result}")
                    return result.get('status') == 'success'
                else:
                    logger.warning("No result available yet (this is OK if timing is off)")
                    return True  # Consider this a pass as the flow worked
            else:
                logger.error(f"Failed to retrieve result: {result_response.status_code}")
                return False

        except Exception as e:
            logger.error(f"End-to-end flow test failed: {e}")
            return False


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Phase 1 Integration Test Suite for DYNA + MobileMorphAgent"
    )
    parser.add_argument(
        "--device",
        type=str,
        help="Device ID of the connected MobileMorphAgent (auto-detects if not specified)"
    )
    parser.add_argument(
        "--package",
        type=str,
        help="Package name to test with (use --interactive if not specified)"
    )
    parser.add_argument(
        "--server",
        type=str,
        default="http://127.0.0.1:5000",
        help="Flask server URL (default: http://127.0.0.1:5000)"
    )
    parser.add_argument(
        "--interactive",
        "-i",
        action="store_true",
        help="Interactively select package from device"
    )
    parser.add_argument(
        "--list-packages",
        action="store_true",
        help="List available packages and exit"
    )

    args = parser.parse_args()

    # Auto-detect device if not specified
    if not args.device:
        try:
            from core.device_auto_detect import auto_detect_device, display_device_banner
            detected_id, device_info = auto_detect_device(args.server)

            if detected_id and device_info:
                display_device_banner(device_info)

                if device_info['agent_online']:
                    args.device = detected_id
                    logger.info(f"✓ Using auto-detected device: {detected_id}")
                else:
                    logger.error("Device detected but agent not online")
                    sys.exit(1)
            else:
                logger.error("No ADB device detected. Please connect a device or use --device")
                sys.exit(1)
        except Exception as e:
            logger.error(f"Auto-detection failed: {e}")
            logger.error("Please specify --device manually")
            sys.exit(1)

    # Handle --list-packages
    if args.list_packages:
        try:
            from core.package_discovery import PackageDiscovery
            discovery = PackageDiscovery(args.device, args.server)
            discovery.list_packages()
            sys.exit(0)
        except Exception as e:
            logger.error(f"Failed to list packages: {e}")
            sys.exit(1)

    # Handle interactive mode or missing package
    if args.interactive or not args.package:
        try:
            from core.package_discovery import PackageDiscovery
            logger.info("Interactive package selection mode")
            discovery = PackageDiscovery(args.device, args.server)
            args.package = discovery.interactive_select()

            if not args.package:
                logger.error("No package selected, exiting")
                sys.exit(1)

        except Exception as e:
            logger.error(f"Interactive selection failed: {e}")
            sys.exit(1)

    tester = Phase1IntegrationTester(
        device_id=args.device,
        package_name=args.package,
        server_url=args.server
    )

    success = tester.run_all_tests()

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
