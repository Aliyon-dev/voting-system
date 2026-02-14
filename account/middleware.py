from django.utils.deprecation import MiddlewareMixin
from django.urls import reverse
from django.shortcuts import redirect
from django.contrib import messages

class AccountCheckMiddleWare(MiddlewareMixin):
    def process_view(self, request, view_func, view_args, view_kwargs):
        modulename = view_func.__module__
        user = request.user
        voter_id = request.session.get('voter_id')

        if user.is_authenticated:
            if user.user_type == '1':  # Admin
                if modulename == 'voting.views':
                    if request.path == reverse('fetch_ballot'):
                        pass
                    elif request.path == reverse('index'):
                        pass
                    else:
                        messages.error(request, "You do not have access to this resource")
                        return redirect(reverse('adminDashboard'))
            else:
                 # Should not happen ideally
                 pass

        elif voter_id:
            # Voter
            if modulename == 'administrator.views':
                messages.error(request, "You do not have access to this resource")
                return redirect(reverse('voterDashboard'))
        
        else:
            # Guest
            if request.path == reverse('account_login') or request.path == reverse('voter_login') or modulename == 'django.contrib.auth.views' or modulename == 'voting.views':
                pass
            else:
                return redirect(reverse('voter_login'))
