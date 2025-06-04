from django.urls import path

from . import views
from django.conf.urls.static import static
app_name = "Nim"
urlpatterns = [
    path("play/", views.play, name="play"),
    path("", views.login, name="login"),
    path("create/", views.create, name="create"),
    path("lobby/", views.lobby, name="lobby"),
]