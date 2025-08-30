def _require_patient_profile(user):
    profile, _ = PatientProfile.objects.get_or_create(user=user)
    return profile