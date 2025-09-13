from django.urls import resolve, reverse
from django.shortcuts import redirect
from django.utils.deprecation import MiddlewareMixin

ALLOWED_PREFIXES = (
    "/static/",
    "/favicon.ico/",
    "/robots.txt",
    "/i18n/",
)

class OnboardingMiddleware(MiddlewareMixin):
    def process_request(self, request):
        path = request.path_info or "/"
        for p in ALLOWED_PREFIXES:
            if path.startswith(p):
                return None

        if not request.user.is_authenticated:
            return None

        try:
            profile = request.user.patient_profile
        except Exception:
            from records.models import PatientProfile
            profile, _ = PatientProfile.objects.get_or_create(
                user=request.user,
                defaults={
                    "first_name_bg": request.user.first_name or "",
                    "last_name_bg": request.user.last_name or "",
                },
            )

        complete = bool(profile.first_name_bg and profile.last_name_bg and profile.date_of_birth)

        try:
            view_name = resolve(path).view_name or ""
        except Exception:
            view_name = ""

        if complete:
            return None

        allowed_views = {
            "medj:personalcard",
            "medj:profile",
            "medj:logout",
            "medj:password_change",
            "medj:password_change_done",
        }

        if view_name in allowed_views:
            return None

        return redirect(reverse("medj:personalcard"))
