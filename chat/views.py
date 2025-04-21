from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login, authenticate
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from .models import Room
from .forms import RoomForm

def signup_view(request):
    if request.method == "POST":
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect("index")
    else:
        form = UserCreationForm()
    return render(request, "chat/signup.html", {"form": form})

def login_view(request):
    if request.method == "POST":
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = authenticate(username=form.cleaned_data["username"],
                                password=form.cleaned_data["password"])
            if user:
                login(request, user)
                return redirect("index")
    else:
        form = AuthenticationForm()
    return render(request, "chat/login.html", {"form": form})

@login_required
def index(request):
    rooms = Room.objects.all()
    return render(request, "chat/index.html", {"rooms": rooms})

@login_required
def room_create(request):
    if request.method == "POST":
        form = RoomForm(request.POST)
        if form.is_valid():
            room = form.save(commit=False)
            room.owner = request.user
            room.save()
            return redirect("room", room_name=room.name)
    else:
        form = RoomForm()
    return render(request, "chat/room_create.html", {"form": form})

@login_required
def room(request, room_name):
    room = get_object_or_404(Room, name=room_name)
    return render(request, "chat/room.html", {"room_name": room.name}) 