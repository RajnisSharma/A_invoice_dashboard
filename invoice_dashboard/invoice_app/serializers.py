from decimal import Decimal

from rest_framework import serializers

from .models import Airline, Vendor, Invoice, InvoiceLine


class AirlineSerializer(serializers.ModelSerializer):
    class Meta:
        model = Airline
        fields = [
            "id",
            "name",
            "iata_code",
            "icao_code",
            "country",
            "active",
            "created_at",
            "updated_at",
        ]


class VendorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Vendor
        fields = [
            "id",
            "name",
            "gstin",
            "email",
            "phone",
            "address",
            "active",
            "created_at",
            "updated_at",
        ]


class InvoiceLineSerializer(serializers.ModelSerializer):
    class Meta:
        model = InvoiceLine
        fields = [
            "id",
            "invoice",
            "description",
            "quantity",
            "unit_price",
            "tax_rate",
            "line_total",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["line_total"]


class InvoiceLineNestedSerializer(serializers.ModelSerializer):
    class Meta:
        model = InvoiceLine
        fields = [
            "id",
            "description",
            "quantity",
            "unit_price",
            "tax_rate",
            "line_total",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "line_total", "created_at", "updated_at"]


class InvoiceListSerializer(serializers.ModelSerializer):
    airline = serializers.CharField(source="airline.name", read_only=True)
    airline_id = serializers.IntegerField(read_only=True)
    vendor_name = serializers.CharField(source="vendor.name", read_only=True)
    vendor_id = serializers.IntegerField(read_only=True)
    gstin = serializers.CharField(source="vendor.gstin", read_only=True, allow_blank=True)
    date = serializers.DateField(source="issue_date", read_only=True)
    amount = serializers.DecimalField(
        source="total_amount", max_digits=12, decimal_places=2, read_only=True
    )
    is_overdue = serializers.SerializerMethodField()

    class Meta:
        model = Invoice
        fields = [
            "id",
            "invoice_no",
            "date",
            "issue_date",
            "due_date",
            "airline",
            "airline_id",
            "vendor_name",
            "vendor_id",
            "gstin",
            "amount",
            "total_amount",
            "currency",
            "status",
            "is_overdue",
            "is_flagged",
            "created_at",
            "updated_at",
        ]

    def get_is_overdue(self, obj: Invoice) -> bool:
        return obj.is_overdue


class InvoiceSerializer(serializers.ModelSerializer):
    vendor_name = serializers.CharField(source="vendor.name", read_only=True)
    airline_name = serializers.CharField(source="airline.name", read_only=True)
    gstin = serializers.CharField(source="vendor.gstin", read_only=True, allow_blank=True)
    lines = InvoiceLineNestedSerializer(many=True, required=False)
    is_overdue = serializers.SerializerMethodField()
    date = serializers.DateField(source="issue_date", read_only=True)
    amount = serializers.DecimalField(
        source="total_amount", max_digits=12, decimal_places=2, read_only=True
    )

    class Meta:
        model = Invoice
        fields = [
            "id",
            "invoice_no",
            "vendor",
            "vendor_name",
            "airline",
            "airline_name",
            "issue_date",
            "due_date",
            "date",
            "currency",
            "subtotal",
            "tax_amount",
            "total_amount",
            "amount",
            "status",
            "is_flagged",
            "gstin",
            "notes",
            "metadata",
            "lines",
            "is_overdue",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["subtotal", "tax_amount", "total_amount"]

    def get_is_overdue(self, obj: Invoice) -> bool:
        return obj.is_overdue

    def validate(self, attrs):
        issue_date = attrs.get("issue_date") or getattr(self.instance, "issue_date", None)
        due_date = attrs.get("due_date") or getattr(self.instance, "due_date", None)
        if issue_date and due_date and due_date < issue_date:
            raise serializers.ValidationError("due_date cannot be earlier than issue_date.")
        return attrs

    def create(self, validated_data):
        lines_data = validated_data.pop("lines", [])
        invoice = Invoice.objects.create(**validated_data)
        self._save_lines(invoice, lines_data)
        return invoice

    def update(self, instance, validated_data):
        lines_data = validated_data.pop("lines", None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        if lines_data is not None:
            instance.lines.all().delete()
            self._save_lines(instance, lines_data)
        return instance

    def _save_lines(self, invoice: Invoice, lines_data):
        if not lines_data:
            invoice.recalc_totals(save=True)
            return
        for line in lines_data:
            InvoiceLine.objects.create(invoice=invoice, **line)


class InvoiceSuggestSerializer(InvoiceListSerializer):
    signals = serializers.SerializerMethodField()

    class Meta(InvoiceListSerializer.Meta):
        fields = InvoiceListSerializer.Meta.fields + ["signals"]

    def get_signals(self, obj: Invoice):
        threshold = self.context.get("threshold", Decimal("10000"))
        signals = []
        if obj.total_amount and obj.total_amount >= threshold:
            signals.append("high_value")
        if obj.is_overdue:
            signals.append("overdue")
        if obj.is_flagged:
            signals.append("flagged")
        if not (obj.vendor and obj.vendor.gstin):
            signals.append("missing_gstin")
        return signals
