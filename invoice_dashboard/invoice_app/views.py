from decimal import Decimal, InvalidOperation

from django.db.models import Q, Sum, Count, F, Value
from django.db.models.functions import Coalesce
from django.utils import timezone
from django.utils.dateparse import parse_date
from rest_framework import viewsets, filters
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Airline, Vendor, Invoice, InvoiceLine, InvoiceStatus
from .pagination import StandardResultsSetPagination
from .serializers import (
    AirlineSerializer,
    VendorSerializer,
    InvoiceSerializer,
    InvoiceListSerializer,
    InvoiceLineSerializer,
    InvoiceSuggestSerializer,
)


def _parse_bool(value: str | None):
    if value is None:
        return None
    value = value.strip().lower()
    if value in {"1", "true", "yes", "y"}:
        return True
    if value in {"0", "false", "no", "n"}:
        return False
    return None


def _parse_decimal(value: str | None):
    if value is None or value == "":
        return None
    try:
        return Decimal(value)
    except (InvalidOperation, TypeError):
        return None


class AirlineViewSet(viewsets.ModelViewSet):
    queryset = Airline.objects.all()
    serializer_class = AirlineSerializer
    pagination_class = StandardResultsSetPagination
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["name", "iata_code", "icao_code", "country"]
    ordering_fields = ["name", "created_at"]
    ordering = ["name"]


class VendorViewSet(viewsets.ModelViewSet):
    queryset = Vendor.objects.all()
    serializer_class = VendorSerializer
    pagination_class = StandardResultsSetPagination
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["name", "gstin", "email", "phone"]
    ordering_fields = ["name", "created_at"]
    ordering = ["name"]


class InvoiceViewSet(viewsets.ModelViewSet):
    queryset = (
        Invoice.objects.select_related("vendor", "airline")
        .prefetch_related("lines")
        .all()
    )
    serializer_class = InvoiceSerializer
    pagination_class = StandardResultsSetPagination
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["invoice_no", "vendor__name", "vendor__gstin", "airline__name"]
    ordering_fields = [
        "issue_date",
        "due_date",
        "total_amount",
        "status",
        "invoice_no",
        "created_at",
    ]
    ordering = ["-issue_date"]

    def get_serializer_class(self):
        if self.action == "list":
            return InvoiceListSerializer
        return InvoiceSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        params = self.request.query_params

        status_param = params.get("status")
        if status_param:
            statuses = [s.strip().upper() for s in status_param.split(",") if s.strip()]
            qs = qs.filter(status__in=statuses)

        vendor_param = params.get("vendor")
        if vendor_param:
            if vendor_param.isdigit():
                qs = qs.filter(vendor_id=int(vendor_param))
            else:
                qs = qs.filter(vendor__name__icontains=vendor_param)

        airline_param = params.get("airline")
        if airline_param:
            if airline_param.isdigit():
                qs = qs.filter(airline_id=int(airline_param))
            else:
                qs = qs.filter(airline__name__icontains=airline_param)

        invoice_no = params.get("invoice_no")
        if invoice_no:
            qs = qs.filter(invoice_no__icontains=invoice_no)

        date_from = parse_date(params.get("date_from", ""))
        if date_from:
            qs = qs.filter(issue_date__gte=date_from)

        date_to = parse_date(params.get("date_to", ""))
        if date_to:
            qs = qs.filter(issue_date__lte=date_to)

        due_from = parse_date(params.get("due_from", ""))
        if due_from:
            qs = qs.filter(due_date__gte=due_from)

        due_to = parse_date(params.get("due_to", ""))
        if due_to:
            qs = qs.filter(due_date__lte=due_to)

        min_total = _parse_decimal(params.get("min_total"))
        if min_total is not None:
            qs = qs.filter(total_amount__gte=min_total)

        max_total = _parse_decimal(params.get("max_total"))
        if max_total is not None:
            qs = qs.filter(total_amount__lte=max_total)

        flagged = _parse_bool(params.get("flagged"))
        if flagged is not None:
            qs = qs.filter(is_flagged=flagged)

        overdue = _parse_bool(params.get("overdue"))
        if overdue is not None:
            today = timezone.now().date()
            overdue_filter = Q(due_date__lt=today) & ~Q(
                status__in=[InvoiceStatus.PAID, InvoiceStatus.CANCELLED]
            )
            qs = qs.filter(overdue_filter if overdue else ~overdue_filter)

        q = params.get("q")
        if q:
            qs = qs.filter(
                Q(invoice_no__icontains=q)
                | Q(vendor__name__icontains=q)
                | Q(vendor__gstin__icontains=q)
                | Q(airline__name__icontains=q)
            )

        return qs.distinct()

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        if "page" in request.query_params or "page_size" in request.query_params:
            page = self.paginate_queryset(queryset)
            if page is not None:
                serializer = self.get_serializer(page, many=True)
                return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)


class InvoiceLineViewSet(viewsets.ModelViewSet):
    queryset = InvoiceLine.objects.select_related("invoice").all()
    serializer_class = InvoiceLineSerializer
    pagination_class = StandardResultsSetPagination
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["description", "invoice__invoice_no"]
    ordering_fields = ["id", "created_at", "line_total"]
    ordering = ["id"]


class SummaryView(APIView):
    """Return airline-wise totals and counts."""

    def get(self, request):
        data = (
            Invoice.objects.annotate(
                airline_name=Coalesce(F("airline__name"), Value("Unknown"))
            )
            .values("airline_name")
            .annotate(
                invoice_count=Count("id"),
                total_amount=Coalesce(Sum("total_amount"), Decimal("0.00")),
            )
            .order_by("-total_amount")
        )
        return Response(
            [
                {
                    "airline": row["airline_name"],
                    "invoice_count": row["invoice_count"],
                    "total_amount": row["total_amount"],
                }
                for row in data
            ]
        )


class AISuggestView(APIView):
    """Rule-based suggestions: high value, overdue, flagged, or missing GSTIN."""

    def get(self, request):
        params = request.query_params
        threshold = _parse_decimal(params.get("min_total") or params.get("threshold"))
        threshold = threshold if threshold is not None else Decimal("10000")
        include_overdue = _parse_bool(params.get("include_overdue"))
        if include_overdue is None:
            include_overdue = True

        qs = Invoice.objects.select_related("vendor", "airline").all()
        filters_q = (
            Q(total_amount__gte=threshold)
            | Q(is_flagged=True)
            | Q(vendor__gstin__isnull=True)
            | Q(vendor__gstin__exact="")
        )

        if include_overdue:
            today = timezone.now().date()
            filters_q |= Q(due_date__lt=today) & ~Q(
                status__in=[InvoiceStatus.PAID, InvoiceStatus.CANCELLED]
            )

        suggestions = qs.filter(filters_q).distinct().order_by("-issue_date")
        serializer = InvoiceSuggestSerializer(
            suggestions, many=True, context={"threshold": threshold}
        )
        return Response(serializer.data)
