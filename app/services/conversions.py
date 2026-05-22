from __future__ import annotations

import shutil
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.models import ConversionJob

SOURCE_EXTENSIONS = {".rar", ".cbr", ".7z", ".cb7"}
MAX_LOG_LINES = 300


def conversion_job_to_dict(job: ConversionJob) -> dict:
    return {
        "id": job.id,
        "source_path": job.source_path,
        "destination_path": job.destination_path,
        "output_extension": job.output_extension,
        "overwrite": job.overwrite,
        "delete_source": job.delete_source,
        "status": job.status,
        "current_source": job.current_source,
        "total_files": job.total_files,
        "completed_files": job.completed_files,
        "skipped_files": job.skipped_files,
        "failed_files": job.failed_files,
        "error": job.error,
        "log": job.log,
        "created_at": job.created_at,
        "started_at": job.started_at,
        "finished_at": job.finished_at,
        "updated_at": job.updated_at,
    }


def create_conversion_job(
    db: Session,
    source_path: str,
    destination_path: str | None,
    output_extension: str,
    overwrite: bool,
    delete_source: bool,
) -> ConversionJob:
    normalized_extension = normalize_output_extension(output_extension)
    job = ConversionJob(
        source_path=str(Path(source_path).expanduser()),
        destination_path=str(Path(destination_path).expanduser()) if destination_path else None,
        output_extension=normalized_extension,
        overwrite=overwrite,
        delete_source=delete_source,
        status="queued",
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


def run_conversion_job(job_id: int) -> dict:
    with SessionLocal() as db:
        job = db.get(ConversionJob, job_id)
        if not job:
            return {"success": False, "error": "conversion job not found"}

        try:
            sources = collect_source_archives(Path(job.source_path).expanduser())
            job.total_files = len(sources)
            job.status = "running"
            job.started_at = datetime.now(timezone.utc)
            job.error = ""
            append_log(job, f"Found {len(sources)} source archive(s).")
            db.commit()

            if not sources:
                job.status = "completed"
                job.finished_at = datetime.now(timezone.utc)
                append_log(job, "Nothing to convert.")
                db.commit()
                return {"success": True, "converted": 0, "skipped": 0, "failed": 0}

            for source in sources:
                job.current_source = str(source)
                append_log(job, f"Converting {source}")
                db.commit()

                try:
                    output = output_path_for(source, job.destination_path, job.output_extension)
                    if output.exists() and not job.overwrite:
                        job.skipped_files += 1
                        append_log(job, f"Skipped existing output: {output}")
                        db.commit()
                        continue

                    convert_one_archive(source, output)
                    job.completed_files += 1
                    append_log(job, f"Created {output}")
                    if job.delete_source:
                        source.unlink(missing_ok=True)
                        append_log(job, f"Deleted source {source}")
                except Exception as exc:  # noqa: BLE001 - keep batch conversion moving
                    job.failed_files += 1
                    append_log(job, f"Failed {source}: {exc}")
                    job.error = str(exc)
                finally:
                    db.commit()

            job.current_source = None
            job.finished_at = datetime.now(timezone.utc)
            job.status = "failed" if job.failed_files else "completed"
            db.commit()
            return {
                "success": job.failed_files == 0,
                "converted": job.completed_files,
                "skipped": job.skipped_files,
                "failed": job.failed_files,
            }
        except Exception as exc:  # noqa: BLE001 - persisted job error is the API surface
            job.status = "failed"
            job.error = str(exc)
            job.finished_at = datetime.now(timezone.utc)
            append_log(job, f"Job failed: {exc}")
            db.commit()
            return {"success": False, "error": str(exc)}


def collect_source_archives(source: Path) -> list[Path]:
    if source.is_file() and source.suffix.lower() in SOURCE_EXTENSIONS:
        return [source]
    if source.is_dir():
        return sorted(
            path for path in source.rglob("*") if path.is_file() and path.suffix.lower() in SOURCE_EXTENSIONS
        )
    raise FileNotFoundError(f"Source path does not exist or is unsupported: {source}")


def output_path_for(source: Path, destination_path: str | None, output_extension: str) -> Path:
    destination = Path(destination_path).expanduser() if destination_path else source.parent
    destination.mkdir(parents=True, exist_ok=True)
    return destination / f"{source.stem}.{normalize_output_extension(output_extension)}"


def convert_one_archive(source: Path, output: Path) -> None:
    zip_cmd = shutil.which("zip")
    if not zip_cmd:
        raise RuntimeError("Missing required command: zip")

    with tempfile.TemporaryDirectory(prefix="pyrragi-convert-") as temp_dir:
        extract_archive(source, Path(temp_dir))
        output.parent.mkdir(parents=True, exist_ok=True)
        if output.exists():
            output.unlink()
        run_command([zip_cmd, "-qr", "-X", str(output), "."], cwd=Path(temp_dir))


def extract_archive(source: Path, destination: Path) -> None:
    suffix = source.suffix.lower()
    if suffix in {".rar", ".cbr"}:
        unrar = shutil.which("unrar")
        if unrar:
            run_command([unrar, "x", "-idq", "-o+", "--", str(source), f"{destination}/"])
            return

        sevenz = shutil.which("7zz") or shutil.which("7z")
        if sevenz:
            run_command([sevenz, "x", "-y", "-bd", f"-o{destination}", "--", str(source)])
            return

        unar = shutil.which("unar")
        if unar:
            run_command([unar, "-quiet", "-force-overwrite", "-output-directory", str(destination), "--", str(source)])
            return

        raise RuntimeError("No extractor found for RAR. Install unrar, 7zip, or unar.")

    if suffix in {".7z", ".cb7"}:
        sevenz = shutil.which("7zz") or shutil.which("7z")
        if sevenz:
            run_command([sevenz, "x", "-y", "-bd", f"-o{destination}", "--", str(source)])
            return

        unar = shutil.which("unar")
        if unar:
            run_command([unar, "-quiet", "-force-overwrite", "-output-directory", str(destination), "--", str(source)])
            return

        raise RuntimeError("No extractor found for 7Z. Install 7zip or unar.")

    raise RuntimeError(f"Unsupported archive type: {source.suffix}")


def run_command(command: list[str], cwd: Path | None = None) -> None:
    result = subprocess.run(command, cwd=cwd, capture_output=True, text=True, check=False)
    if result.returncode:
        message = (result.stderr or result.stdout or "command failed").strip()
        raise RuntimeError(message)


def normalize_output_extension(value: str) -> str:
    normalized = (value or "cbz").lower().lstrip(".")
    return normalized if normalized in {"zip", "cbz"} else "cbz"


def append_log(job: ConversionJob, message: str) -> None:
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    lines = [line for line in (job.log or "").splitlines() if line]
    lines.append(f"{timestamp} {message}")
    job.log = "\n".join(lines[-MAX_LOG_LINES:])
