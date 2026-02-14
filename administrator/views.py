from django.shortcuts import render, reverse, redirect
from voting.models import Voter, Position, Candidate, Votes, Election
from account.models import CustomUser
from voting.forms import *
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django_renderpdf.views import PDFView

@login_required
def dashboard(request):
    user = request.user
    if user.user_type == '1' or user.is_superuser:
        election_id = request.session.get('admin_election_id')
        
        # Super Admin without selection -> Super Dashboard
        if user.is_superuser and not election_id:
             elections = Election.objects.all()
             context = {'elections': elections, 'page_title': 'Super Admin Dashboard'}
             return render(request, "admin/super_dashboard.html", context)
             
        # Regular Admin without selection -> My Elections
        if not election_id:
             elections = Election.objects.filter(created_by=user)
             context = {'elections': elections, 'page_title': 'My Elections'}
             return render(request, "admin/election_list.html", context)

        # Election Dashboard
        try:
            election = Election.objects.get(id=election_id)
        except Election.DoesNotExist:
            del request.session['admin_election_id']
            return redirect(reverse('adminDashboard'))

        positions = Position.objects.filter(election_id=election_id).order_by('priority')
        candidates = Candidate.objects.filter(position__election_id=election_id)
        voters = Voter.objects.filter(election_id=election_id)
        voted_voters = voters.filter(voted=True)
        
        chart_data = {}
        for position in positions:
            list_of_candidates = []
            votes_count = []
            for candidate in candidates.filter(position=position):
                list_of_candidates.append(candidate.fullname)
                votes = Votes.objects.filter(candidate=candidate).count()
                votes_count.append(votes)
            chart_data[position] = {
                'candidates': list_of_candidates,
                'votes': votes_count,
                'pos_id': position.id
            }

        context = {
            'position_count': positions.count(),
            'candidate_count': candidates.count(),
            'voters_count': voters.count(),
            'voted_voters_count': voted_voters.count(),
            'positions': positions,
            'chart_data': chart_data,
            'page_title': "Dashboard",
            'election': election
        }
        return render(request, "admin/home.html", context)
    else:
        return redirect(reverse('voterDashboard'))

@login_required
def voters(request):
    election_id = request.session.get('admin_election_id')
    if not election_id:
        messages.error(request, "Please select an election first")
        return redirect(reverse('adminDashboard'))
        
    voters = Voter.objects.filter(election_id=election_id)
    context = {
        'voters': voters,
        'page_title': 'Voters List'
    }
    if request.method == 'POST':
        sin = request.POST.get('sin')
        if sin:
            if Voter.objects.filter(sin=sin, election_id=election_id).exists():
                messages.error(request, "SIN already exists in this election")
            else:
                election = Election.objects.get(id=election_id)
                voter = Voter(sin=sin, election=election)
                voter.save()
                messages.success(request, "New voter created")
        else:
            messages.error(request, "Please provide a SIN")

    return render(request, "admin/voters.html", context)

@login_required
def view_voter_by_id(request):
    voter_id = request.GET.get('id', None)
    voter = Voter.objects.filter(id=voter_id)
    context = {}
    if not voter.exists():
        context['code'] = 404
    else:
        context['code'] = 200
        voter = voter[0]
        context['sin'] = voter.sin
        context['id'] = voter.id
    return JsonResponse(context)


@login_required
def updateVoter(request):
    if request.method != 'POST':
        messages.error(request, "Access Denied")
    try:
        instance = Voter.objects.get(id=request.POST.get('id'))
        sin = request.POST.get('sin')
        if sin:
            instance.sin = sin
            instance.save()
            messages.success(request, "Voter's SIN updated")
        else:
            messages.error(request, "Please provide a valid SIN")
    except:
        messages.error(request, "Access To This Resource Denied")

    return redirect(reverse('adminViewVoters'))


