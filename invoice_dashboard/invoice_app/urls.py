from django.urls import path, include
from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register(r"airlines", views.AirlineViewSet, basename="airline")
router.register(r"vendors", views.VendorViewSet, basename="vendor")
router.register(r"invoices", views.InvoiceViewSet, basename="invoice")
router.register(r"invoice-lines", views.InvoiceLineViewSet, basename="invoice-line")

urlpatterns = [
    path("", include(router.urls)),
    path("summary/", views.SummaryView.as_view(), name="summary"),
    path("ai-suggest/", views.AISuggestView.as_view(), name="ai_suggest"),
]
