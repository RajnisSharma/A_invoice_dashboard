from decimal import Decimal, ROUND_HALF_UP

from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone


def _quantize(value: Decimal | None) -> Decimal | None:
    if value is None:
        return None
    return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class Airline(TimeStampedModel):
    name = models.CharField(max_length=120, unique=True)
    iata_code = models.CharField(max_length=3, blank=True)
    icao_code = models.CharField(max_length=4, blank=True)
    country = models.CharField(max_length=80, blank=True)
    active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]
        indexes = [
            models.Index(fields=["name"], name="invoice_app_name_1b2d14_idx"),
            models.Index(fields=["iata_code"], name="invoice_app_iata_co_1c4a54_idx"),
        ]

    def __str__(self) -> str:
        return self.name


class Vendor(TimeStampedModel):
    name = models.CharField(max_length=160, unique=True)
    gstin = models.CharField(max_length=15, blank=True)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=30, blank=True)
    address = models.TextField(blank=True)
    active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]
        indexes = [
            models.Index(fields=["name"], name="invoice_app_name_6d0f4c_idx"),
            models.Index(fields=["gstin"], name="invoice_app_gstin_0b7d21_idx"),
        ]

    def __str__(self) -> str:
        return self.name


class InvoiceStatus(models.TextChoices):
    DRAFT = "DRAFT", "Draft"
    ISSUED = "ISSUED", "Issued"
    PARTIALLY_PAID = "PARTIALLY_PAID", "Partially Paid"
    PAID = "PAID", "Paid"
    OVERDUE = "OVERDUE", "Overdue"
    CANCELLED = "CANCELLED", "Cancelled"


class Invoice(TimeStampedModel):
    invoice_no = models.CharField(max_length=40, unique=True)
    vendor = models.ForeignKey(
        Vendor, on_delete=models.PROTECT, related_name="invoices"
    )
    airline = models.ForeignKey(
        Airline, on_delete=models.SET_NULL, related_name="invoices", null=True, blank=True
    )
    issue_date = models.DateField(default=timezone.now)
    due_date = models.DateField(null=True, blank=True)
    currency = models.CharField(max_length=3, default="INR")
    subtotal = models.DecimalField(
        max_digits=12, decimal_places=2, validators=[MinValueValidator(0)], default=0
    )
    tax_amount = models.DecimalField(
        max_digits=12, decimal_places=2, validators=[MinValueValidator(0)], default=0
    )
    total_amount = models.DecimalField(
        max_digits=12, decimal_places=2, validators=[MinValueValidator(0)], default=0
    )
    status = models.CharField(
        max_length=20, choices=InvoiceStatus.choices, default=InvoiceStatus.ISSUED
    )
    is_flagged = models.BooleanField(default=False)
    notes = models.TextField(blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["-issue_date", "-created_at"]
        indexes = [
            models.Index(fields=["invoice_no"], name="invoice_app_invoic_167a2e_idx"),
            models.Index(fields=["issue_date"], name="invoice_app_issue__5b7c1e_idx"),
            models.Index(fields=["due_date"], name="invoice_app_due_da_ee133c_idx"),
            models.Index(fields=["status"], name="invoice_app_status_90e0c8_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.invoice_no}"

    @property
    def is_overdue(self) -> bool:
        if not self.due_date:
            return False
        if self.status in {InvoiceStatus.PAID, InvoiceStatus.CANCELLED}:
            return False
        return self.due_date < timezone.now().date()

    def recalc_totals(self, save: bool = True) -> None:
        lines = self.lines.all()
        subtotal = Decimal("0.00")
        tax = Decimal("0.00")
        for line in lines:
            line_subtotal = (line.quantity or 0) * (line.unit_price or 0)
            line_tax = line_subtotal * ((line.tax_rate or 0) / Decimal("100"))
            subtotal += line_subtotal
            tax += line_tax
        total = subtotal + tax
        subtotal = _quantize(subtotal) or Decimal("0.00")
        tax = _quantize(tax) or Decimal("0.00")
        total = _quantize(total) or Decimal("0.00")
        if save and self.pk:
            Invoice.objects.filter(pk=self.pk).update(
                subtotal=subtotal, tax_amount=tax, total_amount=total
            )
        self.subtotal = subtotal
        self.tax_amount = tax
        self.total_amount = total


class InvoiceLine(TimeStampedModel):
    invoice = models.ForeignKey(
        Invoice, on_delete=models.CASCADE, related_name="lines"
    )
    description = models.CharField(max_length=255)
    quantity = models.DecimalField(
        max_digits=10, decimal_places=2, validators=[MinValueValidator(0)], default=1
    )
    unit_price = models.DecimalField(
        max_digits=12, decimal_places=2, validators=[MinValueValidator(0)], default=0
    )
    tax_rate = models.DecimalField(
        max_digits=5, decimal_places=2, validators=[MinValueValidator(0)], default=0
    )
    line_total = models.DecimalField(
        max_digits=12, decimal_places=2, validators=[MinValueValidator(0)], default=0
    )

    class Meta:
        ordering = ["id"]
        indexes = [
            models.Index(fields=["invoice"], name="invoice_app_invoic_4d5b1b_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.invoice.invoice_no} - {self.description}"

    def save(self, *args, **kwargs):
        line_subtotal = (self.quantity or 0) * (self.unit_price or 0)
        line_tax = line_subtotal * ((self.tax_rate or 0) / Decimal("100"))
        self.line_total = _quantize(line_subtotal + line_tax) or Decimal("0.00")
        super().save(*args, **kwargs)
        self.invoice.recalc_totals(save=True)

    def delete(self, *args, **kwargs):
        invoice = self.invoice
        super().delete(*args, **kwargs)
        invoice.recalc_totals(save=True)
