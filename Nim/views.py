from django.shortcuts import render
from .models import users, requests, games
from django.http import HttpResponse
import random as rd
from django.http import HttpResponse, HttpResponseRedirect
from django.urls import reverse
from django.utils import timezone
from django.db import IntegrityError
import jwt
import datetime
import requests as pyrequests
from django.conf import settings
from jwt.exceptions import ExpiredSignatureError, InvalidTokenError
import json
from django.shortcuts import redirect
def generate_jwt(username):
    payload = {
        "username": username,
        "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=24)
    }
    token = jwt.encode(payload, settings.SECRET_KEY, algorithm="HS256")
    return token

def verify_jwt(token):
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
        return True  # token is valid
    except ExpiredSignatureError:
        return False  # token expired
    except InvalidTokenError:
        return False  # invalid token (bad signature, tampered, etc.)
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
            user = users.objects.get(username=username)
            if user.check_password(password):  # <-- compares using salt and secure hash
                
                return True
            else:
                return False
        except users.DoesNotExist:
            return False

    elif 'jwt' in request.COOKIES:
        return verify_jwt(request.COOKIES['jwt'])
def fetch_username(request):
    if request.method == 'POST' and 'username' in request.POST:
        return request.POST['username']
    else: 
        payload = jwt.decode(request.COOKIES['jwt'], settings.SECRET_KEY, algorithms=["HS256"]) 
        return payload['username']

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
def game_over(state):
    sum = 0
    for x in state:
        sum += x
    if sum == 0:
        return True
    return False

def notify_fastapi_lobby(to_users, message):
    try:
        pyrequests.post('http://localhost:8000/notify-lobby/', json={"to_users": to_users, "message": message})
    except Exception as e:
        print("Failed to notify FastAPI lobby:", e)
#------------------------------------------------end of helper functions--------------------------------
#------------------------------------------------begin of view functions--------------------------------    
def login(request):
    #games.objects.all().delete()
    #users.objects.all().delete()
    #requests.objects.all().delete()
    return render(request, 'login.html')

def lobby(request):
    if not authorised(request):
        return redirect('Nim:login')

    username = fetch_username(request)
    users.objects.filter(username=username).update(last_time=timezone.now())  # update last active time

    if 'from' in request.POST and 'to' in request.POST:
        # Someone sent a game request
        try:
            sender = users.objects.get(username=request.POST['from'])
            receiver = users.objects.get(username=request.POST['to'])

            # Prevent duplicate requests
            if requests.objects.filter(frm=sender, to=receiver).exists():
                return HttpResponse(status=204)

            # Limit number of sent requests (max 5)
            if requests.objects.filter(frm=sender).count() >= 5:
                return HttpResponse(status=204)

            requests.objects.create(frm=sender, to=receiver)

            # Notify receiver in lobby via FastAPI WebSocket
            notify_fastapi_lobby([receiver.username], {
                "type": "new_request",
                "from": sender.username
            })

            return HttpResponse(status=204)

        except Exception:
            return HttpResponse(status=204)

    elif 'response' in request.POST:
        # Someone responded to a request
        from_user = users.objects.get(username=request.POST['from'])
        to_user = users.objects.get(username=username)

        # Delete the request
        requests.objects.get(frm=from_user, to=to_user).delete()

        # Notify both users about the response
        notify_fastapi_lobby([from_user.username, to_user.username], {
            "type": "request_response",
            "from": from_user.username,
            "to": to_user.username,
            "response": request.POST['response']
        })

        if request.POST['response'] == 'accept':
            if from_user.status == 0 and to_user.status == 0:
                games.objects.create(
                    player1=from_user,
                    player2=to_user,
                    state=get_starting_state(),
                    turn=rd.randint(0, 1)
                )
                from_user.status = 1
                to_user.status = 1
                from_user.save(update_fields=["status"])
                to_user.save(update_fields=["status"])

                # Notify both users that the game has started
                notify_fastapi_lobby([from_user.username, to_user.username], {
                    "type": "game_start",
                    "url": "/play/"
                })

                return redirect('Nim:play')

        return redirect('Nim:lobby')


    # Just viewing the lobby
    context = {
        'users': get_online(),
        'me': username,
        'senders': get_senders(username),
    }
    response = render(request, 'lobby.html', context)
    response.set_cookie('jwt', generate_jwt(username))
    return response

   

def play(request):
    if not authorised(request):
        return redirect('Nim:login')

    username = fetch_username(request)
    user = users.objects.get(username=username)

    game = games.objects.filter(player1=user).first() or games.objects.filter(player2=user).first()
    if not game:
        return redirect('Nim:lobby')  

    context = {}
    context['player'] = 0 if game.player1 == user else 1
    context['turn'] = game.turn
    context['username'] = username
    context['game_id'] = game.id


    if request.method == 'POST' and 'pile_index' in request.POST and 'remove_count' in request.POST:
        if context['player'] == game.turn:
            lis = turn_string_to_list(game.state)
            pile_index = int(request.POST['pile_index'])
            remove_count = int(request.POST['remove_count'])

            if 0 <= pile_index < len(lis) and 1 <= remove_count <= lis[pile_index]:
                lis[pile_index] -= remove_count
                game.state = turn_list_to_string(lis)
                game.turn ^= 1
                game.save(update_fields=["state", "turn"])
        return HttpResponseRedirect(reverse('Nim:play'))


    state = turn_string_to_list(game.state)
    if game_over(state):
        users.objects.filter(id__in=[game.player1_id, game.player2_id]).update(status=0)
        game.delete()
    piles = [[None] * count for count in state]
    context['piles'] = json.dumps(piles)

    return render(request, 'game.html', context)

def create (request):
    context = {}
    if request.method == 'POST':
        context['method'] = 'POST'
        if 'username' in request.POST and 'password' in request.POST:
            try: #try to create account 
                user = users(
                username=request.POST['username'],
                last_time=timezone.now(),
                status=0
                )
                user.set_password(request.POST['password'])  
                user.save()
                context['username'] = 'no'
            except IntegrityError:
                context['username'] = 'yes' #mean user name already exist and this viewed in html page

    else :
        context['method'] = 'GET'   #this info for html


    return render(request, 'create.html', context)

def rules(request):
    #games.objects.all().delete()
    #users.objects.all().delete()
    #requests.objects.all().delete()
    return render(request, 'rules.html')