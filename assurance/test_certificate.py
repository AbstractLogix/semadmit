"""Adversarial checks for the assurance certificate writer."""

from __future__ import annotations

import hashlib
import io
import json
import unittest
import copy
import os
import stat
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from contextlib import redirect_stderr
from unittest.mock import patch

from assurance.mutation_check import MUTATIONS
from assurance.source_build import (
    BUILD_COMMANDS,
    SOURCE_EXPORT_COMMAND,
    VALIDATION_COMMAND,
    _run_sandboxed,
)
from assurance.verify_certificate import (
    UNSUPPORTED_GUARANTEES,
    load_certificate,
    validate_certificate_record,
)
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
    main as write_certificate_main,
)


class CertificateIntegrityChecks(unittest.TestCase):
    def _offline_fixture(self, root):
        import hashlib
        import io
        import tarfile
        import zipfile

        source_revision = "a" * 40
        artifact_paths = {}
        executable = root / "semantic-oracle"
        executable.write_bytes(b"\x7fELF" + b"offline-test")
        executable.chmod(0o755)
        artifact_paths["haskell_executable"] = executable

        def tar_archive(path, members):
            with tarfile.open(path, "w:gz") as archive:
                for name, content in members.items():
                    info = tarfile.TarInfo(name)
                    info.size = len(content)
                    archive.addfile(info, io.BytesIO(content))

        haskell_archive = root / "semantic-oracle.tar.gz"
        tar_archive(
            haskell_archive,
            {"semantic-oracle/semantic-oracle.cabal": b"name: semantic-oracle\n", "semantic-oracle/LICENSE": b"license"},
        )
        artifact_paths["haskell_source_archive"] = haskell_archive

        wheel = root / "semadmit.whl"
        with zipfile.ZipFile(wheel, "w") as archive:
            archive.writestr("semadmit/__init__.py", b"\n")
            archive.writestr("semadmit-0.dist-info/METADATA", b"Name: semadmit\n")
            archive.writestr("semadmit-0.dist-info/licenses/LICENSE", b"license")
        artifact_paths["python_wheel"] = wheel

        python_archive = root / "semadmit.tar.gz"
        tar_archive(
            python_archive,
            {
                "semadmit/pyproject.toml": b"[project]\n",
                "semadmit/semadmit/__init__.py": b"\n",
                "semadmit/LICENSE": b"license",
            },
        )
        artifact_paths["python_source_archive"] = python_archive

        artifact_records = {}
        for name, path in artifact_paths.items():
            data = path.read_bytes()
            artifact_records[name] = {
                "filename": path.name,
                "sha256": hashlib.sha256(data).hexdigest(),
                "size_bytes": len(data),
                "mode": stat.S_IMODE(path.stat().st_mode),
            }
        validation = {
            "tests": {"python_package_tests": 1},
            "mutations": {"killed": 1, "total": 1},
            "gates": [
                {"name": "seeded_corpus", "exit_code": 0},
                {"name": "source_mutation", "exit_code": 0},
                {"name": "test_and_coverage", "exit_code": 0},
            ],
        }
        rebuilt = {
            "source": {"commit": source_revision, "tree": "b" * 40},
            "source_date_epoch": 1791569362,
            "locked_inputs_sha256": {"cabal.project.freeze": "c" * 64},
            "build_inputs_sha256": {"assurance/source_build.py": "d" * 64},
            "toolchain": {
                "python": "3.13.14",
                "ghc": "9.14.1",
                "cabal": "3.18.1.0",
                "uv": "uv 0.11.31",
                "system": "Linux",
                "release": "test",
                "machine": "x86_64",
            },
            "commands": {
                "source_export": SOURCE_EXPORT_COMMAND,
                "validation": VALIDATION_COMMAND,
                "build": BUILD_COMMANDS,
            },
            "environment": {
                "LC_ALL": "C.UTF-8",
                "PYTHONHASHSEED": "0",
                "SOURCE_DATE_EPOCH": "source commit time",
                "TZ": "UTC",
                "UV_OFFLINE": "1",
                "CABAL_OFFLINE": "true via temporary CABAL_CONFIG",
            },
            "validation": validation,
            "artifacts": artifact_records,
        }
        certificate = {
            "format": "semadmit-assurance-certificate/0.2",
            "protocol_scope": {
                "claim_protocol": "semadmit/claim/0.1",
                "claim_status": "qualified; Python-only semantics",
                "bouleusis_pin": "de61aa87a5f4470fd64de33c926cff7f92cf8bd6",
                "core_protocol": "semantic-oracle/0.1",
                "selector_protocol": "selector-provenance/0.1",
                "selector_status": "experimental; bounded independence outcomes remain indeterminate",
            },
            "source": {
                **rebuilt["source"],
                "source_date_epoch": rebuilt["source_date_epoch"],
                "locked_inputs_sha256": rebuilt["locked_inputs_sha256"],
                "build_inputs_sha256": rebuilt["build_inputs_sha256"],
            },
            "build": {
                "toolchain": rebuilt["toolchain"],
                "commands": rebuilt["commands"],
                "environment": rebuilt["environment"],
                "artifacts": copy.deepcopy(artifact_records),
                "provenance": {
                    "method": "clean-source-rebuild",
                    "authenticated": False,
                    "ci_execution_identity": {
                        "authentication": "recorded-unverified",
                        "run_id": "123",
                        "run_url": "https://github.com/AbstractLogix/semadmit/actions/runs/123",
                        "head_sha": source_revision,
                        "workflow_name": "Coverage",
                        "workflow_database_id": 375788046,
                        "status": "passed",
                    },
                },
            },
            "validation": copy.deepcopy(validation),
            "unsupported_guarantees": list(UNSUPPORTED_GUARANTEES),
        }
        return certificate, rebuilt, artifact_paths, source_revision

    def test_offline_verifier_accepts_matching_source_rebuild_fixture(self) -> None:
        with TemporaryDirectory() as temporary:
            certificate, rebuilt, artifacts, source_revision = self._offline_fixture(Path(temporary))
            validate_certificate_record(certificate, source_revision, rebuilt, artifacts)

    def test_isolated_build_hides_host_environment_and_blocks_host_writes(self) -> None:
        import shutil
        import sys

        if shutil.which("bwrap") is None:
            self.skipTest("bubblewrap is unavailable in this test environment")
        with TemporaryDirectory() as temporary:
            work = Path(temporary).resolve()
            source = work / "source"
            cabal_cache = work / "cabal-cache"
            uv_cache = work / "uv-cache"
            for directory in (source, cabal_cache, uv_cache):
                directory.mkdir()
            clean_env = {"PATH": os.environ["PATH"], "PYTHONHASHSEED": "0"}
            output = _run_sandboxed(
                [sys.executable, "-c", "import os; print(os.environ.get('PYTHONPATH', '<unset>'))"],
                cwd=source,
                env=clean_env,
                work=work,
                cabal_cache=cabal_cache,
                uv_cache=uv_cache,
                capture=True,
            )
            self.assertEqual(output.strip(), "<unset>")
            host_path = work.parent / f"semadmit-sandbox-write-{work.name}"
            host_path.write_text("protected", encoding="utf-8")
            try:
                with self.assertRaisesRegex(RuntimeError, "isolated command failed"):
                    _run_sandboxed(
                        [sys.executable, "-c", f"open({str(host_path)!r}, 'w').write('changed')"],
                        cwd=source,
                        env=clean_env,
                        work=work,
                        cabal_cache=cabal_cache,
                        uv_cache=uv_cache,
                        capture=True,
                    )
                self.assertEqual(host_path.read_text(encoding="utf-8"), "protected")
            finally:
                host_path.unlink()

    def test_offline_verifier_rejects_arbitrary_artifact_substitution(self) -> None:
        with TemporaryDirectory() as temporary:
            certificate, rebuilt, artifacts, source_revision = self._offline_fixture(Path(temporary))
            substituted = artifacts["python_wheel"]
            substituted.write_text("arbitrary bytes accepted by the old writer", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "does not match the clean-source rebuild"):
                validate_certificate_record(certificate, source_revision, rebuilt, artifacts)

    def test_offline_verifier_rejects_replayed_or_changed_source_identity(self) -> None:
        with TemporaryDirectory() as temporary:
            certificate, rebuilt, artifacts, source_revision = self._offline_fixture(Path(temporary))
            with self.assertRaisesRegex(ValueError, "externally expected revision"):
                validate_certificate_record(certificate, "d" * 40, rebuilt, artifacts)
            certificate["source"]["tree"] = "e" * 40
            with self.assertRaisesRegex(ValueError, "source tree or locked build inputs"):
                validate_certificate_record(certificate, source_revision, rebuilt, artifacts)

    def test_offline_verifier_rejects_altered_results_and_missing_gates(self) -> None:
        with TemporaryDirectory() as temporary:
            certificate, rebuilt, artifacts, source_revision = self._offline_fixture(Path(temporary))
            certificate["validation"]["tests"]["python_package_tests"] = 2
            with self.assertRaisesRegex(ValueError, "results do not match"):
                validate_certificate_record(certificate, source_revision, rebuilt, artifacts)
            certificate["validation"] = dict(rebuilt["validation"])
            certificate["validation"]["gates"] = []
            with self.assertRaisesRegex(ValueError, "results do not match"):
                validate_certificate_record(certificate, source_revision, rebuilt, artifacts)

    def test_offline_verifier_rejects_invalid_or_stale_provenance(self) -> None:
        with TemporaryDirectory() as temporary:
            certificate, rebuilt, artifacts, source_revision = self._offline_fixture(Path(temporary))
            provenance = certificate["build"]["provenance"]
            provenance["authenticated"] = True
            with self.assertRaisesRegex(ValueError, "overstated build provenance"):
                validate_certificate_record(certificate, source_revision, rebuilt, artifacts)
            provenance["authenticated"] = False
            provenance["ci_execution_identity"]["head_sha"] = "f" * 40
            with self.assertRaisesRegex(ValueError, "CI identity is stale"):
                validate_certificate_record(certificate, source_revision, rebuilt, artifacts)

    def test_offline_verifier_rejects_missing_artifacts_tampered_hash_and_truncation(self) -> None:
        with TemporaryDirectory() as temporary:
            certificate, rebuilt, artifacts, source_revision = self._offline_fixture(Path(temporary))
            artifacts.pop("python_wheel")
            with self.assertRaisesRegex(ValueError, "all four required artifact paths"):
                validate_certificate_record(certificate, source_revision, rebuilt, artifacts)
            artifacts["python_wheel"] = Path(temporary) / "semadmit.whl"
            artifacts["python_wheel"].unlink()
            with self.assertRaisesRegex(ValueError, "artifact is missing"):
                validate_certificate_record(certificate, source_revision, rebuilt, artifacts)
            artifacts["python_wheel"].write_bytes(b"arbitrary replacement")
            certificate["build"]["artifacts"]["python_wheel"]["sha256"] = "0" * 64
            with self.assertRaisesRegex(ValueError, "artifact record does not match"):
                validate_certificate_record(certificate, source_revision, rebuilt, artifacts)
            truncated = Path(temporary) / "truncated.json"
            truncated.write_text('{"format":', encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "truncated"):
                load_certificate(truncated)
            duplicate = Path(temporary) / "duplicate.json"
            duplicate.write_text('{"format":"a","format":"b"}', encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "duplicate JSON object key"):
                load_certificate(duplicate)

    def test_writer_does_not_accept_caller_supplied_artifact_paths(self) -> None:
        import sys

        supplied = [
            "write-certificate",
            "--source-revision",
            "a" * 40,
            "--ci-run-url",
            "https://github.com/AbstractLogix/semadmit/actions/runs/123",
            "--artifacts-dir",
            "/tmp/generated-by-writer",
            "--python-wheel",
            "/tmp/arbitrary.whl",
        ]
        with patch("sys.argv", supplied), redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit) as error:
                write_certificate_main()
        self.assertEqual(error.exception.code, 2)

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
