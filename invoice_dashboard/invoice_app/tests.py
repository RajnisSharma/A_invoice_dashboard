from datetime import timedelta
from decimal import Decimal

from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APITestCase

from .models import Airline, Vendor, Invoice, InvoiceLine, InvoiceStatus


class InvoiceModelTests(TestCase):
    def test_line_recalculates_totals(self):
        vendor = Vendor.objects.create(name="SkyVendor", gstin="27ABCDE1234F1Z5")
        airline = Airline.objects.create(name="IndiGo", iata_code="6E")
        invoice = Invoice.objects.create(
            invoice_no="INV-100",
            vendor=vendor,
            airline=airline,
            issue_date=timezone.now().date(),
        )

        InvoiceLine.objects.create(
            invoice=invoice,
            description="Ticket",
            quantity=Decimal("2"),
            unit_price=Decimal("5000"),
            tax_rate=Decimal("5"),
        )
        invoice.refresh_from_db()

        self.assertEqual(invoice.subtotal, Decimal("10000.00"))
        self.assertEqual(invoice.tax_amount, Decimal("500.00"))
        self.assertEqual(invoice.total_amount, Decimal("10500.00"))

    def test_overdue_flag(self):
        vendor = Vendor.objects.create(name="NoGST")
        invoice = Invoice.objects.create(
            invoice_no="INV-200",
            vendor=vendor,
            issue_date=timezone.now().date() - timedelta(days=10),
            due_date=timezone.now().date() - timedelta(days=2),
            status=InvoiceStatus.ISSUED,
        )
        self.assertTrue(invoice.is_overdue)


class InvoiceAPITests(APITestCase):
    def setUp(self):
        self.airline = Airline.objects.create(name="IndiGo", iata_code="6E")
        self.vendor = Vendor.objects.create(name="SkyVendor", gstin="27ABCDE1234F1Z5")
        self.vendor_missing_gstin = Vendor.objects.create(name="NoGST", gstin="")

        self.invoice = Invoice.objects.create(
            invoice_no="INV-1001",
            vendor=self.vendor,
            airline=self.airline,
            issue_date=timezone.now().date() - timedelta(days=3),
            due_date=timezone.now().date() + timedelta(days=10),
            status=InvoiceStatus.ISSUED,
        )
        InvoiceLine.objects.create(
            invoice=self.invoice,
            description="Ticket",
            quantity=Decimal("2"),
            unit_price=Decimal("5000"),
            tax_rate=Decimal("5"),
        )
        self.invoice.refresh_from_db()

        self.overdue_invoice = Invoice.objects.create(
            invoice_no="INV-1002",
            vendor=self.vendor_missing_gstin,
            airline=None,
            issue_date=timezone.now().date() - timedelta(days=20),
            due_date=timezone.now().date() - timedelta(days=5),
            status=InvoiceStatus.ISSUED,
            is_flagged=True,
        )
        InvoiceLine.objects.create(
            invoice=self.overdue_invoice,
            description="Handling",
            quantity=Decimal("1"),
            unit_price=Decimal("12000"),
            tax_rate=Decimal("0"),
        )
        self.overdue_invoice.refresh_from_db()

    def test_list_invoices(self):
        res = self.client.get("/api/invoices/")
        self.assertEqual(res.status_code, 200)
        self.assertIsInstance(res.data, list)
        self.assertEqual(len(res.data), 2)

    def test_pagination_response(self):
        res = self.client.get("/api/invoices/?page=1")
        self.assertEqual(res.status_code, 200)
        self.assertIn("results", res.data)

    def test_summary_endpoint(self):
        res = self.client.get("/api/summary/")
        self.assertEqual(res.status_code, 200)
        airlines = {row["airline"] for row in res.data}
        self.assertIn("IndiGo", airlines)
        self.assertIn("Unknown", airlines)

    def test_ai_suggest_endpoint(self):
        res = self.client.get("/api/ai-suggest/")
        self.assertEqual(res.status_code, 200)
        ids = {item["id"] for item in res.data}
        self.assertIn(self.overdue_invoice.id, ids)
        self.assertTrue(any(item.get("signals") for item in res.data))

    def test_filtering(self):
        res = self.client.get("/api/invoices/?min_total=11000")
        self.assertEqual(res.status_code, 200)
        ids = {item["id"] for item in res.data}
        self.assertIn(self.overdue_invoice.id, ids)
        self.assertNotIn(self.invoice.id, ids)

        overdue_res = self.client.get("/api/invoices/?overdue=true")
        overdue_ids = {item["id"] for item in overdue_res.data}
        self.assertIn(self.overdue_invoice.id, overdue_ids)

    def test_toggle_flag(self):
        res = self.client.patch(
            f"/api/invoices/{self.invoice.id}/",
            {"is_flagged": True},
            format="json",
        )
        self.assertEqual(res.status_code, 200)
        self.invoice.refresh_from_db()
        self.assertTrue(self.invoice.is_flagged)
