from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    """Auto-create UserProfile when a new User is created."""
    if created:
        from .models import UserProfile
        UserProfile.objects.get_or_create(user=instance)
