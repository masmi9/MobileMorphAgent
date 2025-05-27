#!/usr/bin/env python3
"""
Main entry point for the Automated OWASP Dynamic Scanner.

This module provides functionality to analyze Android applications for security
vulnerabilities based on the OWASP Mobile Application Security Verification
Standard (MASVS).
"""

import argparse
import importlib
import logging
import os
import pkgutil
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Tuple, Union
import requests

from rich.logging import RichHandler
from rich.progress import Progress
from rich.text import Text

from core.analyzer import APKAnalyzer
from core.apk_ctx import APKContext
from core.drozer_helper import DrozerHelper
from core.report_generator import ReportGenerator
from core.agent_helper import send_command

# Configure RichHandler for logging
logging.basicConfig(
    level=logging.INFO,
    handlers=[RichHandler(rich_tracebacks=True, show_path=False, show_level=True)],
)


def print_banner() -> None:
    """
    Print the application banner to the console.
    Clears the screen and displays a stylized ASCII art banner.
    """
    os.system("clear")
    banner_text = """
DDD:::::DDDDD:::::D
D::::::::::::DDD
D:::::::::::::::DD
DDD:::::DDDDD:::::D
  D:::::D    D:::::Dyyyyyyy           yyyyyyynnnn  nnnnnnnn      aaaaaaa
  D:::::D     D:::::Dy:::::y         y:::::y n:::nn::::::::nn    a::::::::
  D:::::D     D:::::D y:::::y       y:::::y  n::::::::::::::nn   aaaaaaa::
  D:::::D     D:::::D  y:::::y     y:::::y   nn:::::::::::::::n         a:
  D:::::D     D:::::D   y:::::y   y:::::y      n:::::nnnn:::::n    aaaaaaa:
  D:::::D     D:::::D    y:::::y y:::::y       n::::n    n::::n  aa::::::::
  D:::::D     D:::::D     y:::::y:::::y        n::::n    n::::n a::::aaaa:::
  D:::::D    D:::::D       y:::::::::y         n::::n    n::::na::::a    a::
DDDD:::::DDDDD:::::D         y:::::::y          n::::n    n::::na::::a    a::
D:::::::::::::::DD           y:::::y           n::::n    n::::n a:::::aaaa:::
D::::::::::::DDD            y:::::y            n::::n    n::::n a::::::::::a
DDDDDDDDDDDDDDDDD          y:::::y             nnnnnn    nnnnnn  aaaaaaaaaa
                          y:::::y
                         y:::::y
                        y:::::y
                       y:::::y
                      yyyyyyy
MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM
MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM
MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMXONMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM
MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMl,; dMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM
MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMkdKMMMMNc,Wk oMMWWMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM
MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMd;d,'XMO.l,oMX'c,:.kMXWMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM
MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMNXM0,WM0.cXxcool0MO,dd.c',NWOOXMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM
MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMx ..;..KMWo.:Kx;;,cNMMM: lO.xocl'o'.;'oMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM
MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMx kN00KKoOMWx' :O'OllxNM0:xXc'';Wl. KWxol:KMMMMMMMMMMMNKKWMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM
MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMWMMMMM0;....,l:.:xKNOMX:;,. .lNMMMMWXxdooox0MMW:cWWMMMMMWd;okkxxkWMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMWMM
MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMWO;  xWkdxx0kNWMMMMWloNW0OWKl,OMM0;oKMMNd'dxocNMMMdxMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM
MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM0 oNd:;xol.xMMMMMX'xllO:;N',x,xMMMXxloo0Nc0x:XMMMM;xMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM
MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMNc:;lKMWl,XMMMMMM:cc,xclooKdxxWMMMMMMMMMWkONWXK0Oo.kMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM
MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM0.,WMMMMMMMMMMWX0Okkxdxolc:;;,''....  ,cl,.0MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM
MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM0 .WMMMMMNkl,..';;;:cllc.,d':'c0,c,Xx;k'Oo.NMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM
MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM; lMMMMW: :kNMMMMMMMMXkWWo:xNMkcNMK,:WNN::WMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM
MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMK' :XMM'.NMX:,,'',;:'.l.x0cl:kWdc,dMX,lcNMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM
MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMk. OMW :d,'KMMMMMWXKOkdlc;,,'..;,.,.,:,.NMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM
MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMX, .XMMMx:l0Wo.:'xN;xWMMMMMMMMNxxONMMMMMM;XMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM
MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMWo  lWMMMMMMWd.cNMN ,Ox.KM,l:OMM,cOxolllll:dMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM
MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMK. .KMMMMMMMO..XMMMMKWMMK.O;MW.ON NMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM
MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMWc  lWMMMMMMNc.  MMMMMMMMMM:cWMM,x;kMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM
MMMMMWMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMK. .KMMMMMMWk.cW: WMMMMMk::cd0WMOckWMMMMMMMMMMMMMMMMMMMMMMMMMWMMMMMMMMMMMMMMMMMMMMMMMMMMM
MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMx  :WMMMMMMN,.OMMl.MMN:'lx.KOd:.;kxollc'.....',:oxKWMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM
MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMc  kMMMMMMMO. ll;k;lMO.OMMK;XMMMM0ocdxOOkO00K0Oxd:'  'oXMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM
MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMW; .KMMMMMMMd 'NMMW;;WMOoOMMMMMMMMMMk.olloolcc::;cx0WMKd, .xNMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM
MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM; .XMMMMMMMo c.0MMMMMMl:xdXMMMMMxKMX.oMMMMMMMMMMWKo'.loOWWx' cNMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM
MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMl  XMMMMMMMx 0MK.0MMMMM'0MMWxWMMM:',.oMMMMMMMMMMMMMMMKcl. ;0MO. oMMMMMMMMMMMMMMMMMMMMMMMMMMMMM
MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMO  OMMMMMMMK cOKMk.MMMMMOolc'o,;'..lWOol.xMMMMNNWMMMMMMMMMNo .OMx .XMMMMMMMMMMMMMMMMMMMMMMMMMMM
MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMW. cMMMMMMMM, :xl'd XMMMMMMMMMMWWMMWd'oNK.Okl' ;:::ccxNMMMMMMx.;;WX. OMMMMMMMMMMMMMMMMMMMMMMMMMM
MMMMMMMMMMMMMMMMMMMMMMXll;,lxNMMMMMMMd .WMMMMMMMN lMMMMOoMMMMMMMMMMMMMMN.:WXl..:odl;.'oNMKc :WMMMMX.d:.WW, OMMMMMMMMMMMMMMMMMMMMMMMMM
MMMMMMMMMMMMMMMMMMMMMM0.;oO0o.oMMMMMM. xMMMMMMMM0 ;:;:kWMMMMMMMMMMMMMMM;,Mo.lNMMMMMMMk. ';KX0KMMMMMNx' :MW. KMMMMMMMMMMMMMMMMMMMMMMMM
MMMMMMMMMMMMMMMMMMMMMN.do:.;MW.0MMMMK .WMMMMMMMM0 kMMNd,dMMMMMMMMMMMMMM.:,'NMMMMMMMMMMW' cWMMMMMMMMMMM  WMX .MMMMMMMMMMMMMMMMMMMMMMMM
MMMMMMMMMMMMMMMMMMMMMMKc..'cMMK.dOkx, dMMMMMMMMMW..MM0dd.;MMMMMMMMX:oMM: ,WMMMMMMMMMMMMW. .,lXMMMMMMN:: XMM: kMMMMMMMMMMMMMMMMMMMMMMM
MMMMMMMMMMMMMMMMMMMMMMMk:xlckNWWOkxxkXMMMMMMMMMMMO o;:WMMNXXXWMMMk.k.dk..WMMMMMMWMMMMMMM0 :MO,cWMMMN dX NMMO ;MMMMMMMMMMMMMMMMMMMMWMW
MMMMMMMMMMMMMMMMMMMMMMMWc,,ll'WXcokNMMMMMMMMMMMMMMk..OOllcodo.cKK NMW0: 0MMMMMMNdc:dNMMMMl XMMd'WMMMd'd,MMMN .MMMMMMMMMMMMMMMMMMMMMMM
MMMMMMMMMMMMMMMMMMMMMMMMMMMMW.W0.Oo;.cKMMMMMMMMMMMMX,.;WMMMM.kMMc,MMMM.,MMMMMMo ;Ok. 0MMMW,.:'c.lMMWk,.xMMMX 'MMMMMMMMMMMMMMMMMMMMMMM
MMMMMMMMMMMMMMMMMMMMMMMMMMMMN kl;MMMN  oMMMMMMMMMMMMWk'.dNMM;,WMl.MMMk KMMMMMk ;MMMN. XMMMWc 'KXkl:xo.xMMMMx lMMMMMMMMMMMMMMMMMMMMMMM
MMMMMMMMMMMMMMMMMMMMMMMMMMMMMO;cNMMMMc  WMMMMMMMMMMMMMWx, 'lk:'dO :0l.kMMMMMM; xMMMMk 'WMMMMNd,  ,:;cXMMMMM. NMMMMMMMMMMMMMMMMMMMMMMM
MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMWc:,:oXN  cMMMMMMMMMMMMMMMMWkl,.   .':kWMMMMMMM. KMMMMMc ;WMMMMMMMWNWMMMMMMMc 0MMMMMMMMMMMMMMMMMMMMMMMM
MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMN,ckOl OO  kMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM  NMMMMMMl ,NMMMMMMMMMMMMMMX,.0MMMMMMMMMMMMMMMMMMMMMMMMM
MMMMMMMMMMMMMMMMMMMMMMMMMMMMMM0::. Mc,Mx  NMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMN  WMMMMMMMO..dWMMMMMMMMMMO; cWMMMMMMMMMMMMMMMMMMMMMMMMMM
MMMMMMMMMMMMMMMMMMMMMMMMMMMMMM;,xdoW0 NM'lMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMk .MMMMMMMMMWx, 'lxXMMMMMX ,NMMMMMMMMMMMMMMMMMMMMMMMMMMMM
MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMOo; OM,.,cMMWOWMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM, oMMMMMMMMMMMMW0xl:'c0MMMX,,KMMMMMMMMMMMMMMMMMMMMMMMMMMM
MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM'oMMXOWMx. .kMMMMMMMMMMMMMMMMMMMMMMMMMMMMd .WMMMMMMMMMMMMMMMMMMXc.OMMMx XMMMMMMMMMMMMMMMMMMMMMMMMMM
MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMN.KW,'ck,,Nd  '0MMMMMMMMMMMMMMMMMMMMMMMMWc .XMMMMMMMMMMMMMWOdoloo'cWMO::0MMMMMMMMMMMMMMMMMMMMMMMMMMM
MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM;OW,ONxcxMMMNl  .dNMMMMMMMMMMMMMMMMMMMKl  lWMMMMMMMMMMMMWc.dKKOxKMWWMkc:oXMMMMMMMMMMMMMMMMMMMMMMMMMM
MMMMMWMMMMMMMMMMMMMMMMMMMMMMMMMMMO,:KMMMMMMMMMMWk;  .:d0XWMMMMMMMMMMMW;  oWMMMMMMMMMMMMMM,,O;. 'c;.':;,kWO.0MMMMMMMMMMMMMMMMMMMMMMMMM
MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMKxc;.   ......':okKWNk;.0MMMMMMMMMMMMMo,;' xd.cNMMMWko;cNMMMMMMMMMMMMMMMMMMMMMMMMM
MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMWXKKKKXNNNKOl.XMo.XMMMMMMMMMMMMMMMMK:;oNMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM
MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMN::olld00NMK.,coKMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM
MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMk.Okl0k0O;;;;;;dk.lMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM
MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMxl'Odc:0.XMMMMWx;:KMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM
MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMkkOWooXMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM
MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM
                               """
    from rich import print as rprint

    rprint(Text.from_markup(f"[blue]{banner_text}[/blue]"))


