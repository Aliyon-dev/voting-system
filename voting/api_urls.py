from django.urls import path
from . import api_views

urlpatterns = [
    path('ballot/', api_views.ballot_api_view, name='api_ballot'),
    path('preview/', api_views.preview_vote_api_view, name='api_preview_vote'),
    path('submit/', api_views.submit_ballot_api_view, name='api_submit_ballot'),
    path('verify-otp/', api_views.verify_otp_api_view, name='api_verify_otp'),
    path('resend-otp/', api_views.resend_otp_api_view, name='api_resend_otp'),
    path('dashboard/', api_views.voter_dashboard_api_view, name='api_voter_dashboard'),
    path('results/', api_views.voter_results_api_view, name='api_voter_results'),
    path('csrf-token/', api_views.get_csrf_token, name='api_csrf_token'),
]


