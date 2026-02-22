"""
MobileMorphAgentBridge - Integration bridge between DYNA and MobileMorphAgent

This module provides a bridge layer that allows the DYNA OWASP testing framework
to invoke MobileMorphAgent modules for real-time dynamic analysis.

It translates Drozer-style commands into MobileMorphAgent module calls and
handles the communication with the Flask C2 server.
"""

import requests
import time
import json
import logging
from typing import Dict, Optional, Tuple, Any

logger = logging.getLogger(__name__)


class MobileMorphAgentBridge:
    """
    Bridge between DYNA framework and MobileMorphAgent.

    Provides compatibility with Drozer-style commands while using
    MobileMorphAgent's module system for dynamic testing.
    """

    # Mapping of Drozer commands to MobileMorphAgent modules
    DROZER_TO_MODULE_MAP = {
        "app.package.manifest":         ("ManifestAnalyzer",        "analyze"),
        "app.package.info":             ("PackageEnumerator",        "enumerate"),
        "app.package.attacksurface":    ("ManifestAnalyzer",        "analyze"),
        "app.provider.info":            ("ContentProviderExploiter", "exploit"),
        "app.provider.query":           ("ContentProviderExploiter", "exploit"),
        "scanner.provider.traversal":   ("ContentProviderExploiter", "exploit"),
        "scanner.provider.injection":   ("ContentProviderExploiter", "exploit"),
        "scanner.provider.sqltables":   ("ContentProviderExploiter", "exploit"),
        "app.activity.info":            ("ManifestAnalyzer",        "analyze"),
        "app.service.info":             ("ManifestAnalyzer",        "analyze"),
        "scanner.misc.readablefiles":   ("IPCExploiter",            "exploit"),
        "shell.exec":                   ("SystemCommandExecutor",   "execute"),
        "frida.run":                    ("FridaAutomationModule",   "run"),
        "frida.reflection":             ("ReflectionMonitorModule", "monitor"),
    }

    def __init__(self, device_id: str, package_name: str, server_url: str = "http://127.0.0.1:5000"):
        """
        Initialize the bridge.

        Args:
            device_id: Device ID of the connected MobileMorphAgent
            package_name: Target package name for analysis
            server_url: URL of the Flask C2 server
        """
        self.device_id = device_id
        self.package_name = package_name
        self.server_url = server_url.rstrip('/')
        self.agent_available = False
        self.last_error = None
        self.timeout = 30  # seconds

        # Check agent availability on initialization
        self._check_availability()

    def _check_availability(self) -> bool:
        """Check if the agent is connected and available."""
        try:
            response = requests.get(f"{self.server_url}/agents", timeout=5)
            if response.status_code == 200:
                agents = response.json()
                for agent in agents:
                    if agent.get("device_id") == self.device_id and agent.get("online"):
                        self.agent_available = True
                        logger.info(f"[Bridge] Agent {self.device_id} is online and available")
                        return True

            self.agent_available = False
            self.last_error = "Agent not found or offline"
            logger.warning(f"[Bridge] Agent {self.device_id} not available")
            return False

        except Exception as e:
            self.agent_available = False
            self.last_error = f"Connection error: {str(e)}"
            logger.error(f"[Bridge] Error checking agent availability: {e}")
            return False

    def invoke_agent_module(self, module_name: str, args: Dict[str, Any]) -> Dict[str, Any]:
        """
        Invoke a MobileMorphAgent module and return the result.

        Args:
            module_name: Name of the module (e.g., "ManifestAnalyzer")
            args: Arguments dictionary for the module

        Returns:
            Dictionary containing the module result

        Raises:
            Exception: If the module invocation fails
        """
        if not self.agent_available:
            self._check_availability()
            if not self.agent_available:
                raise Exception(f"Agent not available: {self.last_error}")

        try:
            logger.info(f"[Bridge] Invoking module {module_name} on {self.device_id}")
            logger.debug(f"[Bridge] Module args: {args}")

            # Send module invocation request to server
            response = requests.post(
                f"{self.server_url}/api/agent/module/{self.device_id}",
                json={
                    "module": module_name,
                    "args": args
                },
                timeout=5
            )

            if response.status_code != 200:
                raise Exception(f"Module invocation failed: {response.text}")

            # Poll for result
            result = self._wait_for_result(timeout=self.timeout)

            if result is None:
                raise Exception(f"Timeout waiting for module result (>{self.timeout}s)")

            logger.info(f"[Bridge] Module {module_name} completed successfully")
            return result

        except Exception as e:
            logger.error(f"[Bridge] Module invocation error: {e}")
            raise

    def _wait_for_result(self, timeout: int = 30) -> Optional[Dict[str, Any]]:
        """
        Wait for module result from the agent.

        Args:
            timeout: Maximum time to wait in seconds

        Returns:
            Result dictionary or None if timeout
        """
        start_time = time.time()
        last_result = None

        while (time.time() - start_time) < timeout:
            try:
                response = requests.get(
                    f"{self.server_url}/api/get_result/{self.device_id}",
                    timeout=2
                )

                if response.status_code == 200:
                    result = response.json().get("result")

                    # Check if we got a new result
                    if result and result != last_result:
                        # Verify it's a valid module result
                        if isinstance(result, dict) and "status" in result:
                            return result
                        last_result = result

                time.sleep(0.5)  # Poll every 500ms

            except Exception as e:
                logger.debug(f"[Bridge] Polling error: {e}")
                time.sleep(0.5)

        return None

    def run_command(self, cmd: str) -> str:
        """
        Execute a Drozer-style command via agent modules.

        This method provides backward compatibility with Drozer commands
        by translating them into agent module invocations.

        Args:
            cmd: Drozer-style command (e.g., "run app.package.manifest com.example.app")

        Returns:
            String output formatted for DYNA compatibility
        """
        try:
            # Parse the Drozer command
            module_name, args = self._parse_drozer_command(cmd)

            if not module_name:
                return f"[!] Unsupported command: {cmd}"

            # Invoke the corresponding agent module
            result = self.invoke_agent_module(module_name, args)

            # Format result as Drozer-style output
            return self._format_result_as_drozer(result)

        except Exception as e:
            logger.error(f"[Bridge] Command execution failed: {e}")
            return f"[!] Error executing command: {str(e)}"

    def run_command_safe(self, cmd: str, fallback_msg: str) -> str:
        """
        Execute command with fallback message on failure.

        Args:
            cmd: Drozer-style command
            fallback_msg: Message to return if command fails

        Returns:
            Command result or fallback message
        """
        try:
            if not self.agent_available:
                return fallback_msg
            return self.run_command(cmd)
        except Exception as e:
            logger.warning(f"[Bridge] Command failed, using fallback: {e}")
            return fallback_msg

    def _parse_drozer_command(self, cmd: str) -> Tuple[Optional[str], Dict[str, Any]]:
        """
        Parse Drozer command into module name and arguments.

        Args:
            cmd: Drozer command string

        Returns:
            Tuple of (module_name, args_dict)
        """
        # Remove "run " prefix if present
        if cmd.startswith("run "):
            cmd = cmd[4:]

        parts = cmd.split()
        if not parts:
            return None, {}

        drozer_module = parts[0]

        # Map Drozer module to agent module
        if drozer_module in self.DROZER_TO_MODULE_MAP:
            agent_module, operation = self.DROZER_TO_MODULE_MAP[drozer_module]

            # Build args based on command
            args = {"package": self.package_name}

            # Handle specific command types
            if "provider.query" in drozer_module and len(parts) > 1:
                args["operation"] = "query"
                args["authority"] = parts[2] if "-a" in parts else parts[1]
            elif "provider.traversal" in drozer_module:
                args["operation"] = "test_traversal"
                if "-a" in parts:
                    args["authority"] = parts[parts.index("-a") + 1]
            elif "provider.injection" in drozer_module:
                args["operation"] = "test_sqli"
                if "-a" in parts:
                    args["authority"] = parts[parts.index("-a") + 1]
            elif "provider.sqltables" in drozer_module:
                args["operation"] = "enumerate_sql_tables"
                if "-a" in parts:
                    args["authority"] = parts[parts.index("-a") + 1]
            elif drozer_module == "shell.exec" and len(parts) > 1:
                # Everything after "shell.exec" is the shell command
                args["command"] = " ".join(parts[1:])
            elif drozer_module in ("frida.run", "frida.reflection"):
                # frida.run <target_package> [--mode spawn|attach] [--duration N]
                # frida.reflection <target_package> [--mode spawn|attach] [--duration N]
                if len(parts) > 1 and not parts[1].startswith("-"):
                    args["target_package"] = parts[1]
                else:
                    args["target_package"] = self.package_name
                if "--mode" in parts:
                    args["mode"] = parts[parts.index("--mode") + 1]
                if "--duration" in parts:
                    try:
                        args["duration"] = int(parts[parts.index("--duration") + 1])
                    except (ValueError, IndexError):
                        pass
            elif len(parts) > 1 and not parts[1].startswith("-"):
                # If there's a package name in the command, use it
                args["package"] = parts[1]

            return agent_module, args

        logger.warning(f"[Bridge] No mapping for Drozer command: {drozer_module}")
        return None, {}

    def _format_result_as_drozer(self, result: Dict[str, Any]) -> str:
        """
        Format agent module result as Drozer-style output.

        Args:
            result: Module result dictionary

        Returns:
            Formatted string output
        """
        if result.get("status") == "error":
            return f"[!] Error: {result.get('error', 'Unknown error')}"

        data = result.get("data", {})

        # Format based on data content
        output_lines = []

        if isinstance(data, dict):
            # Handle manifest analysis results
            if "package_name" in data:
                output_lines.append(f"Package: {data['package_name']}")
                if "version_name" in data:
                    output_lines.append(f"  Version: {data['version_name']}")

                # Format flags
                if "flags" in data:
                    output_lines.append("\nApplication Flags:")
                    for key, value in data["flags"].items():
                        output_lines.append(f"  {key}: {value}")

                # Format components
                for component_type in ["activities", "services", "receivers", "providers"]:
                    if component_type in data and data[component_type]:
                        output_lines.append(f"\n{component_type.title()}:")
                        for item in data[component_type]:
                            name = item.get("name", "unknown")
                            exported = item.get("exported", False)
                            permission = item.get("permission", "None")
                            output_lines.append(f"  {name}")
                            output_lines.append(f"    Exported: {exported}")
                            output_lines.append(f"    Permission: {permission}")

                # Format permissions
                if "permissions" in data and data["permissions"]:
                    output_lines.append(f"\nPermissions ({len(data['permissions'])}):")
                    for perm in data["permissions"][:20]:  # Limit to first 20
                        output_lines.append(f"  - {perm}")

            # Handle SQL table enumeration results
            elif "tables" in data:
                output_lines.append(f"Authority: {data.get('authority', '')}")
                output_lines.append(f"Tables found: {data.get('table_count', 0)}")
                tables = data.get("tables", [])
                if isinstance(tables, list):
                    for t in tables:
                        output_lines.append(f"  [{t.get('method', '')}] {t.get('name', '')}")
                        if "columns" in t and t["columns"]:
                            cols = t["columns"] if isinstance(t["columns"], list) else []
                            output_lines.append(f"    Columns: {', '.join(cols)}")
                        if "row_count" in t:
                            output_lines.append(f"    Rows: {t['row_count']}")

            # Handle shell command results
            elif "command" in data:
                output_lines.append(f"$ {data['command']}")
                output_lines.append(data.get("output", ""))

            # Handle provider query results
            elif "uri" in data:
                output_lines.append(f"URI: {data['uri']}")
                output_lines.append(f"Rows: {data.get('row_count', 0)}")
                if "data" in data and data["data"]:
                    output_lines.append("\nData:")
                    for row in data["data"][:5]:  # Show first 5 rows
                        output_lines.append(f"  {json.dumps(row, indent=2)}")

            # Handle reflection monitor results (risk_level + findings dict)
            elif "risk_level" in data:
                output_lines.append(f"Target: {data.get('target_package', '')}")
                output_lines.append(f"Risk Level: {data.get('risk_level', 'UNKNOWN')}")
                output_lines.append(f"Total Events: {data.get('total_events', 0)}")
                duration_ms = data.get("duration_ms", 0)
                output_lines.append(f"Duration: {duration_ms / 1000:.1f}s")
                findings = data.get("findings", {})
                if isinstance(findings, dict):
                    dex_loads = findings.get("dex_loads", [])
                    class_lookups = findings.get("class_lookups", [])
                    method_invocations = findings.get("method_invocations", [])
                    output_lines.append(f"\nDynamic DEX Loads ({len(dex_loads)}):")
                    for d in dex_loads[:10]:
                        output_lines.append(f"  dexPath: {d.get('dexPath', '')}  optimizedDir: {d.get('optimizedDir', '')}")
                    output_lines.append(f"\nClass Lookups ({len(class_lookups)}):")
                    for c in class_lookups[:10]:
                        output_lines.append(f"  {c.get('className', '')}")
                    output_lines.append(f"\nMethod Invocations ({len(method_invocations)}):")
                    for m in method_invocations[:10]:
                        output_lines.append(f"  {m.get('declaringClass', '')}.{m.get('method', '')}")
                hook_counts = data.get("hook_counts", {})
                if hook_counts:
                    output_lines.append("\nHook Counts:")
                    for hook, count in hook_counts.items():
                        output_lines.append(f"  {hook}: {count}")

            # Handle Frida automation results (event_count + output lines)
            elif "event_count" in data:
                output_lines.append(f"Target: {data.get('target_package', '')}")
                output_lines.append(f"Script: {data.get('script', '')}")
                duration_ms = data.get("duration_ms", 0)
                output_lines.append(f"Duration: {duration_ms / 1000:.1f}s")
                output_lines.append(f"Events captured: {data.get('event_count', 0)}")
                output_lines.append(f"Output lines: {data.get('line_count', 0)}")
                events = data.get("events", [])
                if events:
                    output_lines.append(f"\nEvents ({min(len(events), 20)} of {len(events)}):")
                    for ev in events[:20]:
                        hook = ev.get("hook", ev.get("type", ""))
                        ts = ev.get("timestamp", "")
                        ev_data = ev.get("data", {})
                        output_lines.append(f"  [{ts}] {hook}: {json.dumps(ev_data)}")
                raw_output = data.get("output", [])
                if raw_output:
                    output_lines.append(f"\nConsole Output ({len(raw_output)} lines):")
                    for line in raw_output[:30]:
                        output_lines.append(f"  {line}")

            # Handle vulnerability test results
            elif "vulnerable" in data:
                vuln_status = "VULNERABLE" if data["vulnerable"] else "NOT VULNERABLE"
                output_lines.append(f"Status: {vuln_status}")
                if "findings" in data and data["findings"]:
                    output_lines.append("\nFindings:")
                    findings = data["findings"]
                    if isinstance(findings, list):
                        for finding in findings:
                            output_lines.append(f"  - {json.dumps(finding)}")

        return "\n".join(output_lines) if output_lines else str(data)

    def check_connection(self) -> bool:
        """
        Check if connection to agent is active.

        Returns:
            True if agent is connected and responsive
        """
        return self._check_availability()

    def get_connection_status(self) -> Dict[str, Any]:
        """
        Get detailed connection status.

        Returns:
            Dictionary with status information
        """
        return {
            "connected": self.agent_available,
            "device_id": self.device_id,
            "server_url": self.server_url,
            "last_error": self.last_error
        }

    def start_drozer(self) -> bool:
        """
        Initialize connection (for Drozer compatibility).

        Returns:
            True if agent is available
        """
        logger.info(f"[Bridge] Initializing MobileMorphAgent connection for {self.package_name}")
        return self._check_availability()

    def check_agent_connection(self) -> bool:
        """Legacy method for backward compatibility."""
        return self.check_connection()
