"""
Management command: seed_data
Seeds the real VML College bus routes, buses, coordinators, and users.
Usage: python manage.py seed_data
"""
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from core.models import Route, Bus, UserProfile, BusCoordinator


# All boarding points available in the system
ALL_BOARDING_POINTS = [
    '7TH MAILE', 'ALAKKODE', 'ANJARAKKANDY', 'BAKKALAM', 'BALAN KINAR',
    'CHALODE', 'CHAVASERAY', 'CHEMPANTHOTTY', 'CHERUPUZHA', 'CHONADAM',
    'CHULLIOD', 'CHUZHALI', 'DHARMASALA', 'EACHUR', 'ELAYAVOOR PANCHAYATH',
    'EMBATE', 'ERANHOLY PALAM', 'ETTEYAR', 'EZHILODE', 'IRIKKUR', 'IRITTY',
    'KAKKAYANGAD', 'KAMBIL', 'KANHIRANGAD', 'KANIYARVAYAL', 'KANJIRODE',
    'KANNUR CALTEX', 'KARAYATHUMCHAL', 'KARUVANCHAL', 'KATHIRUR ROAD',
    'KATTAMPALLY', 'KEECHERI', 'KODIKKIMOTTA', 'KOLACHERY MUKKU', 'KOLAPPA',
    'KOODALI', 'KOTTAYAMPOYIL', 'KOTTAYODI', 'KUPPAM', 'KURUMATHUR/CHORUKKALA',
    'KUTHUPARAMBA', 'KUYYALI PUZHA', 'MALAPATTAM', 'MAMBARAM', 'MANDALAM',
    'MANGAD', 'MANJAKADU', 'MATTANUR', 'MAYYIL', 'MELE CHOVVA', 'MOKERI',
    'MUTHARIPEEDIKA', 'NADUVIL', 'NARATH', 'NAYATTUPARA', 'NELLIPARA',
    'NIRMALAGIRI', 'ODUVALLY', 'PADIKKUNNU', 'PALLIKUNNU', 'PANAYATHAMPARAMBA',
    'PANOOR', 'PAPPINISSERI', 'PARIYARAM', 'PATHAYAKUNNU', 'PATHIPALAM',
    'PAYYANNUR', 'PERAVOOR', 'PERINGALA', 'PERUVALATHUPARAMBA', 'PILATHARA',
    'PONNIAM WEST', 'POOKODE', 'POOVAM', 'PUNNAD', 'PUTHIYA THERU',
    'PUTHIYA THERU SARANG', 'PUTHUSSERY', 'RAYAROME', 'SREEKANDAPURAM',
    'TALIPARAMBA', 'THALAPP', 'THALASSERY', 'THAMTHODE', 'THANA',
    'THERTHALLY', 'THETTUNNA ROAD', 'ULIKKAL', 'ULIYIL', 'URUVACHAL',
    'VAIDHYAR PEEDIKA', 'VALAKKAI', 'VALAPATTANAM', 'VANNAN METTA', 'VARAM',
    'VAYATTUPARAMBA', 'VILAKKANNUR', 'VILAKKODE', 'THONDIYIL',
]


