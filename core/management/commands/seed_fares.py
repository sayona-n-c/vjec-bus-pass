"""
Management command: seed_fares
Populates (or updates) the BoardingPoint fare table with the exact fares
specified in the VJEC Bus Pass System final-phase requirements.

Usage:
    python manage.py seed_fares
"""

from django.core.management.base import BaseCommand
from core.models import BoardingPoint


FARE_MAP = {
    # fare: [list of boarding point names]
    30:  ['Sreekandapuram', 'Kaniyarvayal'],
    40:  ['Chempanthotty', 'Embate', 'Karayathumchal'],
    50:  ['Irikkur', 'Chulliod', 'Chuzhali', 'Karuvanchal', 'Mandalam', 'Naduvil'],
    60:  ['Alakkode', 'Malapattam', 'Nayattupara'],
    70:  ['Chalode', 'Kurumathur', 'Nellipara', 'Oduvally', 'Kurumathur / Chorukkala'],
    80:  ['7th Maile', 'Kambil', 'Kanhirangad', 'Koodali', 'Kuppam',
          'Mattannur', 'Mayyil', 'Taliparamba'],
    90:  ['Bakkalam', 'Chavaseray', 'Dharmasala', 'Iritty'],
    100: ['Mambaram', 'Etteyar', 'Kakkayangad', 'Keecheri', 'Kodikkimotta',
          'Kolachery Mukku', 'Mangad', 'Mutharipeedika'],
    110: ['Balan Kinar', 'Cherupuzha', 'Eachur', 'Kanjirode', 'Kottayodi',
          'Panayathamparamba', 'Pariyaram'],
    120: ['Elayavoor Panchayath', 'Kattampally', 'Narath'],
    130: ['Pappinisseri', 'Peravoor'],
    140: ['Anjarakkandy', 'Ezhilode', 'Kolappa', 'Kottayampoyil',
          'Mele Chovva', 'Nirmalagiri', 'Padikkunnu'],
    150: ['Chonadam', 'Kannur Caltex', 'Kuthuparamba', 'Manjakadu',
          'Pallikunnu', 'Pathayakunnu'],
    160: ['Eranholy Palam', 'Kuyyali Puzha', 'Mokeri', 'Pathipalam',
          'Peringala', 'Thalassery'],
    170: ['Kathirur Road', 'Payyannur'],
    180: ['Panoor'],
}


class Command(BaseCommand):
    help = 'Seed BoardingPoint fare table with exact VJEC Bus Pass fares'

    def handle(self, *args, **options):
        created_count = 0
        updated_count = 0

        for fare, places in FARE_MAP.items():
            for name in places:
                obj, created = BoardingPoint.objects.update_or_create(
                    name=name,
                    defaults={'fare': fare},
                )
                if created:
                    created_count += 1
                    self.stdout.write(
                        self.style.SUCCESS(f'  [CREATED] {name} -> Rs.{fare}')
                    )
                else:
                    updated_count += 1
                    self.stdout.write(
                        self.style.WARNING(f'  [UPDATED] {name} -> Rs.{fare}')
                    )

        self.stdout.write(
            self.style.SUCCESS(
                f'\nDone! {created_count} created, {updated_count} updated. '
                f'Total: {int(created_count) + int(updated_count)} boarding points.'  # type: ignore[operator]
            )
        )
