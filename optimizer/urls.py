from django.urls import path
from .views import OptimizerSubmitView, OptimizerStatusView #, OptimizerTestView

urlpatterns = [
    path('submit/', OptimizerSubmitView.as_view(), name='submit'),
    path('status/<str:task_id>/', OptimizerStatusView.as_view(), name='status'),
]
