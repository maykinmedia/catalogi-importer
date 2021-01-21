import factory.fuzzy


class UserFactory(factory.django.DjangoModelFactory):
    username = factory.Sequence(lambda n: f"user-{n}")

    class Meta:
        model = "accounts.User"


class StaffUserFactory(UserFactory):
    is_staff = True


class SuperUserFactory(StaffUserFactory):
    is_superuser = True
