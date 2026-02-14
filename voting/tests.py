from django.test import TestCase, Client
from django.urls import reverse
from voting.models import Election, Position, Candidate, Voter, Votes
from account.models import CustomUser

class SINVotingTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = CustomUser.objects.create(email="admin@test.com", password="password")
        self.election = Election.objects.create(title="Test Election", created_by=self.user)
        self.position = Position.objects.create(election=self.election, name="President", max_vote=1, priority=1)
        self.candidate = Candidate.objects.create(fullname="Candidate A", position=self.position, bio="Bio")

    def test_index_redirects_single_election(self):
        response = self.client.get(reverse('index'))
        self.assertRedirects(response, reverse('show_ballot', args=[self.election.id]))

    def test_show_ballot_renders(self):
        response = self.client.get(reverse('show_ballot', args=[self.election.id]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'name="sin"')
        self.assertContains(response, 'name="election_id"')

    def test_submit_ballot_success(self):
        sin = "123456789"
        # Provide election_id in url to avoid redirect loop if error, though successful post redirects to index
        response = self.client.post(reverse('submit_ballot'), {
             'sin': sin,
             'election_id': self.election.id,
             f'president': self.candidate.id # Slugified position name
        }, follow=True)
        # Expect redirect to index, then to show_ballot (since only 1 election)
        self.assertRedirects(response, reverse('show_ballot', args=[self.election.id]), target_status_code=200)
        
        # Verify voter created
        self.assertTrue(Voter.objects.filter(sin=sin, election=self.election).exists())
        voter = Voter.objects.get(sin=sin, election=self.election)
        self.assertTrue(voter.voted)
        
        # Verify vote recorded
        self.assertTrue(Votes.objects.filter(voter=voter, candidate=self.candidate).exists())

    def test_submit_ballot_duplicate_sin(self):
        sin = "123456789"
        # First vote
        self.client.post(reverse('submit_ballot'), {
            'sin': sin,
            'election_id': self.election.id,
            f'president': self.candidate.id
        })
        
        # Second vote
        response = self.client.post(reverse('submit_ballot'), {
            'sin': sin,
            'election_id': self.election.id,
            f'president': self.candidate.id
        }, follow=True)
        
        # Should contain error message and redirect back to ballot
        self.assertContains(response, "You have voted already")
        # Check that we are back on the ballot page
        self.assertRedirects(response, reverse('show_ballot', args=[self.election.id]))

    def test_submit_without_sin(self):
        # We need to make sure we are not redirected to index (if election_id missing) but to ballot
        # But submit_ballot without election_id redirects to index.
        # With election_id it redirects to ballot.
        response = self.client.post(reverse('submit_ballot'), {
            'election_id': self.election.id,
            f'president': self.candidate.id
        }, follow=True)
        self.assertContains(response, "Please enter your SIN")
        self.assertRedirects(response, reverse('show_ballot', args=[self.election.id]))

    def test_index_renders_list_multiple_elections(self):
        Election.objects.create(title="Election 2", created_by=self.user)
        response = self.client.get(reverse('index'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Select an Election")
        self.assertContains(response, "Test Election")
        self.assertContains(response, "Election 2")
        self.assertContains(response, "Admin Login")
        self.assertContains(response, reverse('account_login'))

    def test_voter_login_redirects_to_index(self):
        Election.objects.create(title="Election 2", created_by=self.user)
        response = self.client.get(reverse('voter_login'))
        self.assertRedirects(response, reverse('index'))
