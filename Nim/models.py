from django.db import models

class users(models.Model):
    username = models.CharField(max_length=100, unique=True, db_collation='utf8mb4_bin')  # Case-sensitive and unique username
    password = models.CharField(max_length=100, db_collation='utf8mb4_bin')  # Case-sensitive password
    last_time = models.DateTimeField()  # Last activity timestamp
    status = models.IntegerField() 
class requests(models.Model):
    frm = models.ForeignKey(users, on_delete=models.CASCADE, related_name='sent_requests')  # Who sent the request
    to = models.ForeignKey(users, on_delete=models.CASCADE, related_name='received_requests')  # Who receives the request

    class Meta:
        unique_together = ('frm', 'to')  # Prevent sending multiple requests to the same user

class games(models.Model):
    player1 = models.ForeignKey(users, on_delete=models.CASCADE, related_name='games_as_player1')
    player2 = models.ForeignKey(users, on_delete=models.CASCADE, related_name='games_as_player2')
    state = models.CharField(max_length=1000)
    turn = models.IntegerField()
