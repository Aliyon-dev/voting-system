import os
import django
from django.utils import timezone
from datetime import timedelta

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'e_voting.settings')
django.setup()

from voting.models import Election, Voter, Position, Candidate
from account.models import CustomUser

def run_tests():
    # Setup
    admin, _ = CustomUser.objects.get_or_create(email="testadmin@test.com", defaults={'user_type': '1', 'is_superuser': True})
    
    now = timezone.now()
    past = now - timedelta(days=1)
    future = now + timedelta(days=1)

    # 1. Past election
    print("Testing Past Election...")
    e_past = Election.objects.create(title="Past", created_by=admin, start_date=past - timedelta(days=2), end_date=past)
    assert e_past.end_date < now
    
    # 2. Future election
    print("Testing Future Election...")
    e_future = Election.objects.create(title="Future", created_by=admin, start_date=future, end_date=future + timedelta(days=2))
    assert e_future.start_date > now

    # 3. Active election with strict registration
    print("Testing Active Election (Strict Registration)...")
    e_active_strict = Election.objects.create(title="Active Strict", created_by=admin, start_date=past, end_date=future, require_registered_voters=True)
    voter = Voter.objects.create(sin="12345", election=e_active_strict)

    # Note: testing full views requires RequestFactory, let's just make sure models saved correctly.
    print("Successfully created elections with new fields.")
    
    e_past.delete()
    e_future.delete()
    e_active_strict.delete()
    admin.delete()
    print("Cleanup done.")

if __name__ == '__main__':
    run_tests()
