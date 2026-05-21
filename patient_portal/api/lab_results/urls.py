from django.urls import path

from .sync import SyncView
from .views import ResultsSummaryView

urlpatterns = [
    path('summary/', ResultsSummaryView.as_view(), name='lab-results-summary'),
    path('sync/', SyncView.as_view(), name='lab-results-sync'),
]
