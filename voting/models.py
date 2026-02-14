from django.db import models
from account.models import CustomUser
# Create your models here.


class Election(models.Model):
    title = models.CharField(max_length=100)
    created_by = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title


class Voter(models.Model):
    election = models.ForeignKey(Election, on_delete=models.CASCADE)
    sin = models.CharField(max_length=20)
    voted = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('sin', 'election')

    def __str__(self):
        return f"{self.sin} - {self.election.title}"


class Position(models.Model):
    election = models.ForeignKey(Election, on_delete=models.CASCADE)
    name = models.CharField(max_length=50) # Removed unique=True to allow same position name in diff elections
    max_vote = models.IntegerField()
    priority = models.IntegerField()

    class Meta:
        unique_together = ('name', 'election')

    def __str__(self):
        return f"{self.name} ({self.election.title})"


class Candidate(models.Model):
    fullname = models.CharField(max_length=50)
    photo = models.ImageField(upload_to="candidates")
    bio = models.TextField()
    position = models.ForeignKey(Position, on_delete=models.CASCADE)

    def __str__(self):
        return self.fullname


class Votes(models.Model):
    voter = models.ForeignKey(Voter, on_delete=models.CASCADE)
    position = models.ForeignKey(Position, on_delete=models.CASCADE)
    candidate = models.ForeignKey(Candidate, on_delete=models.CASCADE)
