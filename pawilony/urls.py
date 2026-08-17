from django.contrib.auth import views as auth_views
from django.urls import path

from pawilony import views

app_name = "pawilony"

urlpatterns = [
    path("", views.CalculatorView.as_view(), name="calculator"),
    path("obciazenie/", views.BacklogSummaryView.as_view(), name="backlog_summary"),
    path("admin-panel/login/", auth_views.LoginView.as_view(template_name="pawilony/admin/login.html"), name="login"),
    path("admin-panel/logout/", auth_views.LogoutView.as_view(next_page="pawilony:calculator"), name="logout"),
    path("admin-panel/", views.DashboardView.as_view(), name="dashboard"),
    path("admin-panel/importy/", views.ImportHistoryView.as_view(), name="import_history"),
    path("admin-panel/importy/nowy/", views.ImportUploadView.as_view(), name="import_upload"),
    path("admin-panel/importy/<int:pk>/podglad/", views.ImportPreviewView.as_view(), name="import_preview"),
    path("admin-panel/importy/<int:pk>/zatwierdz/", views.ImportConfirmView.as_view(), name="import_confirm"),
    path("admin-panel/importy/<int:pk>/odrzuc/", views.ImportRejectView.as_view(), name="import_reject"),
]
