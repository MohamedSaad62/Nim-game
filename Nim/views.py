from django.shortcuts import render
from .models import users, requests, games
from django.http import HttpResponse
import random as rd
from django.shortcuts import redirect
from django.urls import reverse
from django.utils import timezone
from django.db import IntegrityError
def is_online(date):
    diff = timezone.now()- date
    diff = diff.total_seconds() / 60
    if diff < 3:
        return True
    return False

def authorised(request):

    if request.method == 'POST' and 'username' in request.POST and 'password' in request.POST:
        username = request.POST['username']
        password = request.POST['password']
        try:
            user = users.objects.get(username=username, password=password)
            return True
        except users.DoesNotExist:
            return False

    elif 'username' in request.COOKIES:
        return True
def fetch_username(request):
    if request.method == 'POST' and 'username' in request.POST:
        return request.POST['username']
    else: 
        return request.COOKIES['username']

def get_online():
    """
    Returns a list of usernames who are online right now.
    """
    all_users = users.objects.all()
    online_users = [x for x in all_users if(is_online(x.last_time))]
    return [x.username for x in online_users]
def get_senders(username):
    """
    Returns a list of usernames who have sent a request to the given user.
    """
    target = users.objects.get(username=username)
    senders_arr = users.objects.filter(sent_requests__to=target)
    return [x.username for x in senders_arr]
def get_starting_state():
    num = rd.randint(4, 8) #number of piles 
    s = ''
    for i in range(1, num):
        s += str(rd.randint(2, 9))
        s += ','
    s = s[:-1]
    return s
def turn_string_to_list(s):
    return [int(x) for x in s.split(',')]
def turn_list_to_string(lis):
    s = ''
    for x in lis:
        s += str(x)
        s += ','
    s = s[:-1]
    return s
#------------------------------------------------end of helper functions--------------------------------
#------------------------------------------------begin of view functions--------------------------------    
def login(request):
    #games.objects.all().delete()
    #users.objects.all().delete()
    #requests.objects.all().delete()
    return render(request, 'login.html')


def lobby(request):
    if authorised(request):
        username = fetch_username(request)
        users.objects.filter(username=username).update(last_time=timezone.now()) #update time of last activity
        if 'from' in request.POST and 'to' in request.POST:
            #someone sent request
            try:
                sender = users.objects.get(username=request.POST['from'])
                receiver = users.objects.get(username=request.POST['to'])
                requests.objects.create(frm=sender, to=receiver)
                return HttpResponse(status=204)
            except Exception as e:
                return HttpResponse(status=204)
        elif 'response' in request.POST:
            #someone responsed to a request
            from_user = users.objects.get(username=request.POST['from'])
            to_user = users.objects.get(username=username)
            requests.objects.get(frm=from_user, to=to_user).delete()
            if request.POST['response'] == 'accept':
                if from_user.status == 0 and to_user.status == 0:
                    games.objects.create(player1=from_user,player2=to_user,state= get_starting_state(),turn=rd.randint(0, 1)) 
                    from_user.status = 1
                    to_user.status = 1
                    from_user.save(update_fields=["status"])
                    to_user.save(update_fields=["status"])
                    return redirect('Nim:play')
            return redirect('Nim:lobby')
        else:
            #just viewing the lobby
            context = {}
            context['users'] = get_online()
            context['me'] = username
            context['senders'] = get_senders(username)
            response =  render(request, 'lobby.html', context)
            response.set_cookie('username', username, max_age=3600)
            return response
        
    else :
        return redirect('Nim:login')


   
def play(request):
    if authorised(request):
        username = fetch_username(request)
        user = users.objects.get(username=username)
        game = games.objects.filter(player1=user).first() or games.objects.filter(player2=user).first()
        context = {}
        if game.player1 == user:
            context['player'] = 0  
        else:
            context['player'] = 1
        
        context['turn'] = game.turn
        if 'pile_index' in request.POST and 'remove_count' in request.POST:
            if context['player'] == game.turn:
                print(game.turn)
                game.turn ^= 1
                print(game.turn)
                lis = turn_string_to_list(str(game.state))
                lis[int(request.POST['pile_index'])] -= int(request.POST['remove_count'])
                game.state = turn_list_to_string(lis)
                game.save(update_fields=["turn", "state"])
        state =  turn_string_to_list(str(game.state))
        piles = [[None] * count for count in state]
        context['piles'] =piles
        context['turn'] = game.turn
        return render(request, 'game.html', context)
    else :
        return redirect('Nim:login')

def create (request):
    context = {}
    if request.method == 'POST':
        context['method'] = 'POST'
        if 'username' in request.POST and 'password' in request.POST:
            try: #try to create account 
                users.objects.create(
                username=request.POST['username'],
                password=request.POST['password'],
                last_time=timezone.now(),
                status=0
                )
                context['username'] = 'no'
            except IntegrityError:
                context['username'] = 'yes' #mean user name already exist and this viewed in html page

    else :
        context['method'] = 'GET'   #this info for html


    return render(request, 'create.html', context)