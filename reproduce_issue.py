import os
import django
import sys

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'e_voting.settings')
django.setup()

from voting.models import Votes, Election, Position, Candidate, Voter

def check_votes():
    print("Checking votes...")
    elections = Election.objects.all()
    print(f"Found {elections.count()} elections.")
    
    for election in elections:
        print(f"Checking election: {election.title} (ID: {election.id})")
        votes = Votes.objects.filter(position__election_id=election.id)
        print(f"Found {votes.count()} votes.")
        
        for i, vote in enumerate(votes):
            try:
                print(f"Vote {i}: ID={vote.id}")
                print(f"  Voter: {vote.voter}")
                print(f"  Candidate: {vote.candidate}")
                print(f"  Position: {vote.position}")
            except Exception as e:
                print(f"ERROR processing vote {vote.id}: {e}")
                import traceback
                traceback.print_exc()

if __name__ == "__main__":
    check_votes()
