#!/usr/bin/env python3
"""Normalize source archive metadata without changing member data."""

from __future__ import annotations

import argparse
import copy
import gzip
import io
import os
import tarfile
import tempfile
from pathlib import Path, PurePosixPath


_VARIABLE_PAX_FIELDS = {"atime", "ctime", "gid", "gname", "mtime", "uid", "uname"}


def normalize(source: Path, destination: Path, epoch: int) -> None:
    if source.resolve() == destination.resolve():
        raise ValueError("input and output paths must differ")
    if not source.is_file():
        raise ValueError(f"input is not a file: {source}")

    destination.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(prefix=".sdist-", dir=destination.parent)
    temporary = Path(temporary_name)
    try:
        with source.open("rb") as source_file, os.fdopen(descriptor, "wb") as output_file:
            with tarfile.open(fileobj=source_file, mode="r:gz") as source_tar:
                with gzip.GzipFile(
                    filename="", fileobj=output_file, mode="wb", mtime=epoch, compresslevel=9
                ) as gzip_file:
                    with tarfile.open(fileobj=gzip_file, mode="w", format=tarfile.PAX_FORMAT) as output_tar:
                        for member in source_tar:
                            member_path = PurePosixPath(member.name)
                            if (
                                member_path.is_absolute()
                                or ".." in member_path.parts
                                or "\\" in member.name
                            ):
                                raise ValueError(f"unsafe archive path: {member.name!r}")
                            if not (member.isdir() or member.isfile()):
                                raise ValueError(f"unsupported archive member type: {member.name!r}")

                            normalized = copy.copy(member)
                            normalized.uid = 0
                            normalized.gid = 0
                            normalized.uname = ""
                            normalized.gname = ""
                            normalized.mtime = epoch
                            normalized.pax_headers = {
                                key: value
                                for key, value in (member.pax_headers or {}).items()
                                if key not in _VARIABLE_PAX_FIELDS
                            }

                            if member.isdir():
                                output_tar.addfile(normalized)
                            else:
                                extracted = source_tar.extractfile(member)
                                if extracted is None:
                                    raise ValueError(f"could not read archive member: {member.name!r}")
                                with extracted:
                                    data = extracted.read()
                                if len(data) != member.size:
                                    raise ValueError(f"truncated archive member: {member.name!r}")
                                output_tar.addfile(normalized, io.BytesIO(data))

        os.replace(temporary, destination)
    except BaseException:
        temporary.unlink(missing_ok=True)
        raise


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path, help="setuptools-generated .tar.gz source archive")
    parser.add_argument("destination", type=Path, help="normalized .tar.gz output archive")
    arguments = parser.parse_args()

    raw_epoch = os.environ.get("SOURCE_DATE_EPOCH")
    if raw_epoch is None or not raw_epoch.isdecimal():
        parser.error("SOURCE_DATE_EPOCH must be a non-negative integer")
    epoch = int(raw_epoch)
    if epoch > 0xFFFFFFFF:
        parser.error("SOURCE_DATE_EPOCH is outside the gzip timestamp range")

    try:
        normalize(arguments.source, arguments.destination, epoch)
    except (OSError, tarfile.TarError, ValueError) as error:
        parser.error(str(error))


if __name__ == "__main__":
    main()