BUS_DATA = [
    # (bus_number, bus_type, capacity, route_name, stops)
    ('BUS 1',  'tourist',  49, 'BUS 1 - THANA to SREEKANDAPURAM',
     ['THANA', 'MELE CHOVVA', 'CHALODE', 'IRIKKUR', 'SREEKANDAPURAM']),

    ('BUS 2',  'college',  49, 'BUS 2 - KALLIASSERI to ODUVALLY',
     ['KALLIASSERI', 'KEECHERI', 'MANGAD', 'DHARMASALA', '7TH MAILE', 'ODUVALLY']),

    ('BUS 3',  'college',  54, 'BUS 3 - CHERUPUZHA to VAYATTUPARAMBA',
     ['CHERUPUZHA', 'ALAKKODE', 'VAYATTUPARAMBA']),

    ('BUS 4',  'college',  49, 'BUS 4 - MAMBARAM to COLLEGE',
     ['MAMBARAM', 'VML COLLEGE']),

    ('BUS 5',  'tourist',  49, 'BUS 5 - PAYYANNUR to EZHILODE',
     ['PAYYANNUR', 'PILATHARA', 'EZHILODE']),

    ('BUS 6',  'college',  49, 'BUS 6 - TALIPARAMBA to VILAKKANNUR',
     ['TALIPARAMBA', 'POOVAM', 'VILAKKANNUR']),

    ('BUS 7',  'college',  54, 'BUS 7 - VALAPATTANAM to NARATH',
     ['VALAPATTANAM', 'PUTHIYA THERU SARANG', 'KATTAMPALLY', 'NARATH']),

    ('BUS 8',  'college',  46, 'BUS 8 - EACHUR to SREEKANDAPURAM',
     ['EACHUR', 'KODIKKIMOTTA', 'CHALODE', 'IRIKKUR', 'SREEKANDAPURAM']),

    ('BUS 9',  'college',  44, 'BUS 9 - VAIDHYAR PEEDIKA to SREEKANDAPURAM',
     ['VAIDHYAR PEEDIKA', 'ELAYAVOOR PANCHAYATH', 'VARAM', 'CHALODE', 'IRIKKUR', 'SREEKANDAPURAM']),

    ('BUS 10', 'college',  54, 'BUS 10 - THALAPP to PUTHIYA THERU',
     ['THALAPP', 'PUTHIYA THERU']),

    ('BUS 11', 'college',  49, 'BUS 11 - BAKKALAM to CHEMPANTHOTTY',
     ['BAKKALAM', 'KURUMATHUR/CHORUKKALA', 'VALAKKAI', 'CHUZHALI', 'CHEMPANTHOTTY']),

    ('BUS 12', 'college',  54, 'BUS 12 - THONDIYIL to IRITTY',
     ['THONDIYIL', 'PERAVOOR', 'VILAKKODE', 'IRITTY']),

    ('BUS 13', 'college',  54, 'BUS 13 - THALASSERY to IRITTY',
     ['THALASSERY', 'POOKODE', 'KUTHUPARAMBA', 'MATTANUR', 'PUNNAD', 'IRITTY']),

    ('BUS 14', 'college',  49, 'BUS 14 - PILATHARA to THETTUNNA ROAD',
     ['PILATHARA', 'PARIYARAM', 'EMBATE', 'KUPPAM', 'THETTUNNA ROAD']),

    ('BUS 15', 'tourist',  49, 'BUS 15 - KANNUR CALTEX to PALLIKUNNU',
     ['KANNUR CALTEX', 'PALLIKUNNU']),

    ('BUS 16', 'tourist',  49, 'BUS 16 - VANNAN METTA to PANAYATHAMPARAMBA',
     ['VANNAN METTA', 'ANJARAKKANDY', 'PANAYATHAMPARAMBA']),

    ('BUS 17', 'tourist',  49, 'BUS 17 - KAMBIL to MAYYIL',
     ['KAMBIL', 'KOLACHERY MUKKU', 'MAYYIL']),

    ('BUS 18', 'tourist',  49, 'BUS 18 - KARETTA to ULIKKAL',
     ['KARETTA', 'MATTANUR', 'IRITTY', 'PUTHUSSERY', 'ULIKKAL']),

    ('BUS 19', 'college',  49, 'BUS 19 - KEECHERI to MALAPPATTAM',
     ['KEECHERI', 'PADIKKUNNU', 'ETTEYAR', 'MALAPATTAM']),

    ('BUS 20', 'college',  34, 'BUS 20 - ALAKKODE to NADUVIL',
     ['ALAKKODE', 'KARUVANCHAL', 'NADUVIL']),

    ('BUS 21', 'tourist',  17, 'BUS 21 - CHAPPARAPADAVU to NADUVIL',
     ['CHAPPARAPADAVU', 'THETTUNNA ROAD', 'ODUVALLY', 'NADUVIL']),
]


