"""Adversarial checks for the assurance certificate writer."""

from __future__ import annotations

import hashlib
import json
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from assurance.mutation_check import MUTATIONS
from assurance.write_certificate import (
    MANDATORY_LOCAL_GATES,
    REQUIRED_CI_WORKFLOW_DATABASE_ID,
    REQUIRED_CI_WORKFLOW_NAME,
    checked_gate,
    expected_python_test_counts,
    hosted_ci,
    local_validation,
    parse_python_test_counts,
    require_clean_validation_commit,
)


class CertificateIntegrityChecks(unittest.TestCase):
    def test_missing_logs_and_nonzero_exit_fail_closed(self) -> None:
        with patch(
            "assurance.write_certificate.subprocess.run",
            return_value=SimpleNamespace(stdout="", returncode=0),
        ):
            with self.assertRaisesRegex(RuntimeError, "no execution log"):
                checked_gate("missing-log", ["true"])

        with patch(
            "assurance.write_certificate.subprocess.run",
            return_value=SimpleNamespace(stdout="partial run output\n", returncode=2),
        ):
            with self.assertRaisesRegex(RuntimeError, "exit code 2"):
                checked_gate("failed-gate", ["false"])

    def test_successful_gate_records_complete_log_hash(self) -> None:
        output = "complete test run\n"
        with patch(
            "assurance.write_certificate.subprocess.run",
            return_value=SimpleNamespace(stdout=output, returncode=0),
        ):
            captured, evidence = checked_gate("logged-gate", ["true"])
        self.assertEqual(captured, output)
        self.assertEqual(evidence["stdout_bytes"], len(output.encode("utf-8")))
        self.assertEqual(
            evidence["stdout_sha256"], hashlib.sha256(output.encode("utf-8")).hexdigest()
        )

    def test_truncated_corpus_output_fails_closed(self) -> None:
        with patch(
            "assurance.write_certificate.checked_gate",
            return_value=("seeded assurance corpus matches", {}),
        ):
            with self.assertRaisesRegex(RuntimeError, "missing or truncated"):
                local_validation()

    def test_truncated_coverage_output_fails_closed(self) -> None:
        package_count, reference_count, certificate_count = expected_python_test_counts()
        mutation_output = "\n".join(
            [
                *(f"KILLED: {mutation.name}" for mutation in MUTATIONS),
                f"mutation score: {len(MUTATIONS)}/{len(MUTATIONS)} (100%)",
            ]
        )
        outputs = [
            "seeded assurance corpus matches its generator",
            mutation_output,
            (
                f"Ran {package_count} tests in 0.001s\nOK\n"
                f"Ran {reference_count} tests in 0.001s\nOK\n"
                f"Ran {certificate_count} tests in 0.001s\nOK\n"
            ),
        ]
        with patch(
            "assurance.write_certificate.checked_gate",
            side_effect=lambda name, command: (
                outputs.pop(0), {"name": name, "argv": command, "exit_code": 0}
            ),
        ):
            with self.assertRaisesRegex(RuntimeError, "success marker"):
                local_validation()

    def test_fabricated_python_test_counts_fail_closed(self) -> None:
        package_count, reference_count, certificate_count = expected_python_test_counts()
        output = (
            f"Ran {package_count + 1} tests in 0.001s\nOK\n"
            f"Ran {reference_count} tests in 0.001s\nOK\n"
            f"Ran {certificate_count} tests in 0.001s\nOK\n"
            "All test and coverage gates passed.\n"
        )
        with self.assertRaisesRegex(RuntimeError, "do not match discovered"):
            parse_python_test_counts(output)

    def test_all_mandatory_local_gates_execute_and_record_logs(self) -> None:
        package_count, reference_count, certificate_count = expected_python_test_counts()
        mutation_output = "\n".join(
            [
                *(f"KILLED: {mutation.name}" for mutation in MUTATIONS),
                f"mutation score: {len(MUTATIONS)}/{len(MUTATIONS)} (100%)",
            ]
        )
        outputs = [
            "seeded assurance corpus matches its generator",
            mutation_output,
            (
                f"Ran {package_count} tests in 0.001s\nOK\n"
                f"Ran {reference_count} tests in 0.001s\nOK\n"
                f"Ran {certificate_count} tests in 0.001s\nOK\n"
                "All test and coverage gates passed.\n"
            ),
        ]
        with patch(
            "assurance.write_certificate.checked_gate",
            side_effect=lambda name, command: (
                outputs.pop(0), {"name": name, "argv": command, "exit_code": 0}
            ),
        ):
            _tests, _mutations, gates = local_validation()
        self.assertEqual(tuple(gate["name"] for gate in gates), MANDATORY_LOCAL_GATES)

    def test_incorrect_mutation_results_fail_closed(self) -> None:
        outputs = [
            "seeded assurance corpus matches its generator",
            "KILLED: canonical-result-comparison\nmutation score: 7/7 (100%)",
        ]
        with patch(
            "assurance.write_certificate.checked_gate",
            side_effect=lambda name, command: (
                outputs.pop(0), {"name": name, "argv": command, "exit_code": 0}
            ),
        ):
            with self.assertRaisesRegex(RuntimeError, "every configured mutation"):
                local_validation()

    def test_incorrect_validation_commit_fails_closed(self) -> None:
        with patch(
            "assurance.write_certificate.subprocess.run",
            side_effect=[
                SimpleNamespace(stdout="a" * 40),
                SimpleNamespace(stdout=""),
                SimpleNamespace(returncode=0),
            ],
        ):
            with self.assertRaisesRegex(RuntimeError, "clean checkout"):
                require_clean_validation_commit("b" * 40, "a" * 40)

    def test_stale_and_wrong_workflow_ci_fail_closed(self) -> None:
        url = "https://github.com/AbstractLogix/semadmit/actions/runs/12345"
        validation_commit = "a" * 40
        run = {
            "url": url,
            "status": "completed",
            "conclusion": "success",
            "headSha": validation_commit,
            "name": REQUIRED_CI_WORKFLOW_NAME,
            "workflowDatabaseId": REQUIRED_CI_WORKFLOW_DATABASE_ID,
        }
        with patch(
            "assurance.write_certificate.subprocess.run",
            return_value=SimpleNamespace(stdout=json.dumps(run)),
        ):
            self.assertEqual(hosted_ci(url, validation_commit)["status"], "passed")

        for mutation, message in (
            ({"headSha": "b" * 40}, "validation commit"),
            ({"name": "Unrelated workflow", "workflowDatabaseId": 1}, "required Coverage"),
            ({"status": "in_progress"}, "not completed successfully"),
            ({"conclusion": "failure"}, "not completed successfully"),
        ):
            with self.subTest(mutation=mutation):
                altered = {**run, **mutation}
                with patch(
                    "assurance.write_certificate.subprocess.run",
                    return_value=SimpleNamespace(stdout=json.dumps(altered)),
                ):
                    with self.assertRaisesRegex(RuntimeError, message):
                        hosted_ci(url, validation_commit)

    def test_missing_hosted_ci_fails_closed(self) -> None:
        with self.assertRaisesRegex(RuntimeError, "CI run is required"):
            hosted_ci(None, "a" * 40)


if __name__ == "__main__":
    unittest.main()
