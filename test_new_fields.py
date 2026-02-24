import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'e_voting.settings')
django.setup()

from voting.models import Election, Voter
from account.models import CustomUser

def run_tests():
    # Setup
    admin, _ = CustomUser.objects.get_or_create(email="testadmin@test.com", defaults={'user_type': '1', 'is_superuser': True})
    
    # 1. Open election
    print("Testing Open Election (Default)...")
    e_open = Election.objects.create(title="Open", created_by=admin)
    assert e_open.is_open == True
    
    # 2. Closed election
    print("Testing Closed Election...")
    e_closed = Election.objects.create(title="Closed", created_by=admin, is_open=False)
    assert e_closed.is_open == False

    # 3. Active election with strict registration
    print("Testing Open Election (Strict Registration)...")
    e_strict = Election.objects.create(title="Strict", created_by=admin, require_registered_voters=True)
    voter = Voter.objects.create(sin="12345", election=e_strict)

    print("Successfully created elections with 'is_open' field.")
    
    e_open.delete()
    e_closed.delete()
    e_strict.delete()
    admin.delete()
    print("Cleanup done.")

if __name__ == '__main__':
    run_tests()
