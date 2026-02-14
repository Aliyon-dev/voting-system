from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from django.utils.text import slugify
from django.conf import settings
from django.contrib import messages
from .models import Position, Candidate, Voter, Votes
from .serializers import (
    PositionSerializer, CandidateSerializer, VoteSerializer,
    VoterSerializer, OTPVerificationSerializer, BallotSerializer
)
from .views import generate_otp, send_sms, bypass_otp


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def ballot_api_view(request):
    """API endpoint to get ballot data (positions and candidates)"""
    if request.user.user_type != '2':  # Only voters
        return Response(
            {'error': 'Only voters can access ballot'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    positions = Position.objects.order_by('priority').all()
    positions_data = PositionSerializer(positions, many=True).data
    
    # Get candidates for each position
    candidates_data = {}
    for position in positions:
        candidates = Candidate.objects.filter(position=position)
        candidates_data[position.id] = CandidateSerializer(
            candidates, many=True, context={'request': request}
        ).data
    
    return Response({
        'positions': positions_data,
        'candidates': candidates_data
    }, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def preview_vote_api_view(request):
    """API endpoint to preview selected votes"""
    if request.user.user_type != '2':  # Only voters
        return Response(
            {'error': 'Only voters can preview votes'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    votes_data = request.data.get('votes', {})
    
    if not votes_data:
        return Response(
            {'error': 'No votes provided'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    preview_list = []
    error = False
    error_message = None
    
    positions = Position.objects.all()
    
    for position in positions:
        max_vote = position.max_vote
        pos = slugify(position.name)
        
        if position.max_vote > 1:
            # Multiple votes allowed
            position_key = pos
            selected_candidate_ids = votes_data.get(position_key, [])
            
            if not selected_candidate_ids:
                continue
            
            if len(selected_candidate_ids) > max_vote:
                error = True
                error_message = f"You can only choose {max_vote} candidates for {position.name}"
                break
            
            candidates = []
            for candidate_id in selected_candidate_ids:
                try:
                    candidate = Candidate.objects.get(id=candidate_id, position=position)
                    candidates.append({
                        'id': candidate.id,
                        'fullname': candidate.fullname,
                    })
                except Candidate.DoesNotExist:
                    error = True
                    error_message = "Invalid candidate selected"
                    break
            
            if error:
                break
            
            preview_list.append({
                'position': position.name,
                'candidates': candidates,
            })
        else:
            # Single vote
            position_key = pos
            selected_candidate_id = votes_data.get(position_key)
            
            if not selected_candidate_id:
                continue
            
            # Handle both list and single value
            if isinstance(selected_candidate_id, list):
                selected_candidate_id = selected_candidate_id[0] if selected_candidate_id else None
            
            if not selected_candidate_id:
                continue
            
            try:
                candidate = Candidate.objects.get(id=selected_candidate_id, position=position)
                preview_list.append({
                    'position': position.name,
                    'candidates': [{
                        'id': candidate.id,
                        'fullname': candidate.fullname,
                    }],
                })
            except Candidate.DoesNotExist:
                error = True
                error_message = "Invalid candidate selected"
                break
    
    if error:
        return Response(
            {'error': error_message},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    return Response({
        'preview': preview_list,
        'success': True
    }, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def submit_ballot_api_view(request):
    """API endpoint to submit votes"""
    if request.user.user_type != '2':  # Only voters
        return Response(
            {'error': 'Only voters can submit votes'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    voter = request.user.voter
    
    # Check if already voted
    if voter.voted:
        return Response(
            {'error': 'You have already voted'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    votes_data = request.data.get('votes', {})
    
    if not votes_data:
        return Response(
            {'error': 'Please select at least one candidate'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    positions = Position.objects.all()
    form_count = 0
    created_votes = []
    
    try:
        for position in positions:
            max_vote = position.max_vote
            pos = slugify(position.name)
            
            if position.max_vote > 1:
                # Multiple votes
                position_key = pos
                selected_candidate_ids = votes_data.get(position_key, [])
                
                if not selected_candidate_ids:
                    continue
                
                if len(selected_candidate_ids) > max_vote:
                    # Rollback
                    Votes.objects.filter(voter=voter, id__in=[v.id for v in created_votes]).delete()
                    return Response(
                        {'error': f'You can only choose {max_vote} candidates for {position.name}'},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                
                for candidate_id in selected_candidate_ids:
                    try:
                        candidate = Candidate.objects.get(id=candidate_id, position=position)
                        vote = Votes.objects.create(
                            candidate=candidate,
                            voter=voter,
                            position=position
                        )
                        created_votes.append(vote)
                        form_count += 1
                    except Candidate.DoesNotExist:
                        Votes.objects.filter(voter=voter, id__in=[v.id for v in created_votes]).delete()
                        return Response(
                            {'error': 'Invalid candidate selected'},
                            status=status.HTTP_400_BAD_REQUEST
                        )
            else:
                # Single vote
                position_key = pos
                selected_candidate_id = votes_data.get(position_key)
                
                if not selected_candidate_id:
                    continue
                
                # Handle both list and single value
                if isinstance(selected_candidate_id, list):
                    selected_candidate_id = selected_candidate_id[0] if selected_candidate_id else None
                
                if not selected_candidate_id:
                    continue
                
                try:
                    candidate = Candidate.objects.get(id=selected_candidate_id, position=position)
                    vote = Votes.objects.create(
                        candidate=candidate,
                        voter=voter,
                        position=position
                    )
                    created_votes.append(vote)
                    form_count += 1
                except Candidate.DoesNotExist:
                    Votes.objects.filter(voter=voter, id__in=[v.id for v in created_votes]).delete()
                    return Response(
                        {'error': 'Invalid candidate selected'},
                        status=status.HTTP_400_BAD_REQUEST
                    )
        
        # Verify vote count
        inserted_votes = Votes.objects.filter(voter=voter)
        if inserted_votes.count() != form_count:
            inserted_votes.delete()
            return Response(
                {'error': 'Vote submission failed. Please try again.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        
        # Mark voter as voted
        voter.voted = True
        voter.save()
        
        return Response({
            'success': True,
            'message': 'Vote submitted successfully'
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        # Rollback on any error
        Votes.objects.filter(voter=voter, id__in=[v.id for v in created_votes]).delete()
        return Response(
            {'error': f'An error occurred: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def verify_otp_api_view(request):
    """API endpoint to verify OTP"""
    if request.user.user_type != '2':  # Only voters
        return Response(
            {'error': 'Only voters can verify OTP'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    serializer = OTPVerificationSerializer(data=request.data)
    
    if not serializer.is_valid():
        return Response(
            {'error': 'Invalid OTP format'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    otp = serializer.validated_data['otp']
    voter = request.user.voter
    db_otp = voter.otp
    
    if db_otp != otp:
        return Response(
            {'error': 'Invalid OTP'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    voter.verified = True
    voter.save()
    
    return Response({
        'success': True,
        'message': 'OTP verified successfully'
    }, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def resend_otp_api_view(request):
    """API endpoint to resend OTP"""
    if request.user.user_type != '2':  # Only voters
        return Response(
            {'error': 'Only voters can request OTP'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    user = request.user
    voter = user.voter
    error = False
    response_message = ""
    
    if settings.SEND_OTP:
        if voter.otp_sent >= 3:
            error = True
            response_message = "You have requested OTP three times. You cannot do this again! Please enter previously sent OTP"
        else:
            phone = voter.phone
            otp = voter.otp
            if otp is None:
                otp = generate_otp()
                voter.otp = otp
                voter.save()
            
            try:
                msg = f"Dear {user}, kindly use {otp} as your OTP"
                message_is_sent = send_sms(phone, msg)
                if message_is_sent:
                    voter.otp_sent = voter.otp_sent + 1
                    voter.save()
                    response_message = "OTP has been sent to your phone number. Please provide it in the box provided below"
                else:
                    error = True
                    response_message = "OTP not sent. Please try again"
            except Exception as e:
                error = True
                response_message = f"OTP could not be sent. {str(e)}"
    else:
        response_message = bypass_otp()
    
    if error:
        return Response(
            {'error': response_message},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    return Response({
        'success': True,
        'message': response_message
    }, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def voter_dashboard_api_view(request):
    """API endpoint to get voter dashboard data"""
    if request.user.user_type != '2':  # Only voters
        return Response(
            {'error': 'Only voters can access dashboard'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    user = request.user
    voter = user.voter
    
    # Auto-verify voter if not already verified (OTP disabled)
    if not voter.verified:
        voter.verified = True
        voter.save()
    
    # Skip OTP verification - go directly to ballot or results
    if voter.voted:
        return Response({
            'verified': True,
            'voted': True,
            'redirect_to': 'results'
        }, status=status.HTTP_200_OK)
    else:
        return Response({
            'verified': True,
            'voted': False,
            'redirect_to': 'ballot'
        }, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def voter_results_api_view(request):
    """API endpoint to get voter's submitted votes"""
    if request.user.user_type != '2':  # Only voters
        return Response(
            {'error': 'Only voters can access results'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    voter = request.user.voter
    
    if not voter.voted:
        return Response(
            {'error': 'You have not voted yet'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    votes = Votes.objects.filter(voter=voter).select_related('candidate', 'position')
    votes_data = VoteSerializer(votes, many=True).data
    
    return Response({
        'votes': votes_data
    }, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([AllowAny])  # Allow unauthenticated access for CSRF token
def get_csrf_token(request):
    """API endpoint to get CSRF token"""
    from django.middleware.csrf import get_token
    csrf_token = get_token(request)
    return Response({
        'csrfToken': csrf_token
    }, status=status.HTTP_200_OK)

