from django.contrib.auth import get_user_model
from django.db.models import Q
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.views import TokenObtainPairView

from .throttles import LoginThrottle


class EmailOrUsernameTokenSerializer(TokenObtainPairSerializer):
    """Accept either the username or the e-mail address in the ``username`` field."""

    def validate(self, attrs):
        identifier = (attrs.get("username") or "").strip()
        user = get_user_model().objects.filter(Q(username__iexact=identifier) | Q(email__iexact=identifier)).first()
        if user is not None:
            attrs["username"] = user.get_username()
        data = super().validate(attrs)
        data["user"] = {
            "id": self.user.id,
            "username": self.user.username,
            "email": self.user.email,
            "role": self.user.role,
            "organisation": self.user.organisation_id,
        }
        return data

    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token["role"] = user.role
        token["organisation"] = user.organisation_id
        return token


class LoginTokenView(TokenObtainPairView):
    serializer_class = EmailOrUsernameTokenSerializer
    throttle_classes = [LoginThrottle]
