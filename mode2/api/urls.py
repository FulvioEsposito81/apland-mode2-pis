"""
URL configuration for MODE II API.
"""

from django.urls import path

from .views import DataImportView, DataValidateView

urlpatterns = [
    path(
        '<str:dataset_ref_name>/<uuid:uuid>/data/<str:data_ref_name>/validate',
        DataValidateView.as_view(),
        name='data-validate'
    ),
    path(
        '<str:dataset_ref_name>/<uuid:uuid>/data/<str:data_ref_name>/import',
        DataImportView.as_view(),
        name='data-import'
    ),
]
