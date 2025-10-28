#!/usr/bin/env python3
"""
MobileMorph Agent Client - Drozer Replacement C2 Client

This client connects to the Android agent via ADB port forwarding and provides
a command-line interface for dynamic Android application security testing.

Architecture:
  [Desktop] --> ADB forward tcp:31415 tcp:31415 --> [Android Agent ServerSocket]

Usage:
    python agent_client.py
    python agent_client.py --package com.example.app
"""

import socket
import json
import subprocess
import sys
import argparse
from typing import Dict, Any, Optional

class AgentClient:
    """Client for communicating with MobileMorph Android Agent"""

    def __init__(self, host='localhost', port=31415):
        self.host = host
        self.port = port
        self.socket = None
        self.connected = False

    def setup_adb_forward(self):
        """Setup ADB port forwarding"""
        try:
            print(f"[*] Setting up ADB port forwarding: tcp:{self.port} -> tcp:{self.port}")
            result = subprocess.run(
                ['adb', 'forward', f'tcp:{self.port}', f'tcp:{self.port}'],
                capture_output=True,
                text=True
            )

            if result.returncode != 0:
                print(f"[!] ADB forward failed: {result.stderr}")
                return False

            print(f"[+] ADB port forwarding established")
            return True

        except FileNotFoundError:
            print("[!] Error: 'adb' command not found. Please install Android SDK Platform Tools.")
            return False
        except Exception as e:
            print(f"[!] ADB forward error: {e}")
            return False

    def connect(self):
        """Connect to the agent"""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.connect((self.host, self.port))
            self.connected = True
            print(f"[+] Connected to agent at {self.host}:{self.port}")

            # Test connection with ping
            response = self.send_command("ping", {})
            if response and response.get("status") == "success":
                print("[+] Agent is responsive")
                return True
            else:
                print("[!] Agent connection test failed")
                return False

        except ConnectionRefusedError:
            print(f"[!] Connection refused. Make sure:")
            print(f"    1. Agent is running on Android device")
            print(f"    2. ADB forward is set up: adb forward tcp:{self.port} tcp:{self.port}")
            return False
        except Exception as e:
            print(f"[!] Connection error: {e}")
            return False

    def disconnect(self):
        """Disconnect from agent"""
        if self.socket:
            try:
                self.socket.close()
                print("[+] Disconnected from agent")
            except:
                pass
        self.connected = False

    def send_command(self, command: str, args: Dict[str, Any]) -> Optional[Dict]:
        """Send command to agent and receive response"""
        if not self.connected:
            print("[!] Not connected to agent")
            return None

        try:
            # Build command JSON
            cmd_obj = {
                "command": command,
                "args": args
            }

            # Send command (newline-delimited JSON)
            cmd_json = json.dumps(cmd_obj) + "\n"
            self.socket.sendall(cmd_json.encode('utf-8'))

            # Receive response
            response_data = b""
            while True:
                chunk = self.socket.recv(4096)
                if not chunk:
                    break
                response_data += chunk
                if b'\n' in response_data:
                    break

            # Parse response
            response_str = response_data.decode('utf-8').strip()
            response = json.loads(response_str)

            return response

        except json.JSONDecodeError as e:
            print(f"[!] Invalid JSON response: {e}")
            return None
        except Exception as e:
            print(f"[!] Command send error: {e}")
            self.connected = False
            return None

    def manifest_analysis(self, package: str) -> Optional[Dict]:
        """Analyze AndroidManifest.xml of target package"""
        print(f"\n[*] Analyzing manifest for {package}...")
        return self.send_command("manifest_analysis", {"package": package})

    def package_enum(self, include_system=False, exported_only=True, filter_pkg=None) -> Optional[Dict]:
        """Enumerate installed packages"""
        print(f"\n[*] Enumerating packages...")
        args = {
            "include_system": include_system,
            "exported_only": exported_only
        }
        if filter_pkg:
            args["filter"] = filter_pkg

        return self.send_command("package_enum", args)

    def permission_audit(self, package: str = None, find_permission: str = None) -> Optional[Dict]:
        """Audit permissions"""
        print(f"\n[*] Auditing permissions...")
        args = {}
        if package:
            args["package"] = package
        if find_permission:
            args["find_permission"] = find_permission

        return self.send_command("permission_audit", args)

    def exploit_intent(self, package: str, component: str, intent_type="activity",
                      action=None, extras=None) -> Optional[Dict]:
        """Send crafted intent to component"""
        print(f"\n[*] Exploiting intent: {package}/{component}")
        args = {
            "package": package,
            "component": component,
            "type": intent_type
        }
        if action:
            args["action"] = action
        if extras:
            args["extras"] = extras

        return self.send_command("exploit_intent", args)

    def exploit_provider(self, authority: str, operation="query", path="", **kwargs) -> Optional[Dict]:
        """Test Content Provider vulnerabilities"""
        print(f"\n[*] Exploiting Content Provider: {authority}")
        args = {
            "authority": authority,
            "operation": operation,
            "path": path
        }
        args.update(kwargs)

        return self.send_command("exploit_provider", args)

    def exploit_webview(self, package: str = None, operation="enumerate") -> Optional[Dict]:
        """Test WebView vulnerabilities"""
        print(f"\n[*] Testing WebView vulnerabilities...")
        args = {"operation": operation}
        if package:
            args["package"] = package

        return self.send_command("exploit_webview", args)

    def exploit_ipc(self, package: str, operation="attack_surface") -> Optional[Dict]:
        """Test IPC vulnerabilities"""
        print(f"\n[*] Analyzing IPC attack surface for {package}...")
        args = {
            "package": package,
            "operation": operation
        }

        return self.send_command("exploit_ipc", args)

    def shell(self, cmd: str) -> Optional[Dict]:
        """Execute shell command on device"""
        print(f"\n[*] Executing shell: {cmd}")
        return self.send_command("shell", {"cmd": cmd})

    def pretty_print_response(self, response: Optional[Dict]):
        """Pretty print JSON response"""
        if not response:
            print("[!] No response received")
            return

        print("\n" + "="*60)

        status = response.get("status", "unknown")
        if status == "success":
            print("[+] SUCCESS")
            data = response.get("data")
            if data:
                print("\nData:")
                print(json.dumps(data, indent=2))
        else:
            print("[!] ERROR")
            error = response.get("error")
            if error:
                print(f"\nError: {error}")

        print("="*60 + "\n")


