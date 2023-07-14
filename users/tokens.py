from django.contrib.auth.tokens import PasswordResetTokenGenerator

class TokenGenerator(PasswordResetTokenGenerator):
    def _make_hash_value(self, user, timestamp):
        return (
            str(user.pk) + str(timestamp) + str(user.profile.verified)
        )

account_activation_token = TokenGenerator()
password_reset_token = PasswordResetTokenGenerator()