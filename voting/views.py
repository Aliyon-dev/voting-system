from django.shortcuts import render, redirect, reverse
from account.views import voter_login, admin_login # Import correct views if needed, or just use redirection by URL name
from .models import Position, Candidate, Voter, Votes, Election
from django.http import JsonResponse
from django.utils.text import slugify
from django.contrib import messages
from django.conf import settings
import json

def index(request):
    # Retrieve all elections
    elections = Election.objects.all()
    if elections.count() == 1:
        return redirect(reverse('show_ballot', args=[elections.first().id]))
    else:
        # If multiple elections, show a list (we'll implement this template later or simple render)
        # For now, let's just render a simple list or redirect to the first one as a fallback
        # Ideally, we should have an 'election_list' view.
        return render(request, "voting/election_list.html", {'elections': elections})

def generate_ballot(election_id, display_controls=False):
    positions = Position.objects.filter(election_id=election_id).order_by('priority')
    output = ""
    candidates_data = ""
    num = 1
    # return None
    for position in positions:
        name = position.name
        position_name = slugify(name)
        candidates = Candidate.objects.filter(position=position)
        for candidate in candidates:
            if position.max_vote > 1:
                instruction = "You may select up to " + \
                    str(position.max_vote) + " candidates"
                input_box = '<input type="checkbox" value="'+str(candidate.id)+'" class="flat-red ' + \
                    position_name+'" name="' + \
                    position_name+"[]" + '">'
            else:
                instruction = "Select only one candidate"
                input_box = '<input value="'+str(candidate.id)+'" type="radio" class="flat-red ' + \
                    position_name+'" name="'+position_name+'">'
            image = "/media/" + str(candidate.photo)
            candidates_data = candidates_data + '<li>' + input_box + '<button type="button" class="btn btn-primary btn-sm btn-flat clist platform" data-fullname="'+candidate.fullname+'" data-bio="'+candidate.bio+'"><i class="fa fa-search"></i> Platform</button><img src="' + \
                image+'" height="100px" width="100px" class="clist"><span class="cname clist">' + \
                candidate.fullname+'</span></li>'
        up = ''
        if position.priority == 1:
            up = 'disabled'
        down = ''
        if position.priority == positions.count():
            down = 'disabled'
        output = output + f"""<div class="row">	<div class="col-xs-12"><div class="box box-solid" id="{position.id}">
             <div class="box-header with-border">
            <h3 class="box-title"><b>{name}</b></h3>"""

        if display_controls:
            output = output + f""" <div class="pull-right box-tools">
        <button type="button" class="btn btn-default btn-sm moveup" data-id="{position.id}" {up}><i class="fa fa-arrow-up"></i> </button>
        <button type="button" class="btn btn-default btn-sm movedown" data-id="{position.id}" {down}><i class="fa fa-arrow-down"></i></button>
        </div>"""

        output = output + f"""</div>
        <div class="box-body">
        <p>{instruction}
        <span class="pull-right">
        <button type="button" class="btn btn-success btn-sm btn-flat reset" data-desc="{position_name}"><i class="fa fa-refresh"></i> Reset</button>
        </span>
        </p>
        <div id="candidate_list">
        <ul>
        {candidates_data}
        </ul>
        </div>
        </div>
        </div>
        </div>
        </div>
        """
        position.priority = num
        position.save()
        num = num + 1
        candidates_data = ''
    return output


def fetch_ballot(request):
    # This view seems to be used for admin preview mainly? 
    # Or voter? If voter, we need voter_id. If admin, we need admin_election_id.
    # Let's support both.
    election_id = None
    if 'voter_id' in request.session:
        try:
            voter = Voter.objects.get(id=request.session['voter_id'])
            election_id = voter.election.id
        except:
             pass
    elif 'admin_election_id' in request.session:
        election_id = request.session['admin_election_id']
        
    if not election_id:
        return JsonResponse("No election found", safe=False)

    output = generate_ballot(election_id, display_controls=True)
    return JsonResponse(output, safe=False)


def dashboard(request):
    # Check if Admin (Legacy path protection)
    if request.user.is_authenticated:
        if request.user.user_type == '1' or request.user.is_superuser:
             return redirect(reverse("adminDashboard"))

    # Check if Voter
    voter_id = request.session.get('voter_id')
    if not voter_id:
        return redirect(reverse('voter_login'))

    try:
        voter = Voter.objects.get(id=voter_id)
    except Voter.DoesNotExist:
        del request.session['voter_id']
        return redirect(reverse('voter_login'))

    if voter.voted:
        # Filter votes by this voter IN THIS ELECTION (filtered by Voter, so implicit)
        context = {
            'my_votes': Votes.objects.filter(voter=voter),
            'election': voter.election
        }
        return render(request, "voting/voter/result.html", context)
    else:
        return redirect(reverse('show_ballot', args=[voter.election.id]))


def show_ballot(request, election_id=None):
    if not election_id:
        messages.error(request, "No election specified")
        return redirect(reverse('index'))

    try:
        election = Election.objects.get(id=election_id)
    except Election.DoesNotExist:
        messages.error(request, "Election not found")
        return redirect(reverse('index'))

    ballot = generate_ballot(election.id, display_controls=False)
    context = {
        'ballot': ballot,
        'election': election
    }
    return render(request, "voting/voter/ballot.html", context)


