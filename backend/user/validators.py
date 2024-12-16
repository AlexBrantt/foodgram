from django.core import validators


class UsernameValidator(validators.RegexValidator):
    regex = r"^[\w.@+-]+\z"
    message = (
        "Enter a valid username. This value may contain only letters, "
        "numbers, and @/./+/-/_ characters."
    )
    flags = 0
