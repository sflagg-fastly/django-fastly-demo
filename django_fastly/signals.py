from django.apps import apps
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver

from .utils import purge_instance


def _get_post_model():
    if not apps.is_installed("blog"):
        return None
    try:
        return apps.get_model("blog", "Post")
    except LookupError:
        return None


PostModel = _get_post_model()


if PostModel is not None:

    @receiver(post_save, sender=PostModel)
    def fastly_purge_on_post_save(sender, instance, **kwargs):
        try:
            if getattr(instance, "status", None) == "published":
                purge_instance(instance)
        except Exception:
            pass

    @receiver(post_delete, sender=PostModel)
    def fastly_purge_on_post_delete(sender, instance, **kwargs):
        try:
            purge_instance(instance)
        except Exception:
            pass
