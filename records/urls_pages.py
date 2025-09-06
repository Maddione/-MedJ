from django.urls import path
from records.views.history import upload_history, document_detail

from records.views.casefiles import casefiles_list, event_detail

app_name = "medj"

urlpatterns = [
    path("upload/history/", upload_history, name="upload_history"),
    path("documents/<int:pk>/", document_detail, name="document_detail"),
    path("casefiles/", casefiles_list, name="casefiles"),
    path("events/<int:pk>/", event_detail, name="event_detail"),

urlpatterns = [
    path("s/<str:token>/", share_public, name="share_public"),
    path("share/history/", share_history_page, name="share_history_page"),
]

]
