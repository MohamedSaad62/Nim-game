from django.shortcuts import render
from .models import users, requests
from django.http import HttpResponse
import random as rd
from django.shortcuts import redirect
from django.urls import reverse
from django.utils import timezone

def is_online(date):
    diff = timezone.now()- date
    diff = diff.total_seconds() / 60
    if diff < 3:
        return True
    return False


def login(request):
    return render(request, 'login.html')


def lobby(request):
    if request.method == 'POST':
        if 'from' in request.POST:
            print("from " + request.POST['from'])
            print("to " + request.POST['to'])
            requests.objects.get_or_create(frm=request.POST['from'], to=request.POST['to'])
                
            return HttpResponse(status=204)
        if users.objects.filter(username = request.POST['username']).exists():
            user = users.objects.filter(username= request.POST['username']).first()
            if user.password == request.POST['password']:
                context = {}
                users.objects.filter(username=request.POST['username']).update(last_time=timezone.now())
                all_users = users.objects.all()
                online_users = [x for x in all_users if(is_online(x.last_time))]
                context['users'] = [x.username for x in online_users]
                context['me'] = request.POST['username']
                response =  render(request, 'lobby.html', context)
                response.set_cookie('username', user.username, max_age=3600)
                return response
            else :
                return redirect('Nim:login')
        else:
            return redirect('Nim:login')
    else:
         if 'username' in request.COOKIES:
            context = {}
            context['users'] = list(users.objects.values_list('username', flat=True))
            context['me'] = request.COOKIES.get('username')
            return render(request, 'lobby.html', context)
         else :
            return redirect('Nim:login')

def play(request):
    return render(request, 'game1.html')

def create (request):
    context = {}
    if request.method == 'POST':
        context['method'] = 'POST'
        if 'username' in request.POST:
            if users.objects.filter(username = request.POST['username']).exists():
                context['username'] = 'yes'
            else :
                context['username'] = 'no'
                users.objects.create(username = request.POST['username'], password = request.POST['password'], last_time = \
                timezone.now(), status = 1)

    else :
        context['method'] = 'GET'


    return render(request, 'create.html', context)