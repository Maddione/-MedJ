from django.db.models.signals import post_save, post_delete, post_migrate
from django.dispatch import receiver
from .models import DocumentTag, LabTestMeasurement, MedicalEvent, get_indicator_canonical_tag

def _sync_event_tags(event):
    tag_ids = list(
        DocumentTag.objects.filter(document__medical_event=event)
        .values_list("tag_id", flat=True)
        .distinct()
    )
    if tag_ids:
        event.tags.set(tag_ids)
    else:
        event.tags.clear()

@receiver(post_save, sender=DocumentTag)
def documenttag_saved(sender, instance, **kwargs):
    doc = getattr(instance, "document", None)
    ev = getattr(doc, "medical_event", None) if doc else None
    if ev:
        _sync_event_tags(ev)

@receiver(post_delete, sender=DocumentTag)
def documenttag_deleted(sender, instance, **kwargs):
    doc = getattr(instance, "document", None)
    ev = getattr(doc, "medical_event", None) if doc else None
    if ev:
        _sync_event_tags(ev)

@receiver(post_save, sender=LabTestMeasurement)
def labmeasurement_saved(sender, instance, **kwargs):
    ev = getattr(instance, "medical_event", None)
    ind = getattr(instance, "indicator", None)
    tag = get_indicator_canonical_tag(ind)
    if ev and tag:
        ev.tags.add(tag)

def post_migrate_sync(sender, **kwargs):
    for ev in MedicalEvent.objects.all():
        _sync_event_tags(ev)

@receiver(post_migrate)
def _post_migrate_receiver(sender, **kwargs):
    post_migrate_sync(sender, **kwargs)
