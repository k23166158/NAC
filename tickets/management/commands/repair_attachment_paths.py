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

        basename_rows = TicketMessageAttachment.objects.filter(file__regex=r"^[^/]+$")
        total = basename_rows.count()
        fixed = 0
        missing = 0
        ambiguous = 0

        self.stdout.write(f"Scanning {total} basename-only attachment rows...")
        if not search_root.exists():
            self.stdout.write(self.style.WARNING(f"Search root does not exist: {search_root}"))
            return

        for attachment in basename_rows.iterator():
            basename = (attachment.file.name or "").strip()
            if not basename:
                missing += 1
                continue

            matches = [p for p in search_root.rglob(basename) if p.is_file()]
            if len(matches) == 1:
                rel = matches[0].relative_to(media_root).as_posix()
                if apply_changes:
                    TicketMessageAttachment.objects.filter(pk=attachment.pk).update(file=rel)
                fixed += 1
            elif len(matches) == 0:
                missing += 1
            else:
                ambiguous += 1

        mode = "APPLIED" if apply_changes else "DRY RUN"
        self.stdout.write(
            f"[{mode}] fixed={fixed} missing={missing} ambiguous={ambiguous} total={total}"
        )
        if not apply_changes:
            self.stdout.write("Re-run with --apply to persist resolvable fixes.")
