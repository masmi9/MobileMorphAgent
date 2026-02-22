"""
Package Discovery Utility

Dynamically discovers and lists installed packages on connected Android devices
for easy selection during DYNA + MobileMorphAgent testing.
"""

import json
import logging
import requests
from typing import List, Dict, Optional, Any
from rich.console import Console
from rich.table import Table
from rich.prompt import Prompt, Confirm

logger = logging.getLogger(__name__)
console = Console()


class PackageDiscovery:
    """Discover and select packages from connected Android agents."""

    def __init__(self, device_id: str, server_url: str = "http://127.0.0.1:5000"):
        self.device_id = device_id
        self.server_url = server_url.rstrip('/')
        self.packages = []

    def discover_packages(self, filter_pattern: str = None) -> List[Dict[str, Any]]:
        """
        Discover installed packages on the connected device.

        Args:
            filter_pattern: Optional filter (e.g., "com.android" to show only Android packages)

        Returns:
            List of package information dictionaries
        """
        try:
            # Import bridge to invoke PackageEnumerator
            from core.mobilemorph_bridge import MobileMorphAgentBridge

            bridge = MobileMorphAgentBridge(
                self.device_id,
                "",  # Package name not needed for enumeration
                self.server_url
            )

            if not bridge.agent_available:
                logger.error(f"Agent {self.device_id} not available")
                return []

            # Invoke PackageEnumerator module
            result = bridge.invoke_agent_module(
                "PackageEnumerator",
                {"filter": filter_pattern or ""}
            )

            if result.get('status') == 'success':
                self.packages = result.get('data', {}).get('packages', [])
                return self.packages
            else:
                logger.error(f"Package enumeration failed: {result.get('error')}")
                return []

        except Exception as e:
            logger.error(f"Error discovering packages: {e}")
            return []

    def list_packages(self, filter_pattern: str = None, limit: int = None) -> None:
        """
        Display discovered packages in a formatted table.

        Args:
            filter_pattern: Optional filter pattern
            limit: Maximum number of packages to display
        """
        packages = self.discover_packages(filter_pattern)

        if not packages:
            console.print("[red]No packages found or agent not available[/red]")
            return

        # Apply limit if specified
        if limit:
            packages = packages[:limit]

        # Create rich table
        table = Table(title=f"📦 Installed Packages on {self.device_id}")
        table.add_column("Package Name", style="cyan", no_wrap=False)
        table.add_column("Version", style="green")
        table.add_column("System", style="yellow")
        table.add_column("Debuggable", style="red")

        for pkg in packages:
            package_name = pkg.get('package_name', 'unknown')
            version = pkg.get('version_name', 'N/A')
            is_system = "✓" if pkg.get('is_system_app', False) else ""
            debuggable = "✓" if pkg.get('debuggable', False) else ""

            table.add_row(package_name, version, is_system, debuggable)

        console.print(table)
        console.print(f"\n[bold]Total packages: {len(packages)}[/bold]")

        if limit and len(self.packages) > limit:
            console.print(f"[dim]Showing {limit} of {len(self.packages)} packages[/dim]")

    def interactive_select(self, filter_pattern: str = None) -> Optional[str]:
        """
        Interactive package selection with search and filtering.

        Args:
            filter_pattern: Initial filter pattern

        Returns:
            Selected package name or None
        """
        console.print("\n[bold cyan]📱 Interactive Package Selection[/bold cyan]\n")

        # Discover packages
        console.print("[yellow]Discovering packages...[/yellow]")
        packages = self.discover_packages(filter_pattern)

        if not packages:
            console.print("[red]No packages found![/red]")
            return None

        while True:
            console.print(f"\n[green]Found {len(packages)} packages[/green]")

            # Show filtering options
            console.print("\n[bold]Filter Options:[/bold]")
            console.print("  1. Show all packages")
            console.print("  2. Show only user apps (non-system)")
            console.print("  3. Show only debuggable apps")
            console.print("  4. Filter by name pattern")
            console.print("  5. List packages")
            console.print("  6. Select package by number")
            console.print("  7. Enter package name manually")
            console.print("  q. Quit")

            choice = Prompt.ask("\n[cyan]Select option[/cyan]", default="5")

            if choice == "1":
                packages = self.discover_packages()
            elif choice == "2":
                packages = [p for p in self.packages if not p.get('is_system_app', False)]
                console.print(f"[green]Filtered to {len(packages)} user apps[/green]")
            elif choice == "3":
                packages = [p for p in self.packages if p.get('debuggable', False)]
                console.print(f"[green]Filtered to {len(packages)} debuggable apps[/green]")
            elif choice == "4":
                pattern = Prompt.ask("[cyan]Enter filter pattern[/cyan] (e.g., 'com.android')")
                packages = [p for p in self.packages if pattern.lower() in p.get('package_name', '').lower()]
                console.print(f"[green]Filtered to {len(packages)} matching packages[/green]")
            elif choice == "5":
                # Display packages
                self._display_numbered_packages(packages, limit=20)
            elif choice == "6":
                # Select by number
                self._display_numbered_packages(packages, limit=20)
                try:
                    num = int(Prompt.ask("[cyan]Enter package number[/cyan]"))
                    if 0 <= num < len(packages):
                        selected = packages[num]['package_name']
                        console.print(f"\n[green]✓ Selected: {selected}[/green]")
                        return selected
                    else:
                        console.print("[red]Invalid number![/red]")
                except ValueError:
                    console.print("[red]Invalid input![/red]")
            elif choice == "7":
                # Manual entry
                pkg_name = Prompt.ask("[cyan]Enter package name[/cyan]")
                if Confirm.ask(f"Use package [cyan]{pkg_name}[/cyan]?"):
                    return pkg_name
            elif choice.lower() == "q":
                return None
            else:
                console.print("[red]Invalid choice![/red]")

    def _display_numbered_packages(self, packages: List[Dict], limit: int = 20) -> None:
        """Display packages with numbers for selection."""
        table = Table(title="📦 Available Packages")
        table.add_column("#", style="dim", width=4)
        table.add_column("Package Name", style="cyan")
        table.add_column("Version", style="green")
        table.add_column("Flags", style="yellow")

        for i, pkg in enumerate(packages[:limit]):
            flags = []
            if pkg.get('is_system_app'):
                flags.append("SYS")
            if pkg.get('debuggable'):
                flags.append("DEBUG")

            table.add_row(
                str(i),
                pkg.get('package_name', 'unknown'),
                pkg.get('version_name', 'N/A'),
                " ".join(flags)
            )

        console.print(table)

        if len(packages) > limit:
            console.print(f"[dim]Showing first {limit} of {len(packages)} packages[/dim]")

    def get_package_details(self, package_name: str) -> Optional[Dict[str, Any]]:
        """
        Get detailed information about a specific package.

        Args:
            package_name: Package name to query

        Returns:
            Package details dictionary or None
        """
        try:
            from core.mobilemorph_bridge import MobileMorphAgentBridge

            bridge = MobileMorphAgentBridge(
                self.device_id,
                package_name,
                self.server_url
            )

            result = bridge.invoke_agent_module(
                "ManifestAnalyzer",
                {"package": package_name}
            )

            if result.get('status') == 'success':
                return result.get('data', {})
            else:
                return None

        except Exception as e:
            logger.error(f"Error getting package details: {e}")
            return None

    def display_package_details(self, package_name: str) -> None:
        """Display detailed information about a package."""
        console.print(f"\n[bold cyan]📱 Package Details: {package_name}[/bold cyan]\n")

        details = self.get_package_details(package_name)

        if not details:
            console.print("[red]Could not retrieve package details[/red]")
            return

        # Basic info
        console.print(f"[bold]Package:[/bold] {details.get('package_name')}")
        console.print(f"[bold]Version:[/bold] {details.get('version_name')} (code: {details.get('version_code')})")

        # Flags
        flags = details.get('flags', {})
        console.print("\n[bold]Security Flags:[/bold]")
        console.print(f"  Debuggable: {self._flag_icon(flags.get('debuggable'))}")
        console.print(f"  Allow Backup: {self._flag_icon(flags.get('allow_backup'))}")
        console.print(f"  Test Only: {self._flag_icon(flags.get('test_only'))}")
        console.print(f"  Target SDK: {flags.get('target_sdk')}")
        console.print(f"  Min SDK: {flags.get('min_sdk')}")

        # Components
        console.print("\n[bold]Components:[/bold]")
        console.print(f"  Activities: {len(details.get('activities', []))}")
        console.print(f"  Services: {len(details.get('services', []))}")
        console.print(f"  Receivers: {len(details.get('receivers', []))}")
        console.print(f"  Providers: {len(details.get('providers', []))}")

        # Exported components
        activities = details.get('activities', [])
        exported_activities = [a for a in activities if a.get('exported')]
        if exported_activities:
            console.print(f"\n[yellow]⚠ {len(exported_activities)} exported activities found[/yellow]")

        providers = details.get('providers', [])
        exported_providers = [p for p in providers if p.get('exported')]
        if exported_providers:
            console.print(f"[yellow]⚠ {len(exported_providers)} exported content providers found[/yellow]")

        # Permissions
        permissions = details.get('permissions', [])
        console.print(f"\n[bold]Permissions:[/bold] {len(permissions)}")
        dangerous_perms = [p for p in permissions if any(x in p for x in ['INTERNET', 'READ_', 'WRITE_', 'CAMERA', 'LOCATION'])]
        if dangerous_perms:
            console.print(f"[yellow]Notable permissions:[/yellow]")
            for perm in dangerous_perms[:5]:
                console.print(f"  - {perm}")

    def _flag_icon(self, value: bool) -> str:
        """Return colored icon for boolean flag."""
        return "[red]✓[/red]" if value else "[green]✗[/green]"

    def search_packages(self, keyword: str) -> List[Dict[str, Any]]:
        """
        Search packages by keyword.

        Args:
            keyword: Search keyword

        Returns:
            List of matching packages
        """
        if not self.packages:
            self.discover_packages()

        keyword_lower = keyword.lower()
        return [
            pkg for pkg in self.packages
            if keyword_lower in pkg.get('package_name', '').lower()
        ]


def main():
    """CLI entry point for package discovery."""
    import argparse

    parser = argparse.ArgumentParser(description="Discover and select Android packages")
    parser.add_argument("--device", required=True, help="Device ID")
    parser.add_argument("--server", default="http://127.0.0.1:5000", help="Server URL")
    parser.add_argument("--list", action="store_true", help="List all packages")
    parser.add_argument("--filter", help="Filter pattern")
    parser.add_argument("--interactive", "-i", action="store_true", help="Interactive selection")
    parser.add_argument("--details", help="Show details for specific package")

    args = parser.parse_args()

    discovery = PackageDiscovery(args.device, args.server)

    if args.details:
        discovery.display_package_details(args.details)
    elif args.interactive:
        selected = discovery.interactive_select(args.filter)
        if selected:
            console.print(f"\n[bold green]Selected package: {selected}[/bold green]")
    elif args.list:
        discovery.list_packages(args.filter)
    else:
        console.print("[yellow]Use --list, --interactive, or --details[/yellow]")


if __name__ == "__main__":
    main()
