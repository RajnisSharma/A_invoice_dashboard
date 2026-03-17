from django.contrib import admin

from .models import Airline, Vendor, Invoice, InvoiceLine


@admin.register(Airline)
class AirlineAdmin(admin.ModelAdmin):
    list_display = ("name", "iata_code", "icao_code", "country", "active")
    search_fields = ("name", "iata_code", "icao_code", "country")
    list_filter = ("active", "country")


@admin.register(Vendor)
class VendorAdmin(admin.ModelAdmin):
    list_display = ("name", "gstin", "email", "phone", "active")
    search_fields = ("name", "gstin", "email", "phone")
    list_filter = ("active",)


class InvoiceLineInline(admin.TabularInline):
    model = InvoiceLine
    extra = 0


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = (
        "invoice_no",
        "vendor",
        "airline",
        "issue_date",
        "due_date",
        "total_amount",
        "status",
        "is_flagged",
    )
    search_fields = ("invoice_no", "vendor__name", "airline__name", "vendor__gstin")
    list_filter = ("status", "airline", "vendor", "is_flagged")
    date_hierarchy = "issue_date"
    inlines = [InvoiceLineInline]


@admin.register(InvoiceLine)
class InvoiceLineAdmin(admin.ModelAdmin):
    list_display = ("invoice", "description", "quantity", "unit_price", "line_total")
    search_fields = ("invoice__invoice_no", "description")
