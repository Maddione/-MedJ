from django.contrib.auth.views import LoginView
from django.utils.http import url_has_allowed_host_and_scheme
from django.urls import reverse_lazy
from django.views.generic import FormView
from django.contrib import messages
from django.utils.translation import gettext as _
from ..forms import RegisterForm

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

class RegisterView(FormView):
    template_name = "auth/register.html"
    form_class = RegisterForm
    success_url = reverse_lazy("medj:login")

    def form_valid(self, form):
        form.save()
        messages.success(self.request, _("Акаунтът е създаден. Влезте с новата си парола."))
        return super().form_valid(form)