def preview_vote(request):
    if request.method != 'POST':
        error = True
        response = "Please browse the system properly"
    else:
        output = ""
        form = dict(request.POST)
        form.pop('csrfmiddlewaretoken', None)
        error = False
        data = []
        
        # Get Election from POST data
        election_id = form.get('election_id')
        if not election_id:
             return JsonResponse({'error': True, 'list': "Election ID missing"})
             
        try:
             election_id = int(election_id[0]) # form.get returns list
        except:
             return JsonResponse({'error': True, 'list': "Invalid Election ID"})

        positions = Position.objects.filter(election_id=election_id)
        for position in positions:
            max_vote = position.max_vote
            pos = slugify(position.name)
            pos_id = position.id
            if position.max_vote > 1:
                this_key = pos + "[]"
                form_position = form.get(this_key)
                if form_position is None:
                    continue
                if len(form_position) > max_vote:
                    error = True
                    response = "You can only choose " + \
                        str(max_vote) + " candidates for " + position.name
                else:
                    start_tag = f"""
                       <div class='row votelist' style='padding-bottom: 2px'>
		                      	<span class='col-sm-4'><span class='pull-right'><b>{position.name} :</b></span></span>
		                      	<span class='col-sm-8'>
                                <ul style='list-style-type:none; margin-left:-40px'>
                    """
                    end_tag = "</ul></span></div><hr/>"
                    data = ""
                    for form_candidate_id in form_position:
                        try:
                            candidate = Candidate.objects.get(
                                id=form_candidate_id, position=position)
                            data += f"""
		                      	<li><i class="fa fa-check-square-o"></i> {candidate.fullname}</li>
                            """
                        except:
                            error = True
                            response = "Please, browse the system properly"
                    output += start_tag + data + end_tag
            else:
                this_key = pos
                form_position = form.get(this_key)
                if form_position is None:
                    continue
                try:
                    form_position = form_position[0]
                    candidate = Candidate.objects.get(
                        position=position, id=form_position)
                    output += f"""
                            <div class='row votelist' style='padding-bottom: 2px'>
		                      	<span class='col-sm-4'><span class='pull-right'><b>{position.name} :</b></span></span>
		                      	<span class='col-sm-8'><i class="fa fa-check-circle-o"></i> {candidate.fullname}</span>
		                    </div>
                      <hr/>
                    """
                except Exception as e:
                    error = True
                    response = "Please, browse the system properly"
    context = {
        'error': error,
        'list': output
    }
    return JsonResponse(context, safe=False)


def submit_ballot(request):
    if request.method != 'POST':
        messages.error(request, "Please, browse the system properly")
        return redirect(reverse('index'))

    form = dict(request.POST)
    form.pop('csrfmiddlewaretoken', None)
    form.pop('submit_vote', None)
    
    # Retrieve SIN and Election ID
    sin = form.pop('sin', None)
    election_id = form.pop('election_id', None)
    
    if not sin:
        messages.error(request, "Please enter your SIN")
        # How to redirect back to ballot with election_id? 
        # We need election_id to redirect.
        if election_id:
             return redirect(reverse('show_ballot', args=[election_id[0]]))
        return redirect(reverse('index'))
    else:
        sin = sin[0] # List, so take first
        
    if not election_id:
        messages.error(request, "Election ID missing")
        return redirect(reverse('index'))
    else:
        election_id = election_id[0]

    # Verify Logic
    try:
        election = Election.objects.get(id=election_id)
    except Election.DoesNotExist:
        messages.error(request, "Invalid Election")
        return redirect(reverse('index'))
        
    # Check if voter exists
    voter, created = Voter.objects.get_or_create(sin=sin, election=election)
    
    if voter.voted:
        messages.error(request, "You have voted already")
        # Redirect to a success page or back to index?
        # Maybe show a dedicated 'already voted' page or valid message on ballot.
        # But if we go back to ballot, SIN is empty again. 
        # For now, back to ballot with error.
        return redirect(reverse('show_ballot', args=[election_id]))

    if len(form.keys()) < 1:
        messages.error(request, "Please select at least one candidate")
        return redirect(reverse('show_ballot', args=[election_id]))
    
    positions = Position.objects.filter(election_id=election.id)
    form_count = 0
    
    for position in positions:
        max_vote = position.max_vote
        pos = slugify(position.name)
        pos_id = position.id
        if position.max_vote > 1:
            this_key = pos + "[]"
            form_position = form.get(this_key)
            if form_position is None:
                continue
            if len(form_position) > max_vote:
                messages.error(request, "You can only choose " +
                               str(max_vote) + " candidates for " + position.name)
                return redirect(reverse('show_ballot', args=[election_id]))
            else:
                for form_candidate_id in form_position:
                    form_count += 1
                    try:
                        candidate = Candidate.objects.get(
                            id=form_candidate_id, position=position)
                        vote = Votes()
                        vote.candidate = candidate
                        vote.voter = voter
                        vote.position = position
                        vote.save()
                    except Exception as e:
                        messages.error(
                            request, "Please, browse the system properly " + str(e))
                        return redirect(reverse('show_ballot', args=[election_id]))
        else:
            this_key = pos
            form_position = form.get(this_key)
            if form_position is None:
                continue
            form_count += 1
            try:
                form_position = form_position[0]
                candidate = Candidate.objects.get(
                    position=position, id=form_position)
                vote = Votes()
                vote.candidate = candidate
                vote.voter = voter
                vote.position = position
                vote.save()
            except Exception as e:
                messages.error(
                    request, "Please, browse the system properly " + str(e))
                return redirect(reverse('show_ballot', args=[election_id]))
    
    inserted_votes = Votes.objects.filter(voter=voter)
    if (inserted_votes.count() != form_count):
        inserted_votes.delete()
        messages.error(request, "Please try voting again!")
        return redirect(reverse('show_ballot', args=[election_id]))
    else:
        voter.voted = True
        voter.save()
        messages.success(request, "Thanks for voting")
        # Where to redirect after voting? 
        # Maybe to a 'thank you' page or index.
        return redirect(reverse('index'))