COORDINATOR_DATA = [
    # (bus_number, staff_id, name, department, contact, boarding_point)
    ('BUS 1',  'SEC005',  'Thomas M S',          'CSE',     '7034210824',  'MELE CHOVA'),
    ('BUS 2',  'FCS113',  'Priya J',              'ADS',     '7339272832',  'DHARMASALA'),
    ('BUS 3',  'OFA001',  'Josteen J Puthumana',  'Office',  '9447646863',  'CHERUPUZHA INDOOR TOWN'),
    ('BUS 4',  'FCS063',  'Rijin I K',            'CSE',     '9947271660',  'AMBANAD'),
    ('BUS 5',  'FCS002',  'Divya B',              'CSE',     '9895606935',  'PERUMBA/PAYYANNUR'),
    ('BUS 6',  'FEC005',  'Bindu Sebastian',      'ECE',     '9947530994',  'LOURDE HOSPITAL - THALIPARAMBA'),
    ('BUS 7',  'FEC007',  'Manoj K C',            'ECE',     '9447416020',  'VALAPATNAM'),
    ('BUS 8',  'FCS075',  'Suhada C',             'CSE',     '9995561420',  'IRIKKUR'),
    ('BUS 9',  'FME002',  'Ryne PM',              'ME',      '9747119997',  'KAMAAL PEEDIKA'),
    ('BUS 10', 'FCS018',  'Vidhya S S',           'CSE',     '9496666700',  'AKG HOSPITAL/TALAP'),
    ('BUS 11', 'FCS005',  'Neena V V',            'CSD',     '9846785896',  'BAKKALAM'),
    ('BUS 12', 'FCE06',   'Dr Biju Mathew',       'CE',      '9847436426',  'PERAVOOR NEW BUS STAND'),
    ('BUS 13', 'FEE063',  'Dilin',                'EEE',     '',            'THOKKILANGADY'),
    ('BUS 14', 'SME001',  'Shaji George',         'ME',      '9495830972',  'PARIYARAM AYURVEDA COLLEGE'),
    ('BUS 15', 'MBA023',  'Athira P',             'MBA',     '9440456314',  'KMMGWC, PALLIKKUNNU'),
    ('BUS 16', 'SEC01',   'Divya K',              'ECE',     '9447736993',  'ANJARAKANDY'),
    ('BUS 17', 'FCS128',  'Athulya N',            'CSE',     '9497535057',  'KAMBIL BUS STOP'),
    ('BUS 18', 'FEC012',  'Jerrin Yomas',         'ECE',     '9961961681',  'THANTHODE'),
    ('BUS 19', 'SDTC005', 'Sayooj K',             'SDTC',    '9895908944',  'VALAPATTANAM'),
    ('BUS 20', 'LOF002',  'Stanly Kurian',        'Library', '9946789490',  'ALAKKODE TOWN'),
]


class Command(BaseCommand):
    help = 'Seed the database with real VML College bus data (2025-26)'

    def handle(self, *args, **kwargs):
        self.stdout.write('Seeding VML College bus data 2025-26...')

        # ── Routes & Buses ──────────────────────────────────
        bus_objects = {}
        for bus_no, btype, cap, route_name, stops in BUS_DATA:
            route, r_created = Route.objects.update_or_create(
                name=route_name,
                defaults={'stops': stops, 'is_active': True}
            )
            bus, b_created = Bus.objects.update_or_create(
                bus_number=bus_no,
                defaults={
                    'route': route,
                    'capacity': cap,
                    'bus_type': btype,
                    'is_active': True,
                }
            )
            bus_objects[bus_no] = bus
            s = '[Created]' if b_created else '[Updated]'
            self.stdout.write(f'  {s} {bus_no} ({btype.upper()}) – {cap} seats – {route_name}')

        # ── Bus Coordinators ─────────────────────────────────
        self.stdout.write('\nSeeding coordinators...')
        for bus_no, staff_id, name, dept, contact, bp in COORDINATOR_DATA:
            bus = bus_objects.get(bus_no)
            if not bus:
                continue
            coord, created = BusCoordinator.objects.update_or_create(
                bus=bus,
                defaults={
                    'staff_id': staff_id,
                    'name': name,
                    'department': dept,
                    'contact': contact,
                    'boarding_point': bp,
                }
            )
            s = '[Created]' if created else '[Updated]'
            self.stdout.write(f'  {s} {bus_no}: {name} ({staff_id})')

        # ── Admin user ───────────────────────────────────────
        admin_user, created = User.objects.get_or_create(
            username='admin',
            defaults={
                'first_name': 'Admin',
                'last_name': 'VML',
                'email': 'admin@vmlcollege.edu',
                'is_staff': True,
                'is_superuser': True,
            }
        )
        if created:
            admin_user.set_password('admin123')
            admin_user.save()
            profile, _ = UserProfile.objects.get_or_create(user=admin_user)
            profile.role = 'admin'
            profile.save()
            self.stdout.write('\n  [Created] Admin -> admin / admin123')
        else:
            self.stdout.write('\n  [Exists]  Admin user')

        # ── Sample student ───────────────────────────────────
        student, created = User.objects.get_or_create(
            username='VML23CS200',
            defaults={'first_name': 'Rahul', 'last_name': 'Sharma', 'email': 'rahul@vmlcollege.edu'}
        )
        if created:
            student.set_password('student123')
            student.save()
            profile, _ = UserProfile.objects.get_or_create(user=student)
            profile.vml_no = 'VML23CS200'
            profile.role = 'student'
            profile.department = 'CSE'
            profile.phone = '9123456789'
            profile.save()
            self.stdout.write('  [Created] Student -> VML23CS200 / student123')
        else:
            self.stdout.write('  [Exists]  Student user')

        self.stdout.write(self.style.SUCCESS('\nDone! 21 buses, 20 coordinators seeded.'))
        self.stdout.write('  Admin   : admin / admin123')
        self.stdout.write('  Student : VML23CS200 / student123')