@login_required
def deleteVoter(request):
    if request.method != 'POST':
        messages.error(request, "Access Denied")
    try:
        voter = Voter.objects.get(id=request.POST.get('id'))
        voter.delete()
        messages.success(request, "Voter Has Been Deleted")
    except:
        messages.error(request, "Access To This Resource Denied")

    return redirect(reverse('adminViewVoters'))


@login_required
def viewPositions(request):
    election_id = request.session.get('admin_election_id')
    if not election_id:
        return redirect(reverse('adminDashboard'))
        
    positions = Position.objects.filter(election_id=election_id).order_by('-priority')
    form = PositionForm(request.POST or None)
    context = {
        'positions': positions,
        'form1': form,
        'page_title': "Positions"
    }
    if request.method == 'POST':
        if form.is_valid():
            form = form.save(commit=False)
            form.election_id = election_id
            form.priority = positions.count() + 1
            form.save()
            messages.success(request, "New Position Created")
        else:
            messages.error(request, "Form errors")
    return render(request, "admin/positions.html", context)


@login_required
def view_position_by_id(request):
    pos_id = request.GET.get('id', None)
    pos = Position.objects.filter(id=pos_id)
    context = {}
    if not pos.exists():
        context['code'] = 404
    else:
        context['code'] = 200
        pos = pos[0]
        context['name'] = pos.name
        context['max_vote'] = pos.max_vote
        context['id'] = pos.id
    return JsonResponse(context)


@login_required
def updatePosition(request):
    if request.method != 'POST':
        messages.error(request, "Access Denied")
    try:
        instance = Position.objects.get(id=request.POST.get('id'))
        pos = PositionForm(request.POST or None, instance=instance)
        # Note: PositionForm needs to allow existing election linkage
        pos.save()
        messages.success(request, "Position has been updated")
    except:
        messages.error(request, "Access To This Resource Denied")

    return redirect(reverse('viewPositions'))


@login_required
def deletePosition(request):
    if request.method != 'POST':
        messages.error(request, "Access Denied")
    try:
        pos = Position.objects.get(id=request.POST.get('id'))
        pos.delete()
        messages.success(request, "Position Has Been Deleted")
    except:
        messages.error(request, "Access To This Resource Denied")

    return redirect(reverse('viewPositions'))


@login_required
def viewCandidates(request):
    election_id = request.session.get('admin_election_id')
    if not election_id:
        return redirect(reverse('adminDashboard'))
        
    candidates = Candidate.objects.filter(position__election_id=election_id)
    form = CandidateForm(request.POST or None, request.FILES or None)
    
    # Filter position dropdown
    if request.method != 'POST':
        form.fields['position'].queryset = Position.objects.filter(election_id=election_id)

    context = {
        'candidates': candidates,
        'form1': form,
        'page_title': 'Candidates'
    }
    if request.method == 'POST':
        # Need to re-filter queryset for validation to work if user submits
        form.fields['position'].queryset = Position.objects.filter(election_id=election_id)
        if form.is_valid():
            form.save()
            messages.success(request, "New Candidate Created")
        else:
            messages.error(request, "Form errors")
    return render(request, "admin/candidates.html", context)


@login_required
def updateCandidate(request):
    if request.method != 'POST':
        messages.error(request, "Access Denied")
    try:
        candidate_id = request.POST.get('id')
        candidate = Candidate.objects.get(id=candidate_id)
        form = CandidateForm(request.POST or None, request.FILES or None, instance=candidate)
        if form.is_valid():
            form.save()
            messages.success(request, "Candidate Data Updated")
        else:
            messages.error(request, "Form has errors")
    except:
        messages.error(request, "Access To This Resource Denied")

    return redirect(reverse('viewCandidates'))


@login_required
def deleteCandidate(request):
    if request.method != 'POST':
        messages.error(request, "Access Denied")
    try:
        pos = Candidate.objects.get(id=request.POST.get('id'))
        pos.delete()
        messages.success(request, "Candidate Has Been Deleted")
    except:
        messages.error(request, "Access To This Resource Denied")

    return redirect(reverse('viewCandidates'))


