from django.db import IntegrityError
from django.db.models import ProtectedError
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import exception_handler


def custom_exception_handler(exc, context):
    """Uniform error envelope: {"success": false, "status_code": ..., "errors": ...}."""

    if isinstance(exc, ProtectedError):
        return Response(
            {
                "success": False,
                "status_code": status.HTTP_409_CONFLICT,
                "errors": {"detail": "This record is referenced by other records and cannot be deleted."},
            },
            status=status.HTTP_409_CONFLICT,
        )

    if isinstance(exc, IntegrityError):
        return Response(
            {
                "success": False,
                "status_code": status.HTTP_400_BAD_REQUEST,
                "errors": {"detail": "This record conflicts with an existing one."},
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    response = exception_handler(exc, context)

    if response is not None:
        response.data = {
            "success": False,
            "status_code": response.status_code,
            "errors": response.data,
        }

    return response
