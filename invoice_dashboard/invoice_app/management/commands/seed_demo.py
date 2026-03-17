from datetime import timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.utils import timezone

from invoice_app.models import Airline, Vendor, Invoice, InvoiceLine, InvoiceStatus


class Command(BaseCommand):
    help = "Seed 5 demo invoices with vendors, airlines, and line items."

    def add_arguments(self, parser):
        parser.add_argument(
            "--reset",
            action="store_true",
            help="Delete existing invoices and lines before seeding.",
        )

    def handle(self, *args, **options):
        if options.get("reset"):
            InvoiceLine.objects.all().delete()
            Invoice.objects.all().delete()

        airlines = {
            "IndiGo": Airline.objects.get_or_create(name="IndiGo", iata_code="6E")[0],
            "SpiceJet": Airline.objects.get_or_create(name="SpiceJet", iata_code="SG")[0],
            "Thai Airways": Airline.objects.get_or_create(name="Thai Airways", iata_code="TG")[0],
            "Vistara": Airline.objects.get_or_create(name="Vistara", iata_code="UK")[0],
        }

        vendors = {
            "SkyVendor": Vendor.objects.get_or_create(
                name="SkyVendor",
                defaults={"gstin": "27ABCDE1234F1Z5", "email": "finance@skyvendor.com"},
            )[0],
            "CloudNine": Vendor.objects.get_or_create(
                name="CloudNine",
                defaults={"gstin": "27ABCDE1234F1Z6", "email": "accounts@cloudnine.in"},
            )[0],
            "NoGST": Vendor.objects.get_or_create(
                name="NoGST",
                defaults={"gstin": "", "email": "ops@nogst.in"},
            )[0],
        }

        today = timezone.now().date()
        demo_data = [
            {
                "invoice_no": "INV-1001",
                "vendor": vendors["SkyVendor"],
                "airline": airlines["IndiGo"],
                "issue_date": today - timedelta(days=12),
                "due_date": today + timedelta(days=10),
                "status": InvoiceStatus.ISSUED,
                "is_flagged": False,
                "lines": [
                    {"description": "Domestic fare", "quantity": Decimal("2"), "unit_price": Decimal("4200"), "tax_rate": Decimal("5")},
                    {"description": "Airport fees", "quantity": Decimal("2"), "unit_price": Decimal("450"), "tax_rate": Decimal("0")},
                ],
            },
            {
                "invoice_no": "INV-1002",
                "vendor": vendors["CloudNine"],
                "airline": airlines["SpiceJet"],
                "issue_date": today - timedelta(days=20),
                "due_date": today - timedelta(days=2),
                "status": InvoiceStatus.ISSUED,
                "is_flagged": True,
                "lines": [
                    {"description": "Charter service", "quantity": Decimal("1"), "unit_price": Decimal("12000"), "tax_rate": Decimal("12")},
                ],
            },
            {
                "invoice_no": "INV-1003",
                "vendor": vendors["SkyVendor"],
                "airline": airlines["Thai Airways"],
                "issue_date": today - timedelta(days=6),
                "due_date": today + timedelta(days=14),
                "status": InvoiceStatus.PARTIALLY_PAID,
                "is_flagged": False,
                "lines": [
                    {"description": "International fare", "quantity": Decimal("1"), "unit_price": Decimal("18500"), "tax_rate": Decimal("5")},
                ],
            },
            {
                "invoice_no": "INV-1004",
                "vendor": vendors["NoGST"],
                "airline": airlines["Vistara"],
                "issue_date": today - timedelta(days=3),
                "due_date": today + timedelta(days=25),
                "status": InvoiceStatus.DRAFT,
                "is_flagged": False,
                "lines": [
                    {"description": "Catering", "quantity": Decimal("3"), "unit_price": Decimal("1500"), "tax_rate": Decimal("0")},
                    {"description": "Handling", "quantity": Decimal("1"), "unit_price": Decimal("800"), "tax_rate": Decimal("0")},
                ],
            },
            {
                "invoice_no": "INV-1005",
                "vendor": vendors["CloudNine"],
                "airline": airlines["IndiGo"],
                "issue_date": today - timedelta(days=30),
                "due_date": today - timedelta(days=5),
                "status": InvoiceStatus.OVERDUE,
                "is_flagged": True,
                "lines": [
                    {"description": "Ground services", "quantity": Decimal("2"), "unit_price": Decimal("5200"), "tax_rate": Decimal("5")},
                ],
            },
        ]

        created_count = 0
        line_count = 0

        for entry in demo_data:
            invoice, created = Invoice.objects.get_or_create(
                invoice_no=entry["invoice_no"],
                defaults={
                    "vendor": entry["vendor"],
                    "airline": entry["airline"],
                    "issue_date": entry["issue_date"],
                    "due_date": entry["due_date"],
                    "status": entry["status"],
                    "is_flagged": entry["is_flagged"],
                },
            )
            if created:
                created_count += 1
                for line in entry["lines"]:
                    InvoiceLine.objects.create(invoice=invoice, **line)
                    line_count += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Seeded {created_count} invoices and {line_count} lines."
            )
        )