def run_logcat_monitor(package_name: str) -> None:
    """
    Run the adb logcat command to monitor logs for the given package.

    Opens a new terminal window (if available) to monitor logs for the specified
    package, highlighting sensitive information like IPs, tokens, passwords, etc.

    Args:
        package_name: The Android package name to monitor logs for
    """

    ip_regex = (
        r"\\b(?:(?:25[0-5]|2[0-4]\\d|1\\d{2}|[1-9]?\\d)\\.){3}"
        r"(?:25[0-5]|2[0-4]\\d|1\\d{2}|[1-9]?\\d)\\b|"
        r"(?:\\b[A-F0-9]{1,4}(?:[A-F0-9]{1,4}:){5}[A-F0-9]{1,4}\\b))"
    )

    combined_regex = (
        f"({ip_regex})|token|key|password|db|database|" f"http://|https://|ip address"
    )

    cmd = (
        f"adb logcat | grep --line-buffered '{package_name}' "
        f"| tee log_output.txt | grep --line-buffered -E --color=always -i "
        f"'{combined_regex}'"
    )

    logging.info(
        "Starting logcat monitor. " "This will run in a separate terminal if available."
    )
    if shutil.which("xterm"):
        subprocess.Popen(
            ["xterm", "-geometry", "200x80+50+50", "-e", "bash", "-c", cmd],
            close_fds=True,
        )
    elif shutil.which("xfce4-terminal"):
        subprocess.Popen(["xfce4-terminal", "-e", f'bash -c "{cmd}"'], close_fds=True)
    elif shutil.which("gnome-terminal"):
        subprocess.Popen(
            [
                "gnome-terminal",
                "--geometry=100x40+50+50",
                "--",
                "bash",
                "-c",
                cmd,
            ],
            close_fds=True,
        )
    else:
        logging.warning(
            "No graphical terminal found. " "Running logcat monitor in the background."
        )
        subprocess.Popen(["bash", "-c", cmd], close_fds=True)

    logging.info("Log monitor started, continuing main script execution...")

