#!/usr/bin/env python3
"""
AODS - Automated OWASP Dynamic Scan Framework

Enhanced with Phase 1 Priority 2: Parallel Plugin Execution Engine
Provides 3-5x speed improvement through intelligent dependency-aware parallel execution.

This framework is a comprehensive mobile application security testing suite that
combines static analysis, dynamic analysis, and automated vulnerability detection.
"""

import argparse
import logging
import os
import shutil
import subprocess
import sys
import uuid
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union

from rich.logging import RichHandler
from rich.text import Text

from core.analyzer import APKAnalyzer
from core.apk_ctx import APKContext
from core.output_manager import OutputLevel, get_output_manager
# ADDED: Import parallel execution engine
from core.parallel_analysis_engine import (
    ExecutionMode, ParallelAnalysisEngine, create_parallel_engine,
    enhance_plugin_manager_with_parallel_execution)
from core.plugin_manager import create_plugin_manager
from core.progressive_analyzer import ProgressiveAnalyzer
from core.report_generator import ReportGenerator

# Import device helpers only if available
try:
    from devices.adb_helper import ADBHelper
except ImportError:
    ADBHelper = None

try:
    # ENHANCED: Try to import MobileMorphAgentBridge first (preferred)
    from core.mobilemorph_bridge import MobileMorphAgentBridge as DrozerHelper
    USING_AGENT_BRIDGE = True
    logging.info("Using MobileMorphAgentBridge for dynamic analysis")
except ImportError:
    # Fallback to legacy DrozerHelper
    try:
        from core.drozer_helper import DrozerHelper
        USING_AGENT_BRIDGE = False
        logging.info("Using legacy DrozerHelper")
    except ImportError:
        # Create a mock DrozerHelper for testing
        USING_AGENT_BRIDGE = False
        logging.warning("No dynamic analysis helper available - using mock")
        class DrozerHelper:
            def __init__(self, package_name):
                self.package_name = package_name

            def start_drozer(self):
                return False

            def check_connection(self):
                return False

            def get_connection_status(self):
                return {"last_error": "Drozer not available"}

            def run_command_safe(self, cmd, fallback_msg):
                return fallback_msg

            # ADDED: Missing run_command method that plugins are calling
            def run_command(self, cmd):
                """Mock run_command method for when Drozer is not available."""
                raise Exception("Drozer not available - dynamic analysis limited")


try:
    from devices.frida_helper import FridaHelper
except ImportError:
    FridaHelper = None

from rich.text import Text

# Import dynamic analysis
try:
    from core.dynamic_log_analyzer import DynamicAnalysisResult
except ImportError:
    DynamicAnalysisResult = None

# Configure RichHandler for logging
logging.basicConfig(
    level=logging.INFO,
    handlers=[RichHandler(rich_tracebacks=True, show_path=False, show_level=True)],
)


def print_banner() -> None:
    """
    Print the application banner to the console.
    Uses the new OutputManager for clean, professional output.
    """
    banner = """
 █████   ██████  ██████  ███████
██   ██ ██    ██ ██   ██ ██
███████ ██    ██ ██   ██ ███████
██   ██ ██    ██ ██   ██      ██
██   ██  ██████  ██████  ███████

Automated OWASP Dynamic Scan Framework
Enterprise Edition with Parallel Execution Engine

📊 Phase 1 Priority 2: 3-5x Speed Improvement Ready
🚀 Dependency-aware parallel plugin execution
💾 Memory-optimized processing (>500MB APKs)
🔧 Adaptive resource management
    """
    print(banner)


def run_dynamic_log_analysis(
    package_name: str, duration_seconds: int = 180, enterprise_mode: bool = False
) -> Optional[DynamicAnalysisResult]:
    """
    Run enterprise-scale dynamic log analysis instead of basic logcat monitoring.

    Captures and analyzes logcat output for security events including:
    - Intent fuzzing responses
    - Service access attempts
    - Authentication component exposure
    - Privilege escalation attempts
    - Debug interface discovery

    Args:
        package_name: The Android package name to monitor
        duration_seconds: How long to capture logs (default: 3 minutes)
        enterprise_mode: Enable enterprise-scale analysis features

    Returns:
        DynamicAnalysisResult: Comprehensive analysis results or None if failed
    """
    output_mgr = get_output_manager()
    output_mgr.status("Starting enterprise dynamic log analysis...", "info")

    # Configure analyzer for enterprise or standard mode
    config = {
        "capture_timeout_seconds": duration_seconds,
        "real_time_analysis": True,
        "max_events_per_type": 200 if enterprise_mode else 50,
        "memory_limit_mb": 512 if enterprise_mode else 256,
        "batch_processing_size": 100 if enterprise_mode else 50,
        "detailed_reporting": enterprise_mode,
        "export_json": True,
    }

    try:
        # Create and start dynamic log analyzer
        analyzer = create_dynamic_log_analyzer(package_name, config)
        analyzer.start_capture(timeout_seconds=duration_seconds)

        output_mgr.status(
            f"🔍 Monitoring dynamic behavior for {duration_seconds} seconds...", "info"
        )
        output_mgr.status(
            "🎯 Analyzing intent fuzzing, service discovery, and authentication flows...",
            "info",
        )

        # Wait for analysis to complete
        import time

        time.sleep(duration_seconds)

        # Stop analysis and get results
        results = analyzer.stop_capture()

        # Display summary
        output_mgr.success(f"✅ Dynamic analysis completed!")
        output_mgr.info(f"📊 Total Security Events: {results.total_events}")

        if results.total_events > 0:
            # Display event breakdown
            output_mgr.info("🔍 Event Summary:")
            for severity, count in results.events_by_severity.items():
                severity_color = {
                    "CRITICAL": "red",
                    "HIGH": "orange1",
                    "MEDIUM": "yellow",
                    "LOW": "blue",
                    "INFO": "green",
                }.get(severity.value, "white")

                output_mgr.console.print(
                    f"  {severity.value}: {count} events", style=severity_color
                )

            # Display security assessment
            output_mgr.info("🛡️ Security Assessment:")
            for assessment_name, assessment_data in [
                ("Intent Fuzzing", results.intent_fuzzing_results),
                ("Service Access", results.service_access_results),
                ("Authentication", results.authentication_analysis),
            ]:
                if "security_assessment" in assessment_data:
                    output_mgr.console.print(
                        f"  {assessment_name}: {assessment_data['security_assessment']}"
                    )

        # Export detailed results
        if config["export_json"]:
            results_path = Path(
                f"dynamic_analysis_{package_name.replace('.', '_')}.json"
            )
            analyzer.export_results(results_path, format="json")
            output_mgr.success(f"📄 Detailed results exported to {results_path}")

        return results

    except Exception as e:
        output_mgr.error(f"❌ Dynamic log analysis failed: {e}")
        logging.exception("Dynamic log analysis error")
        return None


