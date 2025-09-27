from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model

User = get_user_model()

class Command(BaseCommand):
    help = 'Create a superuser with email and password'

    def handle(self, *args, **options):
        email = 'admin@example.com'
        password = 'admin123'
        
        if not User.objects.filter(email=email).exists():
            user = User.objects.create_user(
                email=email,
                password=password,
                first_name='Admin',
                last_name='User'
            )
            user.is_staff = True
            user.is_superuser = True
            user.save()
            self.stdout.write(
                self.style.SUCCESS(f'Successfully created superuser with email: {email}')
            )
        else:
            self.stdout.write(
                self.style.WARNING(f'Superuser with email {email} already exists')
            )