'''
class OWASPTestSuiteDrozer:
    """
    Main test suite for OWASP Mobile Application Security Testing.

    This class manages the overall test process, including unpacking the APK,
    initializing analysis tools, running plugins, and generating reports.
    """

    def __init__(self, apk_path: str, package_name: str):
        """
        Initialize the test suite with APK and package information.

        Args:
            apk_path: Path to the APK file to analyze
            package_name: The package name of the Android application
        """
        self.apk_ctx = APKContext(apk_path_str=apk_path, package_name=package_name)
        drozer_helper = DrozerHelper(self.apk_ctx.device_id)
        self.apk_ctx.set_drozer_helper(drozer_helper)
        self.report_data: List[Tuple[str, Union[str, Text]]] = []
        self.report_generator = ReportGenerator(package_name, self.apk_ctx.scan_mode)
        self.report_formats: List[str] = ["txt"]  # Default to text, can be extended
        self.core_test_characteristics: Dict[str, Dict[str, str]] = {
            "extract_additional_info": {"mode": "safe"},
            "test_debuggable_logging": {"mode": "safe"},
        }

    def start_drozer(self) -> None:
        """
        Start the Drozer server for dynamic testing.

        Initializes the Drozer server connection needed for dynamic analysis.
        """
        if self.apk_ctx.drozer:
            self.apk_ctx.drozer.start_drozer()
        else:
            logging.error("DrozerHelper not initialized in APKContext.")

    def check_drozer_connection(self) -> bool:
        """
        Check if Drozer connection is active.

        Returns:
            bool: True if connection is successful, False otherwise
        """
        if self.apk_ctx.drozer:
            return self.apk_ctx.drozer.check_connection()
        logging.error("DrozerHelper not initialized in APKContext.")
        return False

    def unpack_apk(self) -> None:
        """
        Unpack the APK file for static analysis.

        Decompiles the APK using apktool and initializes the APKAnalyzer.
        Exits if the AndroidManifest.xml cannot be found after unpacking.
        """
        logging.info("Unpacking APK for analysis...")
        self.apk_ctx.decompiled_apk_dir.mkdir(parents=True, exist_ok=True)
        os.system(
            f"apktool d {self.apk_ctx.apk_path} -o "
            f"{self.apk_ctx.decompiled_apk_dir} -f"
        )
        if not self.apk_ctx.manifest_path.exists():
            logging.error("AndroidManifest.xml not found after unpacking.")
            logging.error(
                Text.from_markup(
                    "[red][!] AndroidManifest.xml not found after unpacking. "
                    "Exiting.[/red]"
                )
            )
            sys.exit(1)
        logging.info("APK unpacked successfully.")
        analyzer = APKAnalyzer(
            manifest_dir=str(self.apk_ctx.decompiled_apk_dir),
            decompiled_dir=str(self.apk_ctx.decompiled_apk_dir),
        )
        self.apk_ctx.set_apk_analyzer(analyzer)

    def add_report_section(self, title: str, content: Union[str, Text]) -> None:
        """
        Add a section to the report data.

        Args:
            title: The section title for the report
            content: The content to include in the section
        """
        self.report_data.append((title, content))
        self.report_generator.add_section(title, content)

    def run_plugins(self) -> None:
        """
        Dynamically load and run all plugins in the plugins directory.

        Discovers and executes all available plugins based on the current scan mode.
        Plugins are only run if they match the scan mode (safe or deep).
        Results from each plugin are added to the report.
        """
        package = "plugins"
        plugin_modules_to_run = []
        for _, module_name, _ in pkgutil.iter_modules([package]):
            try:
                module = importlib.import_module(f"{package}.{module_name}")
                if hasattr(module, "run"):
                    plugin_mode = "safe"
                    if hasattr(module, "PLUGIN_CHARACTERISTICS") and (
                        isinstance(module.PLUGIN_CHARACTERISTICS, dict)
                    ):
                        plugin_mode = module.PLUGIN_CHARACTERISTICS.get("mode", "safe")
                    if self.apk_ctx.scan_mode == "deep" or plugin_mode == "safe":
                        plugin_modules_to_run.append((module_name, module, plugin_mode))
                    else:
                        logging.info(
                            Text.from_markup(
                                f"[yellow]Skip plugin (safe): {module_name} "
                                f"(mode: {plugin_mode})[/yellow]"
                            )
                        )
            except Exception as e:
                logging.error(
                    f"Failed to load plugin {module_name}: {Text(str(e))}",
                    exc_info=True,
                )
        if not plugin_modules_to_run:
            logging.info("No plugins to run based on scan mode or availability.")
            return
        with Progress(transient=True) as progress_bar:
            task = progress_bar.add_task(
                "[cyan]Running Plugins...[/cyan]",
                total=len(plugin_modules_to_run),
            )
            for module_name, module, plugin_mode in plugin_modules_to_run:
                progress_bar.update(
                    task,
                    description=(
                        f"[cyan]Plugin:[/cyan] [bold magenta]{module_name}"
                        f"[/bold magenta] ({plugin_mode})"
                    ),
                )
                try:
                    title, result = module.run(self.apk_ctx)
                    self.add_report_section(title, result)
                    logging.info(
                        Text.from_markup(
                            f"[bold]Results: {module_name} ({title}):[/bold]"
                        )
                    )
                    if result:
                        if isinstance(result, str):
                            logging.info(Text(result))
                        else:
                            logging.info(result)
                except Exception as e:
                    logging.error(
                        f"Failed to run plugin {module_name}: {Text(str(e))}",
                        exc_info=True,
                    )
                    self.add_report_section(
                        f"Error with plugin: {module_name}",
                        Text.from_markup(f"[red]Failed to run: {Text(str(e))}[/red]"),
                    )
                progress_bar.advance(task)

    def attack_surface_analysis(self) -> None:
        """
        Perform an attack surface analysis on the application.

        Analyzes the application's exposed components (activities, services,
        broadcast receivers, content providers) to identify potential attack vectors.
        Results are added to the report.
        """
        logging.info("Performing In-Depth Attack Surface Analysis...")
        commands = [
            f"run app.activity.info -a {self.apk_ctx.package_name}",
            f"run app.service.info -a {self.apk_ctx.package_name}",
            f"run app.broadcast.info -a {self.apk_ctx.package_name}",
            f"run app.provider.info -a {self.apk_ctx.package_name}",
            f"run app.package.attacksurface " f"{self.apk_ctx.package_name}",
        ]
        results = []
        for cmd in commands:
            output = self.apk_ctx.drozer.run_command(cmd)
            logging.info(output)
            results.append(output)
        self.add_report_section("Attack Surface Analysis", "\n".join(results))

    def traversal_vulnerabilities(self) -> None:
        """
        Test content providers for path traversal vulnerabilities.

        Checks if the application's content providers allow unauthorized
        access to files or data through path traversal techniques.
        Results are added to the report.
        """
        logging.info("Testing Content Providers for Traversal Vulns...")
        content_providers = self.apk_ctx.drozer.run_command(
            f"run scanner.provider.traversal -a {self.apk_ctx.package_name}"
        )
        logging.info(content_providers)
        self.add_report_section("Traversal Vulnerabilities", content_providers)

    def injection_vulnerabilities(self) -> None:
        """
        Test content providers for SQL injection vulnerabilities.

        Checks if the application's content providers are susceptible to
        SQL injection attacks. Results are added to the report.
        """
        logging.info("Testing Content Providers for basic SQL Injection Vulns...")
        content_providers = self.apk_ctx.drozer.run_command(
            f"run scanner.provider.injection -a {self.apk_ctx.package_name}"
        )
        logging.info(content_providers)
        self.add_report_section("Injection Vulnerabilities", content_providers)

    def extract_additional_info(self) -> None:
        """
        Extract additional information from the APK.

        Retrieves certificate details, permissions, native libraries,
        and custom permissions from the analyzed APK.
        Results are added to the report.
        """
        test_type = "APK Information Extraction"
        report_content = {
            "Test Description": (
                "Extracts additional information from the APK such as "
                "certificate details, permissions, and native libraries."
            ),
            "Results": [],
            "Status": "INFO",
        }
        try:
            if not self.apk_ctx.analyzer:
                logging.warning(
                    "APKAnalyzer not initialized. Skipping info extraction."
                )
                report_content["Results"].append(
                    {"Warning": "APKAnalyzer not available."}
                )
            else:
                cert_details = self.apk_ctx.analyzer.get_certificate_details()
                if cert_details:
                    report_content["Results"].append(
                        {"Certificate Details": cert_details}
                    )
                    logging.info(f"Certificate Details: {cert_details}")
                permissions = self.apk_ctx.analyzer.get_permissions()
                if permissions:
                    report_content["Results"].append({"Permissions": permissions})
                    logging.info(f"Permissions: {permissions}")
                native_libs = self.apk_ctx.analyzer.get_native_libraries()
                if native_libs:
                    report_content["Results"].append({"Native Libraries": native_libs})
                    logging.info(f"Native Libraries: {native_libs}")
                custom_perms = [
                    p
                    for p in permissions
                    if p.startswith(str(self.apk_ctx.package_name))
                ]
                if custom_perms:
                    report_content["Results"].append(
                        {"Custom Permissions": custom_perms}
                    )
                    logging.info(f"Custom Permissions Found: {custom_perms}")
        except Exception as e:
            error_msg = f"Error extracting APK info: {Text(str(e))}"
            logging.error(error_msg, exc_info=True)
            report_content["Results"].append({"Error": error_msg})
            report_content["Status"] = "ERROR"
        self.add_report_section(test_type, report_content)

    def test_debuggable_logging(self) -> None:
        """
        Check if the application is debuggable and analyze logging.

        Verifies whether the application is configured as debuggable in the manifest,
        which is a security risk for production apps. Also provides information
        about logging practices.
        Results are added to the report.
        """
        test_type = "Debuggable and Logging Checks"
        report_content = {
            "Test Description": (
                "Checks if the application is debuggable and looks for "
                "excessive logging."
            ),
            "Results": [],
            "Status": "PASS",
        }
        try:
            if not self.apk_ctx.analyzer:
                logging.warning(
                    "APKAnalyzer not initialized. Skipping debuggable check."
                )
                report_content["Results"].append(
                    {"Warning": "APKAnalyzer not available for check."}
                )
            elif self.apk_ctx.analyzer.is_debuggable():
                report_content["Results"].append(
                    {"Finding": "Application is debuggable."}
                )
                report_content["Status"] = "FAIL"
                logging.warning(
                    Text.from_markup(
                        "[yellow]Application is debuggable. "
                        "Should be false for release builds.[/yellow]"
                    )
                )
            else:
                report_content["Results"].append(
                    {"Finding": "Application is not debuggable."}
                )
                logging.info("Application is not debuggable.")
            report_content["Results"].append(
                {
                    "Logging Check": (
                        "Manual review of logcat output (log_output.txt) "
                        "is recommended for sensitive info disclosure."
                    )
                }
            )
            logging.info("Review logcat output in 'log_output.txt' for sensitive data.")
        except Exception as e:
            error_msg = f"Error during debuggable/logging checks: {Text(str(e))}"
            logging.error(error_msg, exc_info=True)
            report_content["Results"].append({"Error": error_msg})
            report_content["Status"] = "ERROR"
        self.add_report_section(test_type, report_content)

    def set_report_formats(self, formats: List[str]) -> None:
        """
        Set the output formats for report generation.

        Args:
            formats: List of format strings ('txt', 'html', 'json', 'csv', 'all')
        """
        valid_formats = {"txt", "html", "json", "csv", "all"}
        self.report_formats = [fmt for fmt in formats if fmt in valid_formats]
        if not self.report_formats:
            self.report_formats = ["txt"]  # Default fallback
        logging.info(f"Report formats set to: {', '.join(self.report_formats)}")

    def generate_report(self) -> None:
        """
        Generate reports in multiple formats using the ReportGenerator.

        Creates reports in the specified formats (text, HTML, JSON, CSV) with
        comprehensive formatting and analysis of scan results.
        """
        logging.info("Generating reports in multiple formats...")

        # Update report generator with current scan mode
        self.report_generator.scan_mode = self.apk_ctx.scan_mode
        self.report_generator.add_metadata("apk_path", str(self.apk_ctx.apk_path))
        self.report_generator.add_metadata("total_tests_run", len(self.report_data))

        # Generate text report (legacy compatibility)
        if "txt" in self.report_formats:
            report_str = "OWASP MASVS Test Report\n"
            report_str += "=========================\n\n"
            for title, content in self.report_data:
                report_str += f"## {title}\n"
                if isinstance(content, dict):
                    for key, value in content.items():
                        report_str += f"  {key}: {value}\n"
                else:
                    report_str += f"  {content}\n"
                report_str += "\n"
            report_filename = f"{self.apk_ctx.package_name}_report.txt"
            with open(report_filename, "w") as f:
                f.write(report_str)
            logging.info(f"Text report generated: {report_filename}")

        # Generate enhanced reports using ReportGenerator
        try:
            if any(
                fmt in self.report_formats for fmt in ["html", "json", "csv", "all"]
            ):
                if "all" in self.report_formats:
                    # Generate all formats
                    output_files = self.report_generator.generate_all_formats()
                    for format_name, file_path in output_files.items():
                        logging.info(
                            f"Enhanced {format_name.upper()} report generated: {file_path}"
                        )
                else:
                    # Generate specific formats
                    if "html" in self.report_formats:
                        html_filename = (
                            f"{self.apk_ctx.package_name}_security_report.html"
                        )
                        self.report_generator.generate_html(Path(html_filename))
                        logging.info(f"HTML report generated: {html_filename}")

                    if "json" in self.report_formats:
                        json_filename = (
                            f"{self.apk_ctx.package_name}_security_report.json"
                        )
                        self.report_generator.generate_json(Path(json_filename))
                        logging.info(f"JSON report generated: {json_filename}")

                    if "csv" in self.report_formats:
                        csv_filename = (
                            f"{self.apk_ctx.package_name}_security_report.csv"
                        )
                        self.report_generator.generate_csv(Path(csv_filename))
                        logging.info(f"CSV report generated: {csv_filename}")

        except Exception as e:
            logging.error(f"Error generating enhanced reports: {e}")
            logging.info("Falling back to text-only report generation.")

        logging.info("Report generation completed.")

    def get_result(self, device_id: str) -> str:
        url = f"http://127.0.0.1:5000/api/get_result/{device_id}"
        return requests.get(url).json().get("result", "")

    def full_test_suite(self) -> None:
        """
        Run the complete test suite on the application.

        Executes all tests in a sequence, including starting Drozer,
        unpacking the APK, monitoring logs, running plugins,
        and executing core tests. Finally generates a report.
        Exits the program if critical elements like Drozer fail.
        """
        print_banner()
        logging.info(f"Starting OWASP MASVS Test Suite for {self.apk_ctx.apk_path}")
        logging.info(f"Package Name: {self.apk_ctx.package_name}")
        logging.info(f"Scan Mode: {self.apk_ctx.scan_mode}")
        self.start_drozer()
        if not self.check_drozer_connection():
            logging.error(
                Text.from_markup(
                    "[red][!] Drozer connection failed. "
                    "Ensure Drozer server and agent are running.[/red]"
                )
            )
            sys.exit(1)
        self.unpack_apk()
        if self.apk_ctx.scan_mode == "deep":
            run_logcat_monitor(str(self.apk_ctx.package_name))
        self.run_plugins()
        core_methods_to_run = []
        for method_name, characteristics in self.core_test_characteristics.items():
            method = getattr(self, method_name, None)
            if method and callable(method):
                mode = characteristics.get("mode", "safe")
                if self.apk_ctx.scan_mode == "deep" or mode == "safe":
                    core_methods_to_run.append((method_name, method, mode))
                else:
                    logging.info(
                        Text.from_markup(
                            f"[yellow]Skipping core test (safe mode): "
                            f"{method_name} (mode: {mode})[/yellow]"
                        )
                    )
        if core_methods_to_run:
            with Progress(transient=True) as progress_bar:
                task = progress_bar.add_task(
                    "[cyan]Running Core Tests...[/cyan]",
                    total=len(core_methods_to_run),
                )
                for method_name, method_func, mode in core_methods_to_run:
                    progress_bar.update(
                        task,
                        description=(
                            f"[cyan]Test:[/cyan] [bold]{method_name[:8]}"
                            f"[/bold] ({mode})"
                        ),
                    )
                    try:
                        logging.info(f"Executing core test: {method_name} ({mode})")
                        method_func()
                    except Exception as e:
                        error = f"Error in {method_name}: {e}"
                        logging.error(error, exc_info=True)
                        self.add_report_section(
                            f"Error in test: {method_name}",
                            Text.from_markup(f"[red]{error}[/red]"),
                        )
                    progress_bar.advance(task)
        # Generated formatted report
        self.generate_report()
        logging.info("Test suite completed.")
        logging.info(
            Text.from_markup(
                "[green]=============================================[/green]"
            )
        )
        logging.info(
            Text.from_markup(
                f"[green]✓ Tests completed for {self.apk_ctx.package_name}[/green]"
            )
        )
        logging.info(
            Text.from_markup(
                "[green]=============================================[/green]"
            )
        )
'''