class OWASPTestSuiteDrozer:
    """
    Main test suite for OWASP Mobile Application Security Testing.

    This class manages the overall test process, including unpacking the APK,
    initializing analysis tools, running plugins, and generating reports.
    """

    def __init__(
        self,
        apk_path: str,
        package_name: str,
        enable_parallel: bool = True,
        enable_optimized: bool = False,
        agent_device_id: str = None,
        agent_server_url: str = "http://127.0.0.1:5000",
    ):
        """
        Initialize the test suite with APK and package information.

        Args:
            apk_path: Path to the APK file to analyze
            package_name: The package name of the Android application
            enable_parallel: Enable parallel plugin execution (default: True)
            enable_optimized: Enable advanced optimized execution (default: False)
            agent_device_id: Device ID for MobileMorphAgent connection (optional)
            agent_server_url: Flask server URL for agent communication (default: http://127.0.0.1:5000)
        """
        self.apk_ctx = APKContext(apk_path_str=apk_path, package_name=package_name)

        # Initialize DrozerHelper/AgentBridge based on availability and configuration
        if USING_AGENT_BRIDGE and agent_device_id:
            drozer_helper = DrozerHelper(agent_device_id, self.apk_ctx.package_name, agent_server_url)
            logging.info(f"Initialized MobileMorphAgentBridge for device {agent_device_id}")
        else:
            drozer_helper = DrozerHelper(self.apk_ctx.package_name)
            if agent_device_id:
                logging.warning("MobileMorphAgentBridge not available, falling back to legacy Drozer")

        self.apk_ctx.set_drozer_helper(drozer_helper)
        self.report_data: List[Tuple[str, Union[str, Text]]] = []
        self.report_generator = ReportGenerator(package_name, self.apk_ctx.scan_mode)
        self.report_formats: List[str] = ["txt"]  # Default to text, can be extended
        self.core_test_characteristics: Dict[str, Dict[str, str]] = {
            "extract_additional_info": {"mode": "safe"},
            "test_debuggable_logging": {"mode": "safe"},
            "platform_01_cleartext_traffic": {"mode": "safe"},
        }

        # Initialize the unified plugin manager
        self.plugin_manager = create_plugin_manager(self.apk_ctx.scan_mode)

        # ENHANCED: Initialize parallel execution engine
        self.enable_parallel = enable_parallel
        self.enable_optimized = enable_optimized
        self.parallel_engine = None

        if enable_parallel:
            # Auto-detect optimal worker count based on system resources
            import psutil

            cpu_count = psutil.cpu_count()
            memory_gb = psutil.virtual_memory().total / (1024**3)

            # Optimize worker count based on system resources
            if memory_gb >= 16 and cpu_count >= 8:
                max_workers = min(8, cpu_count)  # High-end system
                execution_mode = ExecutionMode.ADAPTIVE
            elif memory_gb >= 8 and cpu_count >= 4:
                max_workers = min(4, cpu_count)  # Mid-range system
                execution_mode = ExecutionMode.ADAPTIVE
            else:
                max_workers = 2  # Conservative for lower-end systems
                execution_mode = ExecutionMode.ADAPTIVE

            # Override with optimized mode if requested
            if enable_optimized:
                execution_mode = ExecutionMode.OPTIMIZED
                # For optimized mode, allow more workers since they're distributed across specialized pools
                max_workers = min(12, cpu_count + 2)

            # Create parallel engine
            self.parallel_engine = create_parallel_engine(
                max_workers=max_workers,
                memory_limit_gb=min(
                    memory_gb * 0.7, 8.0
                ),  # Use 70% of available memory, max 8GB
                execution_mode=execution_mode,
            )

            # Enhance plugin manager with parallel execution
            self.plugin_manager = enhance_plugin_manager_with_parallel_execution(
                self.plugin_manager, self.parallel_engine
            )

            output_mgr = get_output_manager()

            if enable_optimized:
                output_mgr.status(
                    f"Advanced optimized execution enabled: {max_workers} total workers across "
                    f"{len(self.parallel_engine.advanced_scheduler.worker_pools)} specialized pools, "
                    f"{memory_gb:.1f}GB memory available",
                    "info",
                )
            else:
                output_mgr.status(
                    f"Parallel execution enabled: {max_workers} workers, "
                    f"{memory_gb:.1f}GB memory available",
                    "info",
                )

        # Enterprise analysis attributes
        self.progressive_analyzer = None
        self.specific_plugins = []
        self.benchmarking_enabled = False

        # Dynamic analysis results storage
        self.dynamic_analysis_results: Optional[DynamicAnalysisResult] = None

    def start_drozer(self) -> bool:
        """
        Start the Drozer server for dynamic testing with enhanced error handling.

        Initializes the Drozer server connection needed for dynamic analysis.
        Uses graceful degradation instead of hard exits when Drozer fails.

        Returns:
            bool: True if Drozer started successfully, False otherwise
        """
        if self.apk_ctx.drozer:
            return self.apk_ctx.drozer.start_drozer()
        else:
            logging.error("DrozerHelper not initialized in APKContext.")
            return False

    def check_drozer_connection(self) -> bool:
        """
        Check if Drozer connection is active with enhanced status reporting.

        Returns:
            bool: True if connected, False otherwise
        """
        if self.apk_ctx.drozer:
            connected = self.apk_ctx.drozer.check_connection()
            if not connected:
                status = self.apk_ctx.drozer.get_connection_status()
                logging.warning(f"Drozer connection failed: {status['last_error']}")
            return connected
        else:
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
        Execute all plugins using enhanced parallel execution system.

        ENHANCED: Now uses parallel plugin execution engine for 3-5x speed improvement
        with intelligent dependency management and memory optimization.
        """
        output_mgr = get_output_manager()

        # Validate plugin integration
        if not self.plugin_manager.validate_integration():
            output_mgr.warning("Some advanced plugins may not be available")

        # Enhanced execution with parallel capabilities
        if self.enable_parallel and self.parallel_engine:
            output_mgr.section_header(
                "Parallel Plugin Execution",
                f"Running plugins with {self.parallel_engine.max_workers} workers",
            )

            # Track execution time for performance metrics
            import time

            start_time = time.time()

            # Execute all plugins with parallel engine
            plugin_results = self.plugin_manager.execute_all_plugins(self.apk_ctx)

            execution_time = time.time() - start_time

            # Display performance metrics
            if hasattr(self.plugin_manager, "_parallel_engine"):
                stats = self.parallel_engine.get_execution_statistics()
                output_mgr.status(
                    f"Parallel execution completed in {execution_time:.1f}s "
                    f"(efficiency: {stats.parallel_efficiency:.1%})",
                    "success",
                )
        else:
            output_mgr.section_header(
                "Sequential Plugin Execution", "Running plugins in sequential mode"
            )
            # Fallback to sequential execution
            plugin_results = self.plugin_manager.execute_all_plugins(self.apk_ctx)

        # Add plugin results to report
        for plugin_name, (title, content) in plugin_results.items():
            self.add_report_section(title, content)

        # Display plugin execution summary
        summary_table = self.plugin_manager.generate_plugin_summary()
        output_mgr.console.print(summary_table)

        # Display MASVS coverage
        masvs_coverage = self.plugin_manager.get_masvs_coverage()
        output_mgr.status(f"MASVS Controls Covered: {len(masvs_coverage)}", "info")

    def attack_surface_analysis(self) -> None:
        """
        Analyze the attack surface of the application.

        Identifies exported activities, services, and content providers
        that could be potential entry points for attackers.
        Results are added to the report.
        """
        logging.info("Analyzing Attack Surface...")
        commands = [
            f"run app.provider.info -a {self.apk_ctx.package_name}",
            f"run app.package.attacksurface " f"{self.apk_ctx.package_name}",
        ]
        results = []
        for cmd in commands:
            try:
                output = self.apk_ctx.drozer.run_command_safe(
                    cmd, f"Attack surface command temporarily unavailable: {cmd}"
                )
                logging.info("Attack surface command completed")
                results.append(output)
            except Exception as e:
                error_msg = f"Error executing attack surface command '{cmd}': {e}"
                logging.error(error_msg)
                results.append(f"Analysis temporarily unavailable: {error_msg}")

        self.add_report_section("Attack Surface Analysis", "\n".join(results))

    def traversal_vulnerabilities(self) -> None:
        """
        Test content providers for path traversal vulnerabilities.

        Checks if the application's content providers allow unauthorized
        access to files or data through path traversal techniques.
        Results are added to the report.
        """
        logging.info("Testing Content Providers for Traversal Vulns...")
        try:
            content_providers = self.apk_ctx.drozer.run_command_safe(
                f"run scanner.provider.traversal -a {self.apk_ctx.package_name}",
                "Path traversal analysis temporarily unavailable - Drozer connection issue",
            )
            logging.info("Path traversal scan completed")
            self.add_report_section("Path Traversal Vulnerabilities", content_providers)
        except Exception as e:
            error_msg = f"Error during traversal vulnerability scan: {e}"
            logging.error(error_msg)
            self.add_report_section(
                "Path Traversal Vulnerabilities",
                f"Analysis temporarily unavailable: {error_msg}",
            )

    def injection_vulnerabilities(self) -> None:
        """
        Test content providers for SQL injection vulnerabilities.

        Checks if the application's content providers are susceptible to
        SQL injection attacks. Results are added to the report.
        """
        logging.info("Testing Content Providers for basic SQL Injection Vulns...")
        try:
            content_providers = self.apk_ctx.drozer.run_command_safe(
                f"run scanner.provider.injection -a {self.apk_ctx.package_name}",
                "SQL injection analysis temporarily unavailable - Drozer connection issue",
            )
            logging.info("SQL injection scan completed")
            self.add_report_section("SQL Injection Vulnerabilities", content_providers)
        except Exception as e:
            error_msg = f"Error during SQL injection vulnerability scan: {e}"
            logging.error(error_msg)
            self.add_report_section(
                "SQL Injection Vulnerabilities",
                f"Analysis temporarily unavailable: {error_msg}",
            )

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
        Test for debuggable logging and sensitive information exposure.

        Checks if the application is debuggable and monitors for sensitive
        information in logs. This test helps identify potential information
        disclosure vulnerabilities through logging.
        """
        logging.info("Testing for debuggable logging and sensitive information...")

        # Check if app is debuggable from manifest
        debuggable_info = []
        if self.apk_ctx.analyzer:
            is_debuggable = self.apk_ctx.analyzer.is_debuggable()
            if is_debuggable:
                debuggable_info.append(
                    '❌ Application is debuggable (android:debuggable="true")'
                )
                debuggable_info.append(
                    "⚠ This allows debugging and may expose sensitive information"
                )
            else:
                debuggable_info.append("✓ Application is not debuggable")

        # Monitor logs for sensitive patterns (if in deep mode)
        log_findings = []
        if self.apk_ctx.scan_mode == "deep":
            try:
                # Run a brief log capture to check for immediate sensitive data
                log_cmd = f"timeout 10s adb logcat | grep '{self.apk_ctx.package_name}'"
                result = subprocess.run(
                    log_cmd, shell=True, capture_output=True, text=True, timeout=15
                )

                if result.stdout:
                    sensitive_patterns = [
                        (r"password", "Password"),
                        (r"token", "Token"),
                        (r"key", "API Key"),
                        (r"secret", "Secret"),
                        (r"http://", "HTTP URL"),
                        (r"\b(?:\d{1,3}\.){3}\d{1,3}\b", "IP Address"),
                    ]

                    for pattern, description in sensitive_patterns:
                        import re

                        if re.search(pattern, result.stdout, re.IGNORECASE):
                            log_findings.append(f"⚠ Found {description} in logs")

                if not log_findings:
                    log_findings.append("✓ No immediate sensitive data found in logs")

            except subprocess.TimeoutExpired:
                log_findings.append("⚠ Log monitoring timed out")
            except Exception as e:
                log_findings.append(f"⚠ Error monitoring logs: {e}")
        else:
            log_findings.append("ℹ Log monitoring skipped in safe mode")

        # Compile results
        all_findings = debuggable_info + log_findings

        # Create formatted output
        result_text = Text()
        result_text.append("Debuggable Logging Analysis\n", style="bold blue")

        for finding in all_findings:
            if finding.startswith("❌"):
                result_text.append(f"{finding}\n", style="red")
            elif finding.startswith("⚠"):
                result_text.append(f"{finding}\n", style="yellow")
            elif finding.startswith("✓"):
                result_text.append(f"{finding}\n", style="green")
            else:
                result_text.append(f"{finding}\n")

        self.add_report_section("Debuggable Logging Test", result_text)

    def platform_01_cleartext_traffic(self) -> None:
        """
        Run PLATFORM-01 Clear-Text-Traffic Flag analysis.

        This method integrates the PLATFORM-01 plugin into the core test suite
        to check for clear-text traffic configuration in the AndroidManifest.xml.
        """
        try:
            from plugins.platform_01_cleartext_traffic import \
                run_platform_01_cleartext_traffic

            logging.info("Running PLATFORM-01: Clear-Text-Traffic Flag analysis...")
            status, analysis_result = run_platform_01_cleartext_traffic(self.apk_ctx)

            # Add to report generator for enhanced reporting
            self.report_generator.add_section(
                "PLATFORM-01: Clear-Text-Traffic Flag Analysis",
                {
                    "id": "PLATFORM-01",
                    "title": "Clear-Text-Traffic Flag Analysis",
                    "description": "Analysis of android:usesCleartextTraffic configuration and network security settings",
                    "status": status,
                    "risk_level": "MEDIUM-HIGH" if status == "FAIL" else "LOW",
                    "category": "Platform Usage",
                    "evidence": str(analysis_result),
                    "masvs_control": "MSTG-NETWORK-01",
                },
            )

            # Add to legacy report format
            self.add_report_section(
                "PLATFORM-01: Clear-Text-Traffic Flag", analysis_result
            )

        except ImportError as e:
            error_msg = f"Failed to import PLATFORM-01 plugin: {e}"
            logging.error(error_msg)
            self.add_report_section(
                "PLATFORM-01: Clear-Text-Traffic Flag",
                Text.from_markup(f"[red]Plugin import error: {error_msg}[/red]"),
            )
        except Exception as e:
            error_msg = f"Error running PLATFORM-01 analysis: {e}"
            logging.error(error_msg, exc_info=True)
            self.add_report_section(
                "PLATFORM-01: Clear-Text-Traffic Flag",
                Text.from_markup(f"[red]Analysis error: {error_msg}[/red]"),
            )

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
        Generate comprehensive security reports in multiple formats.

        Creates reports in the specified formats (text, HTML, JSON, CSV) with
        comprehensive formatting and analysis of scan results.
        """
        output_mgr = get_output_manager()

        # Update report generator with current scan mode
        self.report_generator.scan_mode = self.apk_ctx.scan_mode
        self.report_generator.add_metadata("apk_path", str(self.apk_ctx.apk_path))
        self.report_generator.add_metadata("total_tests_run", len(self.report_data))

        generated_files = {}

        # Generate text report (legacy compatibility)
        if "txt" in self.report_formats:
            output_mgr.verbose("Generating text report...")
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
            generated_files["txt"] = report_filename
            output_mgr.verbose(f"Text report generated: {report_filename}")

        # Generate enhanced reports using ReportGenerator
        try:
            if any(
                fmt in self.report_formats for fmt in ["html", "json", "csv", "all"]
            ):
                if "all" in self.report_formats:
                    output_mgr.verbose("Generating all report formats...")
                    # Generate all formats
                    output_files = self.report_generator.generate_all_formats()
                    for format_name, file_path in output_files.items():
                        generated_files[format_name] = str(file_path)
                        output_mgr.verbose(
                            f"Enhanced {format_name.upper()} report generated: {file_path}"
                        )
                else:
                    # Generate specific formats
                    if "html" in self.report_formats:
                        output_mgr.verbose("Generating HTML report...")
                        html_filename = (
                            f"{self.apk_ctx.package_name}_security_report.html"
                        )
                        self.report_generator.generate_html(Path(html_filename))
                        generated_files["html"] = html_filename
                        output_mgr.verbose(f"HTML report generated: {html_filename}")

                    if "json" in self.report_formats:
                        output_mgr.verbose("Generating JSON report...")
                        json_filename = (
                            f"{self.apk_ctx.package_name}_security_report.json"
                        )
                        self.report_generator.generate_json(Path(json_filename))
                        generated_files["json"] = json_filename
                        output_mgr.verbose(f"JSON report generated: {json_filename}")

                    if "csv" in self.report_formats:
                        output_mgr.verbose("Generating CSV report...")
                        csv_filename = (
                            f"{self.apk_ctx.package_name}_security_report.csv"
                        )
                        self.report_generator.generate_csv(Path(csv_filename))
                        generated_files["csv"] = csv_filename
                        output_mgr.verbose(f"CSV report generated: {csv_filename}")

        except Exception as e:
            output_mgr.error(f"Error generating enhanced reports: {e}")
            output_mgr.warning("Falling back to text-only report generation.")

        # Display generated files summary
        if generated_files:
            output_mgr.report_generated(generated_files)

        output_mgr.verbose("Report generation completed.")

    def full_test_suite(self) -> None:
        """
        Run the complete test suite on the application.

        Executes all tests in a sequence, including starting Drozer,
        unpacking the APK, monitoring logs, running plugins,
        and executing core tests. Finally generates a report.
        Exits the program if critical elements like Drozer fail.
        """
        output_mgr = get_output_manager()

        # Display banner and initial information
        print_banner()

        output_mgr.section_header(
            "OWASP MASVS Security Test Suite",
            "Comprehensive Mobile Application Security Analysis",
        )

        # Display scan configuration
        output_mgr.status(f"Target APK: {self.apk_ctx.apk_path}")
        output_mgr.status(f"Package Name: {self.apk_ctx.package_name}")
        output_mgr.status(f"Scan Mode: {self.apk_ctx.scan_mode.upper()}")

        # Enhanced Drozer connection with hang prevention
        print("🔄 Initializing Drozer connection...")

        # ADDED: Quick Drozer availability check (5 seconds max)
        drozer_available = False
        try:
            # Quick check if Drozer is even available
            quick_check = subprocess.run(
                ["drozer", "console", "connect", "--help"],
                capture_output=True,
                timeout=5,
                check=False,
            )
            if quick_check.returncode == 0:
                drozer_available = True
                output_mgr.status(
                    "🔧 Drozer available, attempting connection...", "info"
                )
            else:
                output_mgr.warning("⚠️ Drozer not responding, skipping dynamic analysis")
        except (subprocess.TimeoutExpired, FileNotFoundError, Exception) as e:
            output_mgr.warning(f"⚠️ Drozer quick check failed: {e}")
            drozer_available = False

        # Only attempt full connection if Drozer is available
        if drozer_available:
            if self.apk_ctx.drozer.start_drozer():
                if self.apk_ctx.drozer.check_connection():
                    output_mgr.status("✅ Drozer connected successfully", "success")
                    output_mgr.info("🚀 Dynamic analysis capabilities enabled")
                else:
                    status = self.apk_ctx.drozer.get_connection_status()

                    # ENHANCED: Prominent failure communication
                    output_mgr.section_header(
                        "⚠️ DROZER CONNECTION FAILURE",
                        "Dynamic analysis capabilities will be limited",
                    )
                    output_mgr.error(f"❌ Connection failed: {status['last_error']}")
                    output_mgr.warning(
                        "🔒 The following analysis features will be unavailable:"
                    )
                    output_mgr.console.print("   • Attack surface mapping via Drozer")
                    output_mgr.console.print("   • Live intent fuzzing")
                    output_mgr.console.print("   • Runtime component enumeration")
                    output_mgr.console.print("   • Dynamic content provider testing")
                    output_mgr.console.print("   • Real-time vulnerability discovery")
                    output_mgr.info(
                        "📊 Analysis will continue with static analysis and available plugins"
                    )
                    output_mgr.status(
                        "⏳ Proceeding with comprehensive static security analysis...",
                        "info",
                    )
            else:
                # ENHANCED: Prominent startup failure communication
                output_mgr.section_header(
                    "⚠️ DROZER STARTUP FAILURE",
                    "Unable to initialize dynamic analysis environment",
                )
                output_mgr.error(
                    "❌ Failed to start Drozer server or establish port forwarding"
                )
                output_mgr.warning("🔧 Possible causes:")
                output_mgr.console.print("   • ADB not properly configured")
                output_mgr.console.print("   • Android device/emulator not connected")
                output_mgr.console.print("   • Drozer agent not installed on device")
                output_mgr.console.print("   • Port forwarding conflicts")
                output_mgr.warning("🔒 Dynamic analysis features will be unavailable:")
                output_mgr.console.print("   • Live component testing")
                output_mgr.console.print("   • Runtime security validation")
                output_mgr.console.print("   • Dynamic attack surface analysis")
                output_mgr.info(
                    "📊 Continuing with static analysis - many vulnerabilities can still be detected"
                )
                output_mgr.status(
                    "⏳ Proceeding with comprehensive static security analysis...",
                    "info",
                )
        else:
            # ENHANCED: Prominent unavailability communication
            output_mgr.section_header(
                "⚠️ DROZER NOT AVAILABLE", "Dynamic analysis framework not detected"
            )
            output_mgr.error("❌ Drozer framework is not installed or not accessible")
            output_mgr.warning("🔧 To enable dynamic analysis:")
            output_mgr.console.print(
                "   1. Install Drozer framework: pip install drozer"
            )
            output_mgr.console.print("   2. Connect Android device/emulator via ADB")
            output_mgr.console.print("   3. Install Drozer agent APK on target device")
            output_mgr.console.print("   4. Ensure USB debugging is enabled")
            output_mgr.warning("🔒 Analysis will be limited to static methods:")
            output_mgr.console.print("   ✓ APK structure analysis")
            output_mgr.console.print("   ✓ Manifest security review")
            output_mgr.console.print("   ✓ Code pattern detection")
            output_mgr.console.print("   ✓ Permission analysis")
            output_mgr.console.print("   ✓ Cryptographic implementation review")
            output_mgr.console.print("   ✓ Hardcoded secret detection")
            output_mgr.info(
                "📊 Static analysis provides comprehensive security coverage for most vulnerabilities"
            )
            output_mgr.status(
                "⏳ Proceeding with enhanced static security analysis...", "info"
            )

        # Unpack APK
        output_mgr.status("Unpacking APK for static analysis...", "progress")
        self.unpack_apk()
        output_mgr.status("APK unpacked successfully", "success")

        # Run plugins
        output_mgr.section_header(
            "Plugin Execution", "Running specialized security test plugins"
        )
        self.run_plugins()

        # Prepare core tests
        core_methods_to_run = []
        for method_name, characteristics in self.core_test_characteristics.items():
            method = getattr(self, method_name, None)
            if method and callable(method):
                mode = characteristics.get("mode", "safe")
                if self.apk_ctx.scan_mode == "deep" or mode == "safe":
                    core_methods_to_run.append((method_name, method, mode))
                else:
                    output_mgr.verbose(f"Skipping core test (safe mode): {method_name}")

        # Execute core tests with progress tracking
        if core_methods_to_run:
            output_mgr.section_header(
                "Core Security Tests", "Executing fundamental security validations"
            )
            output_mgr.progress_start(
                "Running core security tests", len(core_methods_to_run)
            )

            for method_name, method_func, mode in core_methods_to_run:
                test_display_name = method_name.replace("_", " ").title()
                output_mgr.progress_update(
                    description=f"Executing: {test_display_name}"
                )

                try:
                    output_mgr.verbose(f"Running: {test_display_name} ({mode} mode)")
                    method_func()
                    output_mgr.test_result(test_display_name, "PASS")
                except Exception as e:
                    error_msg = f"Error in {method_name}: {e}"
                    output_mgr.test_result(test_display_name, "ERROR", str(e))
                    self.add_report_section(
                        f"Error in test: {method_name}",
                        Text.from_markup(f"[red]{error_msg}[/red]"),
                    )

                output_mgr.progress_update(1)

            output_mgr.progress_stop()

        # Generate reports
        output_mgr.section_header(
            "Report Generation", "Creating comprehensive security analysis reports"
        )

        # Initialize and run secret extraction (Priority 5.1.4)
        output_mgr.status("Initializing secret extraction...", "progress")
        try:
            self.report_generator.initialize_secret_extractor(self.apk_ctx.apk_path)
            output_mgr.status("Running hardcoded secret analysis...", "progress")
            self.report_generator.extract_and_add_secrets()
            output_mgr.status("Secret extraction completed", "success")
        except Exception as e:
            output_mgr.warning(
                f"Secret extraction failed: {e} - Continuing with report generation"
            )

        output_mgr.status("Generating security reports...", "progress")
        self.generate_report()

        # Display final summary
        vulnerabilities = self.report_generator._extract_vulnerabilities()
        output_mgr.vulnerability_summary(vulnerabilities)
        output_mgr.scan_summary(self.report_generator.metadata)

        output_mgr.status("Security analysis completed successfully", "success")

    def configure_plugins(self, plugin_names: List[str]) -> None:
        """Configure specific plugins to run."""
        self.specific_plugins = plugin_names

    def enable_benchmarking(self) -> None:
        """Enable performance benchmarking during analysis."""
        self.benchmarking_enabled = True

    def run_dynamic_analysis(self, duration_seconds: int = 180) -> None:
        """
        Run comprehensive dynamic analysis with enterprise-scale log monitoring.

        Replaces basic logcat monitoring with structured security event analysis.
        """
        output_mgr = get_output_manager()

        # Determine if enterprise mode should be enabled
        enterprise_mode = (
            hasattr(self, "progressive_analyzer")
            and self.progressive_analyzer is not None
        )

        output_mgr.status("🚀 Initiating dynamic security analysis...", "info")

        # Run enterprise dynamic log analysis
        self.dynamic_analysis_results = run_dynamic_log_analysis(
            package_name=self.apk_ctx.package_name,
            duration_seconds=duration_seconds,
            enterprise_mode=enterprise_mode,
        )

        # Add dynamic analysis results to report
        if self.dynamic_analysis_results:
            self._add_dynamic_analysis_to_report()

    def _add_dynamic_analysis_to_report(self) -> None:
        """Add dynamic analysis results to the security report."""
        if not self.dynamic_analysis_results:
            return

        results = self.dynamic_analysis_results

        # Create dynamic analysis report section
        report_content = []

        # Summary
        report_content.append(f"📱 Package Analyzed: {results.package_name}")
        report_content.append(
            f"⏱️ Analysis Duration: {results.analysis_duration_seconds:.1f} seconds"
        )
        report_content.append(f"🔍 Total Security Events: {results.total_events}")
        report_content.append("")

        # Event breakdown by severity
        if results.events_by_severity:
            report_content.append("🔥 Events by Severity:")
            for severity, count in results.events_by_severity.items():
                report_content.append(f"  {severity.value}: {count}")
            report_content.append("")

        # Event breakdown by type
        if results.events_by_type:
            report_content.append("📊 Events by Type:")
            for event_type, count in results.events_by_type.items():
                report_content.append(
                    f"  {event_type.value.replace('_', ' ').title()}: {count}"
                )
            report_content.append("")

        # Intent fuzzing analysis
        intent_results = results.intent_fuzzing_results
        if intent_results:
            report_content.append("🎯 Intent Fuzzing Analysis:")
            report_content.append(
                f"  Components Tested: {intent_results.get('total_components_tested', 0)}"
            )
            report_content.append(
                f"  Responding Components: {intent_results.get('responding_components', 0)}"
            )
            report_content.append(
                f"  Unique Intents Tested: {intent_results.get('unique_intents_tested', 0)}"
            )
            report_content.append(
                f"  Assessment: {intent_results.get('security_assessment', 'Unknown')}"
            )
            report_content.append("")

        # Service access analysis
        service_results = results.service_access_results
        if service_results:
            report_content.append("🔐 Service Access Analysis:")
            report_content.append(
                f"  Services Tested: {service_results.get('services_tested', 0)}"
            )
            report_content.append(
                f"  Protected Services: {service_results.get('protected_services', 0)}"
            )
            protection_rate = service_results.get("protection_rate", 0)
            report_content.append(f"  Protection Rate: {protection_rate:.1%}")
            report_content.append(
                f"  Assessment: {service_results.get('security_assessment', 'Unknown')}"
            )
            report_content.append("")

        # Authentication analysis
        auth_results = results.authentication_analysis
        if auth_results:
            report_content.append("🔑 Authentication Security Analysis:")
            report_content.append(
                f"  Authentication Events: {auth_results.get('authentication_events', 0)}"
            )
            report_content.append(
                f"  Auth Components Detected: {auth_results.get('authentication_components_detected', 0)}"
            )
            report_content.append(
                f"  Assessment: {auth_results.get('security_assessment', 'Unknown')}"
            )
            report_content.append("")

        # Security recommendations
        if results.recommendations:
            report_content.append("📋 Security Recommendations:")
            for i, recommendation in enumerate(results.recommendations, 1):
                report_content.append(f"  {i}. {recommendation}")
            report_content.append("")

        # Add critical events details if any
        critical_events = [
            e for e in results.security_events if e.severity.value == "CRITICAL"
        ]

        if critical_events:
            report_content.append("⚠️ CRITICAL Security Events:")
            for event in critical_events[:5]:  # Show first 5 critical events
                report_content.append(
                    f"  • {event.event_type.value}: {event.component}"
                )
                report_content.append(f"    Action: {event.action}")
                if event.intent_action:
                    report_content.append(f"    Intent: {event.intent_action}")
                report_content.append(
                    f"    Time: {event.timestamp.strftime('%H:%M:%S')}"
                )
                report_content.append("")

        # Add to main report
        dynamic_report = "\n".join(report_content)
        self.add_report_section("Dynamic Security Analysis", dynamic_report)


def main() -> None:
    """
    Main entry point for the application.

    Parses command-line arguments, sets up the test environment,
    and runs the OWASP Mobile Application Security Test Suite.
    """
    # Session isolation to prevent cross-contamination between APK analyses
    analysis_session_id = str(uuid.uuid4())
    logging.info(f"Starting new analysis session: {analysis_session_id}")

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
        default=["html"],
        help="List of formats to generate (txt, html, json, csv, all)",
    )

    # Output management options (Priority 4.1.2)
    parser.add_argument(
        "--quiet",
        "-q",
        action="store_true",
        help="Quiet mode - only show critical errors and final results",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Verbose mode - show detailed progress and status information",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Debug mode - show all debug information and technical details",
    )

    # Enterprise scale analysis options
    parser.add_argument(
        "--enterprise-mode",
        action="store_true",
        help="Enable enterprise-scale analysis optimizations for large APKs (>100MB)",
    )
    parser.add_argument(
        "--plugins",
        nargs="+",
        type=str,
        default=[],
        help="Specific plugins to run (e.g., apk2url_extraction, intent_fuzzing)",
    )
    parser.add_argument(
        "--benchmark",
        action="store_true",
        help="Run performance benchmarking during analysis",
    )

    # ADDED: Parallel execution options (Phase 1 Priority 2 & 3)
    parser.add_argument(
        "--parallel",
        action="store_true",
        default=True,
        help="Enable parallel plugin execution for 3-5x speed improvement (default: enabled)",
    )
    parser.add_argument(
        "--sequential",
        action="store_true",
        help="Force sequential plugin execution (disables parallel processing)",
    )
    parser.add_argument(
        "--optimized",
        action="store_true",
        help="Enable advanced optimized execution with plugin affinity-based scheduling (Phase 1 Priority 3)",
    )
    parser.add_argument(
        "--max-workers",
        type=int,
        metavar="N",
        help="Maximum number of worker threads for parallel execution (auto-detected if not specified)",
    )

    # ADDED: MobileMorphAgent integration options (Phase 1 - Core Integration)
    parser.add_argument(
        "--agent-device",
        type=str,
        metavar="DEVICE_ID",
        help="Device ID of connected MobileMorphAgent (auto-detects if not specified)",
    )
    parser.add_argument(
        "--agent-server",
        type=str,
        default="http://127.0.0.1:5000",
        metavar="URL",
        help="Flask C2 server URL for agent communication (default: http://127.0.0.1:5000)",
    )
    parser.add_argument(
        "--list-packages",
        action="store_true",
        help="List available packages on connected agent and exit",
    )
    parser.add_argument(
        "--interactive-pkg",
        "-i",
        action="store_true",
        help="Interactively select package from connected agent",
    )

    args = parser.parse_args()

    # Handle --list-packages (requires agent)
    if args.list_packages:
        if not args.agent_device:
            print("[ERROR] --list-packages requires --agent-device")
            sys.exit(1)

        try:
            from core.package_discovery import PackageDiscovery
            discovery = PackageDiscovery(args.agent_device, args.agent_server)
            discovery.list_packages()
            sys.exit(0)
        except Exception as e:
            print(f"[ERROR] Failed to list packages: {e}")
            sys.exit(1)

    # Handle interactive package selection
    if args.interactive_pkg:
        if not args.agent_device:
            print("[ERROR] --interactive-pkg requires --agent-device")
            sys.exit(1)

        try:
            from core.package_discovery import PackageDiscovery
            discovery = PackageDiscovery(args.agent_device, args.agent_server)
            selected_pkg = discovery.interactive_select()

            if selected_pkg:
                args.pkg = selected_pkg
                print(f"[INFO] Selected package: {selected_pkg}")
            else:
                print("[ERROR] No package selected")
                sys.exit(1)
        except Exception as e:
            print(f"[ERROR] Interactive selection failed: {e}")
            sys.exit(1)

    # Configure output manager based on arguments
    output_mgr = get_output_manager()
    if args.debug:
        output_mgr.level = OutputLevel.DEBUG
    elif args.verbose:
        output_mgr.level = OutputLevel.VERBOSE
    elif args.quiet:
        output_mgr.level = OutputLevel.QUIET
    else:
        output_mgr.level = OutputLevel.NORMAL

    # Configure logging to match output level
    output_mgr._configure_logging()

    # Determine parallel execution mode
    enable_parallel = args.parallel and not args.sequential
    enable_optimized = args.optimized and not args.sequential

    if args.sequential:
        output_mgr.info("Sequential execution mode enabled")
    elif enable_optimized:
        output_mgr.info(
            "Advanced optimized execution mode enabled (Phase 1 Priority 3)"
        )
        output_mgr.info(
            "🚀 Plugin affinity-based scheduling with specialized worker pools"
        )
    elif enable_parallel:
        output_mgr.info("Parallel execution mode enabled (Phase 1 Priority 2)")

    # Auto-detect device if not specified
    device_id = args.agent_device
    if not device_id:
        try:
            from core.device_auto_detect import auto_detect_device, display_device_banner
            detected_id, device_info = auto_detect_device(args.agent_server)

            if detected_id and device_info:
                display_device_banner(device_info)

                if device_info['agent_online']:
                    device_id = detected_id
                    output_mgr.success(f"✓ Using auto-detected device: {device_id}")
                else:
                    output_mgr.warning("⚠ Device detected but agent not online")
                    output_mgr.info("Proceeding with static analysis only")
            else:
                output_mgr.info("No ADB device detected, running static analysis only")
        except Exception as e:
            output_mgr.debug(f"Auto-detection failed: {e}")
            output_mgr.info("Running static analysis only")

    # Initialize and run test suite with enhanced execution options
    suite = OWASPTestSuiteDrozer(
        args.apk,
        args.pkg,
        enable_parallel=enable_parallel,
        enable_optimized=enable_optimized,
        agent_device_id=device_id,
        agent_server_url=args.agent_server,
    )

    # Display agent connection status if configured
    if device_id:
        if USING_AGENT_BRIDGE and hasattr(suite.apk_ctx.drozer, 'agent_available'):
            if suite.apk_ctx.drozer.agent_available:
                output_mgr.status(
                    f"✅ MobileMorphAgent connected: {device_id}",
                    "success"
                )
                output_mgr.info("🚀 Real-time dynamic analysis enabled")
            else:
                output_mgr.warning(
                    f"⚠️ MobileMorphAgent not available: {device_id}"
                )
                output_mgr.info(f"Error: {suite.apk_ctx.drozer.last_error}")
                output_mgr.info("📊 Falling back to static analysis only")
        else:
            output_mgr.warning("⚠️ Agent bridge not available, using legacy Drozer")

    # Configure max workers if specified
    if args.max_workers and enable_parallel and suite.parallel_engine:
        suite.parallel_engine.max_workers = args.max_workers
        suite.parallel_engine._adaptive_workers = args.max_workers
        output_mgr.info(f"Max workers set to {args.max_workers}")

    suite.apk_ctx.set_scan_mode(args.mode)
    suite.set_report_formats(args.formats)

    # Configure enterprise mode if enabled or auto-detected
    if args.enterprise_mode or suite.apk_ctx.is_enterprise_app():
        output_mgr.info("Enterprise mode enabled - optimizing for large APK analysis")

        # Initialize progressive analyzer for enterprise apps
        try:
            progressive_analyzer = ProgressiveAnalyzer()

            # Configure enterprise analysis strategy
            if suite.apk_ctx.analysis_metadata["apk_size_mb"] > 200:
                # Very large apps (>200MB) - minimal sampling
                progressive_analyzer.configure_enterprise_strategy(
                    "minimal", 0.02
                )  # 2% sampling
            elif suite.apk_ctx.analysis_metadata["apk_size_mb"] > 100:
                # Large apps (>100MB) - reduced sampling
                progressive_analyzer.configure_enterprise_strategy(
                    "reduced", 0.05
                )  # 5% sampling
            else:
                # Standard enterprise apps
                progressive_analyzer.configure_enterprise_strategy(
                    "standard", 0.10
                )  # 10% sampling

            # Apply progressive analysis to the suite
            suite.progressive_analyzer = progressive_analyzer
            output_mgr.status(
                "Progressive analysis configured for enterprise scale", "success"
            )

        except ImportError:
            output_mgr.warning(
                "Progressive analyzer not available - using standard analysis"
            )

    # Configure specific plugins if requested
    if args.plugins:
        output_mgr.info(f"Running specific plugins: {args.plugins}")
        suite.configure_plugins(args.plugins)

    # Enable benchmarking if requested
    if args.benchmark:
        suite.enable_benchmarking()

    suite.full_test_suite()


if __name__ == "__main__":
    main()