def interactive_mode(client: AgentClient):
    """Interactive CLI mode"""
    print("\n" + "="*60)
    print("MobileMorph Agent - Interactive Mode")
    print("="*60)
    print("\nCommands:")
    print("  manifest <package>              - Analyze manifest")
    print("  packages [filter]               - List packages")
    print("  permissions <package>           - Audit permissions")
    print("  attack_surface <package>        - Show IPC attack surface")
    print("  intent <package> <component>    - Send intent")
    print("  provider <authority>            - Query content provider")
    print("  shell <command>                 - Execute shell command")
    print("  help                            - Show this help")
    print("  exit                            - Exit")
    print()

    while True:
        try:
            cmd = input("morph> ").strip()

            if not cmd:
                continue

            if cmd == "exit":
                break

            if cmd == "help":
                interactive_mode(client)
                return

            parts = cmd.split(maxsplit=2)
            command = parts[0]

            if command == "manifest" and len(parts) >= 2:
                response = client.manifest_analysis(parts[1])
                client.pretty_print_response(response)

            elif command == "packages":
                filter_pkg = parts[1] if len(parts) >= 2 else None
                response = client.package_enum(exported_only=True, filter_pkg=filter_pkg)
                client.pretty_print_response(response)

            elif command == "permissions" and len(parts) >= 2:
                response = client.permission_audit(package=parts[1])
                client.pretty_print_response(response)

            elif command == "attack_surface" and len(parts) >= 2:
                response = client.exploit_ipc(parts[1], "attack_surface")
                client.pretty_print_response(response)

            elif command == "intent" and len(parts) >= 3:
                pkg = parts[1]
                component = parts[2]
                response = client.exploit_intent(pkg, component)
                client.pretty_print_response(response)

            elif command == "provider" and len(parts) >= 2:
                authority = parts[1]
                response = client.exploit_provider(authority)
                client.pretty_print_response(response)

            elif command == "shell" and len(parts) >= 2:
                shell_cmd = cmd[6:]  # Everything after "shell "
                response = client.shell(shell_cmd)
                client.pretty_print_response(response)

            else:
                print("[!] Unknown command or invalid syntax. Type 'help' for available commands.")

        except KeyboardInterrupt:
            print("\n[*] Use 'exit' to quit")
        except Exception as e:
            print(f"[!] Error: {e}")


def main():
    parser = argparse.ArgumentParser(description='MobileMorph Agent Client - Drozer Replacement')
    parser.add_argument('--host', default='localhost', help='Agent host (default: localhost)')
    parser.add_argument('--port', type=int, default=31415, help='Agent port (default: 31415)')
    parser.add_argument('--no-forward', action='store_true', help='Skip ADB port forwarding setup')
    parser.add_argument('--package', '-p', help='Target package for analysis')
    parser.add_argument('--command', '-c', help='Command to execute (manifest, packages, permissions, etc.)')
    args = parser.parse_args()

    print("\n" + "="*60)
    print("MobileMorph Agent Client v1.0")
    print("Drozer Replacement with Enhanced C2 Capabilities")
    print("="*60 + "\n")

    client = AgentClient(host=args.host, port=args.port)

    # Setup ADB forwarding unless skipped
    if not args.no_forward:
        if not client.setup_adb_forward():
            sys.exit(1)

    # Connect to agent
    if not client.connect():
        sys.exit(1)

    try:
        # Execute specific command if provided
        if args.command and args.package:
            if args.command == "manifest":
                response = client.manifest_analysis(args.package)
                client.pretty_print_response(response)
            elif args.command == "permissions":
                response = client.permission_audit(package=args.package)
                client.pretty_print_response(response)
            elif args.command == "attack_surface":
                response = client.exploit_ipc(args.package, "attack_surface")
                client.pretty_print_response(response)
            else:
                print(f"[!] Unknown command: {args.command}")
        else:
            # Enter interactive mode
            interactive_mode(client)

    finally:
        client.disconnect()


if __name__ == "__main__":
    main()