class OWASPTestSuiteAgent:
    def __init__(self, apk_path: str, package_name: str, device_id: str):
        self.apk_ctx = APKContext(apk_path_str=apk_path, package_name=package_name)
        self.device_id = device_id
        self.report_data: List[Tuple[str, Union[str, Text]]] = []
        self.report_generator = ReportGenerator(package_name, self.apk_ctx.scan_mode)
        self.report_formats: List[str] = ["txt"]

    def unpack_apk(self) -> None:
        logging.info("Unpacking APK for analysis...")
        self.apk_ctx.decompiled_apk_dir.mkdir(parents=True, exist_ok=True)
        os.system(
            f"apktool d {self.apk_ctx.apk_path} -o {self.apk_ctx.decompiled_apk_dir} -f"
        )
        if not self.apk_ctx.manifest_path.exists():
            logging.error("AndroidManifest.xml not found after unpacking.")
            sys.exit(1)
        logging.info("APK unpacked successfully.")
        analyzer = APKAnalyzer(
            manifest_dir=str(self.apk_ctx.decompiled_apk_dir),
            decompiled_dir=str(self.apk_ctx.decompiled_apk_dir),
        )
        self.apk_ctx.set_apk_analyzer(analyzer)

    def add_report_section(self, title: str, content: Union[str, Text]) -> None:
        self.report_data.append((title, content))
        self.report_generator.add_section(title, content)

    def get_result(self) -> str:
        url = f"http://127.0.0.1:5000/api/get_result/{self.device_id}"
        try:
            return requests.get(url).json().get("result", "")
        except Exception as e:
            logging.error(f"Failed to fetch result from agent: {e}")
            return "Error fetching result."

    def run_plugins(self) -> None:
        plugin_dir = "morph_server/modules"
        sys.path.insert(0, os.path.abspath("morph_server"))  # Allow importing as modules.*
        plugin_modules_to_run = []
        for _, module_name, _ in pkgutil.iter_modules([plugin_dir]):
            try:
                module = importlib.import_module(f"modules.{module_name}")
                if hasattr(module, "run"):
                    plugin_modules_to_run.append((module_name, module))
            except Exception as e:
                logging.error(f"Failed to load plugin {module_name}: {e}", exc_info=True)

        if not plugin_modules_to_run:
            logging.info("No plugins to run.")
            return

        with Progress(transient=True) as progress_bar:
            task = progress_bar.add_task("[cyan]Running Plugins...[/cyan]", total=len(plugin_modules_to_run))
            for module_name, module in plugin_modules_to_run:
                progress_bar.update(task, description=f"[cyan]Plugin:[/cyan] [bold magenta]{module_name}[/bold magenta]")
                try:
                    command_obj = module.generate_command(self.apk_ctx.package_name)
                    command = command_obj["cmd"]
                    args = command_obj.get("args", {})
                    from core.agent_helper import send_command
                    send_command(self.device_id, command, args)
                    result = self.get_result()
                    self.add_report_section(module_name.replace("_", " ").title(), result)
                except Exception as e:
                    logging.error(f"Failed to run plugin {module_name}: {e}", exc_info=True)
                    self.add_report_section(f"Error with plugin: {module_name}", f"Exception: {e}")
                progress_bar.advance(task)

    def run_agent_command(self, title: str, command: str, args: dict = {}) -> None:
        send_command(self.device_id, command, args)
        logging.info(f"Sent agent command: {command}, waiting for result...")
        result = self.get_result()
        self.add_report_section(title, result)

    def generate_report(self) -> None:
        logging.info("Generating reports...")
        self.report_generator.scan_mode = self.apk_ctx.scan_mode
        self.report_generator.add_metadata("apk_path", str(self.apk_ctx.apk_path))
        self.report_generator.add_metadata("total_tests_run", len(self.report_data))

        if "txt" in self.report_formats:
            report_str = "OWASP MASVS Test Report\n==========================\n\n"
            for title, content in self.report_data:
                report_str += f"## {title}\n"
                report_str += f"  {content}\n\n"
            report_filename = f"{self.apk_ctx.package_name}_report.txt"
            with open(report_filename, "w") as f:
                f.write(report_str)
            logging.info(f"Text report generated: {report_filename}")

    def full_test_suite(self) -> None:
        logging.info(f"Starting OWASP MASVS Test Suite for {self.apk_ctx.apk_path}")
        self.unpack_apk()
        self.run_plugins()
        self.run_agent_command("Attack Surface Analysis", "attack_surface", {"package": self.apk_ctx.package_name})
        self.run_agent_command("SQL Injection Checks", "sql_injection", {"package": self.apk_ctx.package_name})
        self.run_agent_command("Traversal Vulnerabilities", "uri_traversal", {"package": self.apk_ctx.package_name})
        self.generate_report()

def main() -> None:
    """
    Main entry point for the application.

    Parses command-line arguments, sets up the test environment,
    and runs the OWASP Mobile Application Security Test Suite.
    """
    parser = argparse.ArgumentParser(
        description="Mobile Application Security Verification Standard Testing Tool",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--apk", type=str, required=True, help="Path to the APK file for testing"
    )
    parser.add_argument(
        "--pkg", type=str, required=True, help="Package name of the application"
    )
    parser.add_argument(
        "--device", type=str, help="Emulated Device ID"
    )
    parser.add_argument(
        "--mode",
        choices=["safe", "deep"],
        default="safe",
        help="Safe mode only runs non-destructive tests",
    )
    parser.add_argument(
        "--skip",
        nargs="+",
        type=str,
        default=[],
        help="List of tests to skip (by name)",
    )
    parser.add_argument(
        "--formats",
        nargs="+",
        type=str,
        default=[],
        help="List of formats to generate (txt, html, json, csv, all)",
    )
    args = parser.parse_args()
    suite = OWASPTestSuiteAgent(args.apk, args.pkg)
    suite.apk_ctx.set_scan_mode(args.mode)
    suite.set_report_formats(args.formats)
    suite.full_test_suite()


if __name__ == "__main__":
    main()
