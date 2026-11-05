from django.core.management.base import BaseCommand
from django.utils.text import slugify

from apps.locations.models import District, Locality, Neighbourhood, Province

# NOTE: Province names are authoritative. District lists are indicative and MUST be
# reconciled against the official ECZ / 2022 census district list before public launch.
PROVINCES = [
    ("Central", "CE"),
    ("Copperbelt", "CB"),
    ("Eastern", "EA"),
    ("Luapula", "LP"),
    ("Lusaka", "LS"),
    ("Muchinga", "MC"),
    ("Northern", "NO"),
    ("North-Western", "NW"),
    ("Southern", "SO"),
    ("Western", "WE"),
]

DISTRICTS = {
    "Central": ["Chibombo", "Chisamba", "Chitambo", "Kabwe", "Kapiri Mposhi", "Luano",
                "Mkushi", "Mumbwa", "Ngabwe", "Serenje", "Shibuyunji"],
    "Copperbelt": ["Chililabombwe", "Chingola", "Kalulushi", "Kitwe", "Luanshya",
                   "Lufwanyama", "Masaiti", "Mpongwe", "Mufulira", "Ndola"],
    "Eastern": ["Chadiza", "Chama", "Chipata", "Kasenengwa", "Katete", "Lundazi",
                "Mambwe", "Nyimba", "Petauke", "Sinda", "Vubwi"],
    "Luapula": ["Chembe", "Chiengi", "Chifunabuli", "Chipili", "Kawambwa", "Lunga",
                "Mansa", "Milenge", "Mwansabombwe", "Mwense", "Nchelenge", "Samfya"],
    "Lusaka": ["Chilanga", "Chongwe", "Kafue", "Luangwa", "Lusaka", "Rufunsa"],
    "Muchinga": ["Chinsali", "Isoka", "Mafinga", "Mpika", "Nakonde", "Shiwang'andu"],
    "Northern": ["Chilubi", "Kaputa", "Kasama", "Luwingu", "Mbala", "Mporokoso",
                 "Mpulungu", "Mungwi", "Nsama", "Senga Hill"],
    "North-Western": ["Chavuma", "Kabompo", "Kalumbila", "Kasempa", "Manyinga",
                      "Mufumbwe", "Mushindamo", "Mwinilunga", "Solwezi", "Zambezi"],
    "Southern": ["Chikankata", "Choma", "Gwembe", "Itezhi-Tezhi", "Kalomo", "Kazungula",
                 "Livingstone", "Mazabuka", "Monze", "Namwala", "Pemba", "Siavonga",
                 "Sinazongwe", "Zimba"],
    "Western": ["Kalabo", "Kaoma", "Limulunga", "Lukulu", "Mongu", "Mulobezi", "Mwandi",
                "Nalolo", "Nkeyema", "Senanga", "Sesheke", "Shangombo", "Sioma"],
}

# Phase 1 seeds only Lusaka's neighbourhoods; the rest arrive with Phase 2 demand.
LUSAKA_NEIGHBOURHOODS = [
    "Kabulonga", "Woodlands", "Kabwata", "Chelston", "Roma", "Rhodes Park",
    "Ibex Hill", "Kalundu", "Olympia", "Emmasdale", "Matero", "Kalingalinga",
    "Chilenje", "Libala", "Avondale", "Meanwood", "Northmead", "Kamwala",
    "Fairview", "Thornpark", "Garden", "Chudleigh", "Silverest", "Chalala",
    "John Laing", "Mtendere", "Kaunda Square", "Chainda", "Bauleni",
]


class Command(BaseCommand):
    help = "Seed Zambian provinces, districts, localities and Lusaka neighbourhoods."

    def handle(self, *args, **options):
        created = {"province": 0, "district": 0, "locality": 0, "neighbourhood": 0}

        for name, code in PROVINCES:
            province, was_created = Province.objects.get_or_create(
                slug=slugify(name), defaults={"name": name, "code": code}
            )
            created["province"] += int(was_created)

            for district_name in DISTRICTS.get(name, []):
                district, was_created = District.objects.get_or_create(
                    province=province,
                    slug=slugify(district_name),
                    defaults={"name": district_name},
                )
                created["district"] += int(was_created)

                # One locality per district for now; finer granularity comes later.
                locality, was_created = Locality.objects.get_or_create(
                    district=district,
                    slug=slugify(district_name),
                    defaults={"name": district_name},
                )
                created["locality"] += int(was_created)

                if district_name == "Lusaka":
                    for hood_name in LUSAKA_NEIGHBOURHOODS:
                        _, was_created = Neighbourhood.objects.get_or_create(
                            locality=locality,
                            slug=slugify(hood_name),
                            defaults={"name": hood_name},
                        )
                        created["neighbourhood"] += int(was_created)

        self.stdout.write(
            self.style.SUCCESS(
                "Seeded: {province} provinces, {district} districts, "
                "{locality} localities, {neighbourhood} neighbourhoods.".format(**created)
            )
        )