@login_required
def view_candidate_by_id(request):
    candidate_id = request.GET.get('id', None)
    candidate = Candidate.objects.filter(id=candidate_id)
    context = {}
    if not candidate.exists():
        context['code'] = 404
    else:
        candidate = candidate[0]
        context['code'] = 200
        context['fullname'] = candidate.fullname
        previous = CandidateForm(instance=candidate)
        context['form'] = str(previous.as_p())
    return JsonResponse(context)


@login_required
def ballot_position(request):
    context = {
        'page_title': "Ballot Position"
    }
    return render(request, "admin/ballot_position.html", context)

# update_ballot_position... Skipping logic update details for brevity but crucial it targets correct election. 
# Current logic relies on Position ID which is unique, so it's safe.

@login_required
def ballot_title(request):
    from urllib.parse import urlparse
    url = urlparse(request.META['HTTP_REFERER']).path
    from django.urls import resolve
    try:
        redirect_url = resolve(url)
        title = request.POST.get('title', 'No Name')
        
        # Now we should update Election title, not a file
        election_id = request.session.get('admin_election_id')
        if election_id:
            election = Election.objects.get(id=election_id)
            election.title = title
            election.save()
            messages.success(request, "Election title updated")
        else:
            messages.error(request, "No election selected")
            
        return redirect(url)
    except Exception as e:
        messages.error(request, e)
        return redirect("/")


@login_required
def viewVotes(request):
    election_id = request.session.get('admin_election_id')
    if not election_id:
        return redirect(reverse('adminDashboard'))
    votes = Votes.objects.filter(position__election_id=election_id)
    context = {
        'votes': votes,
        'page_title': 'Votes'
    }
    return render(request, "admin/votes.html", context)


@login_required
def resetVote(request):
    election_id = request.session.get('admin_election_id')
    if not election_id:
        return redirect(reverse('adminDashboard'))
        
    Votes.objects.filter(position__election_id=election_id).delete()
    Voter.objects.filter(election_id=election_id).update(voted=False)
    messages.success(request, "All votes for this election have been reset")
    return redirect(reverse('viewVotes'))

@login_required
def select_election(request):
    if request.user.user_type != '1' and not request.user.is_superuser:
        messages.error(request, "Access Denied")
        return redirect(reverse('voterDashboard'))
        
    if request.method == 'POST':
        election_id = request.POST.get('election_id')
        # Security check: Does user own this election?
        if request.user.is_superuser:
             if Election.objects.filter(id=election_id).exists():
                 request.session['admin_election_id'] = election_id
        else:
             if Election.objects.filter(id=election_id, created_by=request.user).exists():
                 request.session['admin_election_id'] = election_id
    return redirect(reverse('adminDashboard')) # Will redirect to dashboard showing selected election

@login_required
def create_election(request):
    if request.user.user_type != '1' and not request.user.is_superuser:
        messages.error(request, "Access Denied")
        return redirect(reverse('voterDashboard'))

    if request.method == 'POST':
        title = request.POST.get('title')
        if title:
            Election.objects.create(title=title, created_by=request.user)
            messages.success(request, "Election Created")
        else:
            messages.error(request, "Title required")
    return redirect(reverse('adminDashboard'))


@login_required
def deselect_election(request):
    if 'admin_election_id' in request.session:
        del request.session['admin_election_id']
    return redirect(reverse('adminDashboard'))


def find_n_winners(data, n):
    final_list = []
    candidate_data = data[:]
    for i in range(0, n):
        max1 = 0
        if len(candidate_data) == 0:
            continue
        this_winner = max(candidate_data, key=lambda x: x['votes'])
        this = this_winner['name'] + " with " + str(this_winner['votes']) + " votes"
        final_list.append(this)
        candidate_data.remove(this_winner)
    return ", &nbsp;".join(final_list)


