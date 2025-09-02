from django.contrib.auth.views import LoginView
from django.utils.http import url_has_allowed_host_and_scheme

class RememberLoginView(LoginView):
    redirect_authenticated_user = True

    def form_valid(self, form):
        response = super().form_valid(form)
        remember = self.request.POST.get("remember")
        if remember:
            self.request.session.set_expiry(1209600)
        else:
            self.request.session.set_expiry(0)
        next_url = self.request.POST.get("next") or self.request.GET.get("next")
        if next_url and url_has_allowed_host_and_scheme(next_url, allowed_hosts={self.request.get_host()}):
            self.success_url = next_url
        return response
