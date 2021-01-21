import factory.fuzzy


class UserFactory(factory.django.DjangoModelFactory):
    username = factory.Sequence(lambda n: f"user-{n}")
    email = factory.Faker("email")

    first_name = factory.Faker("first_name")
    last_name = factory.Faker("last_name")

    class Meta:
        model = "accounts.User"


class StaffUserFactory(UserFactory):
    is_staff = True


class SuperUserFactory(StaffUserFactory):
    is_superuser = True