class PrintView(PDFView):
    template_name = 'admin/print.html'
    prompt_download = True

    @property
    def download_name(self):
        return "result.pdf"

    def get_context_data(self, *args, **kwargs):
        title = "E-voting"
        # Logic needs to fetch title from current election if possible, or context
        # But this is a Class Based View, getting session is tricky? 
        # request is available in self.request
        election_id = self.request.session.get('admin_election_id')
        if election_id:
            try:
                election = Election.objects.get(id=election_id)
                title = election.title
            except:
                pass
                
        context = super().get_context_data(*args, **kwargs)
        position_data = {}
        
        # Filter by election if selected
        if election_id:
            positions = Position.objects.filter(election_id=election_id)
        else:
            positions = Position.objects.none() # Or all? Better none for safety if not selected.

        for position in positions:
            candidate_data = []
            winner = ""
            for candidate in Candidate.objects.filter(position=position):
                this_candidate_data = {}
                votes = Votes.objects.filter(candidate=candidate).count()
                this_candidate_data['name'] = candidate.fullname
                this_candidate_data['votes'] = votes
                candidate_data.append(this_candidate_data)
            
            if len(candidate_data) < 1:
                winner = "Position does not have candidates"
            else:
                if position.max_vote > 1:
                    winner = find_n_winners(candidate_data, position.max_vote)
                else:
                    winner = max(candidate_data, key=lambda x: x['votes'])
                    if winner['votes'] == 0:
                        winner = "No one voted for this yet."
                    else:
                        count = sum(1 for d in candidate_data if d.get('votes') == winner['votes'])
                        if count > 1:
                            winner = f"There are {count} candidates with {winner['votes']} votes"
                        else:
                            winner = "Winner : " + winner['name']
            
            position_data[position.name] = {
                'candidate_data': candidate_data, 'winner': winner, 'max_vote': position.max_vote}
        context['positions'] = position_data
        context['election_title'] = title
        return context


@login_required
def update_ballot_position(request, position_id, up_or_down):
    try:
        context = {
            'error': False
        }
        position = Position.objects.get(id=position_id)
        election_id = position.election.id # Use position's election context
        
        if up_or_down == 'up':
            priority = position.priority - 1
            if priority == 0:
                context['error'] = True
                output = "This position is already at the top"
            else:
                # Filter by election!
                Position.objects.filter(priority=priority, election_id=election_id).update(
                    priority=(priority+1))
                position.priority = priority
                position.save()
                output = "Moved Up"
        else:
            priority = position.priority + 1
            if priority > Position.objects.filter(election_id=election_id).count():
                output = "This position is already at the bottom"
                context['error'] = True
            else:
                Position.objects.filter(priority=priority, election_id=election_id).update(
                    priority=(priority-1))
                position.priority = priority
                position.save()
                output = "Moved Down"
        context['message'] = output
    except Exception as e:
        context['message'] = str(e)

    return JsonResponse(context)


@login_required
def viewAdmins(request):
    if not request.user.is_superuser:
         return redirect(reverse('adminDashboard'))
    
    admins = CustomUser.objects.filter(user_type='1')
    context = {'admins': admins, 'page_title': 'Administrators'}
    
    if request.method == 'POST':
        # Create Admin
        email = request.POST.get('email')
        password = request.POST.get('password')
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        
        if CustomUser.objects.filter(email=email).exists():
             messages.error(request, "Email already exists")
        else:
             user = CustomUser.objects.create_user(email=email, password=password, first_name=first_name, last_name=last_name, user_type='1')
             messages.success(request, "New Admin Created")
             
    return render(request, "admin/admins.html", context)

@login_required
def deleteAdmin(request):
    if not request.user.is_superuser:
         messages.error(request, "Access Denied")
         return redirect(reverse('adminDashboard'))
    if request.method == 'POST':
         admin_id = request.POST.get('id')
         try:
             admin = CustomUser.objects.get(id=admin_id)
             if admin != request.user: # Prevent self-deletion
                  admin.delete()
                  messages.success(request, "Admin Deleted")
             else:
                  messages.error(request, "Cannot delete yourself")
         except:
              messages.error(request, "Error deleting admin")
    return redirect(reverse('viewAdmins'))
