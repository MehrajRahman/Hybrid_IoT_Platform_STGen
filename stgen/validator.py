# stgen/validator.py
"""
@file validator.py
@brief Automated Protocol Validation Framework
@details Checks protocol compliance with IoT communication best practices.
         This module analyzes the raw metrics produced by the orchestrator against
         defined Quality of Service (QoS) thresholds to determine if a protocol
         is suitable for production use.
"""

import logging
from typing import Dict, Any, List
from dataclasses import dataclass

# @brief Logger for the validator module
_LOG = logging.getLogger("validator")


@dataclass
class ValidationResult:
    """
    @brief Result of a single validation check.
    @details Container for the status, descriptive message, and severity of a specific QoS check.
    """
    check_name: str  # < Name of the check performed (e.g., "Latency (P95)")
    passed: bool  # < Boolean indicating if the check passed
    message: str  # < Human-readable result message
    severity: str  # < Severity level: "critical", "warning", "info"
    metric_value: Any = None  # < The actual measured value associated with the check


class ProtocolValidator:
    """
    @brief Validates protocol implementation against IoT best practices.

    @details Performs a suite of checks including:
             - Latency requirements (P95, P99)
             - Packet loss tolerance
             - Throughput capabilities
             - Concurrency handling
             - Error handling
    """

    def __init__(self, results: Dict[str, Any], qos_requirements: Dict[str, Any] = None):
        """
        @brief Initialize validator.

        @param results Test results dictionary from the orchestrator.
        @param qos_requirements Dictionary of expected QoS thresholds (optional).
                                Examples: {'max_latency_ms': 200, 'max_loss_percent': 1.0}
        """
        self.results = results
        self.qos = qos_requirements or {}
        self.checks: List[ValidationResult] = []

    def run_all_checks(self) -> List[ValidationResult]:
        """
        @brief Run all validation checks.

        @details Executes individual check methods internally and aggregates their results.
        @return List[ValidationResult] A list of all validation results.
        """
        _LOG.info("Running protocol validation checks...")

        self._check_latency()
        self._check_packet_loss()
        self._check_throughput()
        self._check_concurrency()
        self._check_ordering()
        self._check_error_handling()

        return self.checks

    def _check_latency(self) -> None:
        """
        @brief Validate latency meets requirements.
        @details Checks P95 latency against `max_latency_ms` (default 200ms) and
                 P99 latency against 2x the threshold.
        @return None
        """
        max_latency = self.qos.get("max_latency_ms", 200)

        if "lat_p95_ms" in self.results:
            p95 = self.results["lat_p95_ms"]
            passed = p95 <= max_latency

            self.checks.append(ValidationResult(
                check_name="Latency (P95)",
                passed=passed,
                message=f"P95 latency: {p95:.2f}ms (threshold: {max_latency}ms)",
                severity="critical" if not passed else "info",
                metric_value=p95
            ))

        if "lat_p99_ms" in self.results:
            p99 = self.results["lat_p99_ms"]
            max_p99 = max_latency * 2  # P99 can be 2x P95
            passed = p99 <= max_p99

            self.checks.append(ValidationResult(
                check_name="Latency (P99)",
                passed=passed,
                message=f"P99 latency: {p99:.2f}ms (threshold: {max_p99}ms)",
                severity="warning" if not passed else "info",
                metric_value=p99
            ))

    def _check_packet_loss(self) -> None:
        """
        @brief Validate packet loss is within acceptable range.
        @details Checks loss percentage against `max_loss_percent` (default 1.0%).
        @return None
        """
        max_loss = self.qos.get("max_loss_percent", 1.0) / 100.0

        if "loss" in self.results:
            loss = self.results["loss"]
            passed = loss <= max_loss

            self.checks.append(ValidationResult(
                check_name="Packet Loss",
                passed=passed,
                message=f"Loss rate: {loss*100:.2f}% (threshold: {max_loss*100:.1f}%)",
                severity="critical" if not passed else "info",
                metric_value=loss
            ))

    def _check_throughput(self) -> None:
        """
        @brief Validate throughput capabilities.
        @details Verifies that the number of received messages meets the minimum expected count.
        @return None
        """
        if "sent" in self.results and "recv" in self.results:
            sent = self.results["sent"]
            recv = self.results["recv"]

            # Check if protocol handled all clients
            min_expected = self.qos.get("min_messages", 10)
            passed = recv >= min_expected

            self.checks.append(ValidationResult(
                check_name="Throughput",
                passed=passed,
                message=f"Delivered {recv}/{sent} messages (min: {min_expected})",
                severity="warning" if not passed else "info",
                metric_value=recv
            ))

    def _check_concurrency(self) -> None:
        """
        @brief Check if protocol handles concurrent clients without errors.
        @return None
        """
        if "sent" in self.results and "errors" in self.results:
            errors = self.results["errors"]
            passed = errors == 0

            self.checks.append(ValidationResult(
                check_name="Concurrency Handling",
                passed=passed,
                message=f"Errors during concurrent operation: {errors}",
                severity="critical" if not passed else "info",
                metric_value=errors
            ))

    def _check_ordering(self) -> None:
        """
        @brief Check message ordering (if required).
        @details Currently a placeholder for future sequence number analysis.
        @return None
        """
        if self.qos.get("in_order_delivery", False):
            # Check if protocol maintains order
            # This requires sequence number analysis (to be implemented)
            self.checks.append(ValidationResult(
                check_name="Message Ordering",
                passed=True,  # Placeholder
                message="Order preservation not yet validated",
                severity="info"
            ))

    def _check_error_handling(self) -> None:
        """
        @brief Validate error handling and recovery.
        @details Checks total error count reported by the orchestrator.
        @return None
        """
        if "errors" in self.results:
            errors = self.results["errors"]
            passed = errors == 0

            self.checks.append(ValidationResult(
                check_name="Error Handling",
                passed=passed,
                message=f"Total errors: {errors}",
                severity="warning" if errors > 0 else "info",
                metric_value=errors
            ))

    def generate_report(self) -> str:
        """
        @brief Generate a text-based validation report.
        @details Summarizes passed/failed checks and provides an overall status
                 (Production-Ready, Critical Issues, or Warnings).
        @return str The formatted report string.
        """
        report = []
        report.append("=" * 60)
        report.append("PROTOCOL VALIDATION REPORT")
        report.append("=" * 60)
        report.append("")

        passed = sum(1 for c in self.checks if c.passed)
        total = len(self.checks)

        report.append(f"Checks Passed: {passed}/{total}")
        report.append("")

        for check in self.checks:
            if check.passed:
                symbol = "✅"
            elif check.severity == "critical":
                symbol = "❌"
            else:
                symbol = "⚠️"

            report.append(f"{symbol} {check.check_name}: {check.message}")

        report.append("")
        report.append("=" * 60)

        if passed == total:
            report.append(" ALL CHECKS PASSED - Protocol is production-ready!")
        elif any(c.severity == "critical" and not c.passed for c in self.checks):
            report.append(" CRITICAL ISSUES FOUND - Protocol needs fixes")
        else:
            report.append("  WARNINGS FOUND - Protocol works but has issues")

        report.append("=" * 60)

        return "\n".join(report)


def validate_protocol_results(results: Dict[str, Any], qos: Dict[str, Any] = None) -> str:
    """
    @brief Convenience function to validate protocol results.

    @details Instantiates a ProtocolValidator, runs all checks, and returns the report.

    @param results Test results from orchestrator.
    @param qos QoS requirements dictionary.

    @return str Validation report string.
    """
    validator = ProtocolValidator(results, qos)
    validator.run_all_checks()
    return validator.generate_report()
