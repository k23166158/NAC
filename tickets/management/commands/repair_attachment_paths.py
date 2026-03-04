from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand

from tickets.models import TicketMessageAttachment


class Command(BaseCommand):
    """Repair attachment file paths that were stored as basename-only values."""

    help = "Repair TicketMessageAttachment.file values when only a basename is stored."

    def add_arguments(self, parser):
        """Add command flags."""
        parser.add_argument(
            "--apply",
            action="store_true",
            help="Apply updates to the database. Without this flag, performs a dry run.",
        )

    def handle(self, *args, **options):
        """Run path repair for basename-only attachment rows."""
        apply_changes = options["apply"]
        media_root = Path(settings.MEDIA_ROOT)
        search_root = media_root / "ticket_attachments"
        rows = TicketMessageAttachment.objects.filter(file__regex=r"^[^/]+$")
        total = rows.count()
        self.stdout.write(f"Scanning {total} basename-only attachment rows...")
        if not self._search_root_exists(search_root):
            return
        fixed, missing, ambiguous = self._process_rows(rows, search_root, media_root, apply_changes)
        self._print_summary(apply_changes, fixed, missing, ambiguous, total)

    def _search_root_exists(self, search_root):
        """Return True when ticket attachment root exists."""
        if search_root.exists():
            return True
        self.stdout.write(self.style.WARNING(f"Search root does not exist: {search_root}"))
        return False

    def _process_rows(self, rows, search_root, media_root, apply_changes):
        """Process basename-only rows and return summary counts."""
        summary = {"fixed": 0, "missing": 0, "ambiguous": 0}
        for attachment in rows.iterator():
            result = self._repair_single(attachment, search_root, media_root, apply_changes)
            summary[result] += 1
        return summary["fixed"], summary["missing"], summary["ambiguous"]

    def _repair_single(self, attachment, search_root, media_root, apply_changes):
        """Repair a single row and return fixed/missing/ambiguous."""
        basename = (attachment.file.name or "").strip()
        if not basename:
            return "missing"
        matches = [p for p in search_root.rglob(basename) if p.is_file()]
        if len(matches) != 1:
            return "missing" if len(matches) == 0 else "ambiguous"
        rel = matches[0].relative_to(media_root).as_posix()
        if apply_changes:
            TicketMessageAttachment.objects.filter(pk=attachment.pk).update(file=rel)
        return "fixed"

    def _print_summary(self, apply_changes, fixed, missing, ambiguous, total):
        """Print final summary line."""
        mode = "APPLIED" if apply_changes else "DRY RUN"
        self.stdout.write(f"[{mode}] fixed={fixed} missing={missing} ambiguous={ambiguous} total={total}")
        if not apply_changes:
            self.stdout.write("Re-run with --apply to persist resolvable fixes.")
