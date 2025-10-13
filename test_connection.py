#!/usr/bin/env python3
"""
Test script to verify MobileMorph Agent-Server connection
Run this after starting the server and agent to test the connection
"""

import requests
import json
import time
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

console = Console()

SERVER_URL = "http://localhost:5000"

def check_server():
    """Check if server is running"""
    try:
        response = requests.get(f"{SERVER_URL}/agents", timeout=5)
        return response.status_code == 200
    except requests.exceptions.ConnectionError:
        return False

def list_agents():
    """List all connected agents"""
    try:
        response = requests.get(f"{SERVER_URL}/agents")
        agents = response.json()

        if not agents:
            console.print("[yellow]No agents connected yet[/yellow]")
            return None

        table = Table(title="Connected Agents", show_header=True, header_style="bold magenta")
        table.add_column("Device ID", style="cyan")
        table.add_column("Manufacturer", style="green")
        table.add_column("Model", style="green")
        table.add_column("Rooted", style="yellow")
        table.add_column("Online", style="blue")

        for agent in agents:
            device_id = agent.get("device_id", "unknown")
            manufacturer = agent.get("manufacturer", "unknown")
            model = agent.get("model", "unknown")
            rooted = "Yes" if agent.get("rooted") else "No"
            online = "✓ Online" if agent.get("online") else "✗ Offline"

            table.add_row(device_id, manufacturer, model, rooted, online)

        console.print(table)
        return agents[0].get("device_id") if agents else None

    except Exception as e:
        console.print(f"[red]Error listing agents: {e}[/red]")
        return None

def send_test_command(device_id, command="id"):
    """Send a test command to agent"""
    try:
        console.print(f"\n[cyan]Sending command to {device_id}: {command}[/cyan]")

        payload = {
            "device_id": device_id,
            "command": command,
            "args": {}
        }

        response = requests.post(
            f"{SERVER_URL}/api/send_command",
            json=payload,
            headers={"Content-Type": "application/json"}
        )

        if response.status_code == 200:
            console.print("[green]✓ Command queued successfully[/green]")
            return True
        else:
            console.print(f"[red]✗ Failed to send command: {response.status_code}[/red]")
            return False

    except Exception as e:
        console.print(f"[red]Error sending command: {e}[/red]")
        return False

def get_result(device_id):
    """Get command result from agent"""
    try:
        console.print(f"[cyan]Waiting for result from {device_id}...[/cyan]")

        # Wait a bit for agent to execute and respond
        time.sleep(2)

        response = requests.get(f"{SERVER_URL}/api/get_result/{device_id}")

        if response.status_code == 200:
            data = response.json()
            result = data.get("result")

            if result:
                console.print("\n[green]✓ Received result:[/green]")
                console.print(Panel(str(result), title="Command Output", border_style="green"))
                return True
            else:
                console.print("[yellow]⚠ No result available yet[/yellow]")
                return False
        else:
            console.print(f"[red]✗ Failed to get result: {response.status_code}[/red]")
            return False

    except Exception as e:
        console.print(f"[red]Error getting result: {e}[/red]")
        return False

def run_connection_test():
    """Run complete connection test"""
    console.print(Panel.fit(
        "[bold cyan]MobileMorph Agent-Server Connection Test[/bold cyan]",
        border_style="cyan"
    ))

    # Step 1: Check server
    console.print("\n[bold]Step 1: Checking server status...[/bold]")
    if not check_server():
        console.print("[red]✗ Server is not running![/red]")
        console.print("[yellow]Start the server with: python morph_server/server/main.py[/yellow]")
        return

    console.print("[green]✓ Server is running[/green]")

    # Step 2: List agents
    console.print("\n[bold]Step 2: Looking for connected agents...[/bold]")
    device_id = list_agents()

    if not device_id:
        console.print("\n[yellow]⚠ No agents connected[/yellow]")
        console.print("[yellow]Make sure you:[/yellow]")
        console.print("  1. Installed the agent APK on device")
        console.print("  2. Opened the app and clicked 'Start Agent'")
        console.print("  3. Updated SERVER_URL in CommandService.java to your IP")
        return

    # Step 3: Send test command
    console.print(f"\n[bold]Step 3: Sending test command to {device_id}...[/bold]")
    if not send_test_command(device_id, "whoami && uname -a"):
        console.print("[red]✗ Failed to send command[/red]")
        return

    # Step 4: Get result
    console.print("\n[bold]Step 4: Retrieving command result...[/bold]")
    if get_result(device_id):
        console.print("\n" + "="*60)
        console.print("[bold green]✅ CONNECTION TEST SUCCESSFUL![/bold green]")
        console.print("="*60)
        console.print("\n[cyan]Your agent is properly connected and responding to commands.[/cyan]")
        console.print("\n[bold]Next Steps:[/bold]")
        console.print("  • Test exploit modules: /exploit/<module>")
        console.print("  • Push Frida hooks: /frida_hooks")
        console.print("  • Run OWASP scan: /run_dyna")
    else:
        console.print("\n[yellow]⚠ Agent connected but not responding[/yellow]")
        console.print("[yellow]Check device logcat:[/yellow]")
        console.print("  adb logcat | grep -E '(CommandService|WS)'")

def interactive_mode():
    """Interactive command testing mode"""
    console.print(Panel.fit(
        "[bold cyan]Interactive Command Mode[/bold cyan]",
        border_style="cyan"
    ))

    device_id = list_agents()
    if not device_id:
        console.print("[red]No agents connected[/red]")
        return

    console.print(f"\n[green]Connected to device: {device_id}[/green]")
    console.print("[dim]Type 'exit' to quit[/dim]\n")

    while True:
        try:
            command = input("morph> ")
            if command.lower() in ['exit', 'quit', 'q']:
                break

            if not command.strip():
                continue

            send_test_command(device_id, command)
            get_result(device_id)
            print()

        except KeyboardInterrupt:
            print("\n")
            break
        except Exception as e:
            console.print(f"[red]Error: {e}[/red]")

def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="Test MobileMorph Agent-Server Connection"
    )
    parser.add_argument(
        '--interactive', '-i',
        action='store_true',
        help='Enter interactive command mode'
    )
    parser.add_argument(
        '--server-url',
        default='http://localhost:5000',
        help='Server URL (default: http://localhost:5000)'
    )

    args = parser.parse_args()

    global SERVER_URL
    SERVER_URL = args.server_url

    if args.interactive:
        interactive_mode()
    else:
        run_connection_test()

if __name__ == "__main__":
    main()
