from django.urls import path
from . import views
from django.contrib.auth.views import LogoutView

urlpatterns = [
    path("", views.index, name="index"),
    path("signup/", views.signup_view, name="signup"),
    path("login/", views.login_view, name="login"),
    path("logout/", LogoutView.as_view(next_page="/"), name="logout"),
    path("create/", views.room_create, name="room_create"),
    path("room/<str:room_name>/", views.room, name="room"),
] 