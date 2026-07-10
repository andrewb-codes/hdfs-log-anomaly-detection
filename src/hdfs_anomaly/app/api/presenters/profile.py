from hdfs_anomaly.app.models.profile import Profile
from hdfs_anomaly.app.schemas.profile import ProfileResponse


def build_profile_response(profile: Profile) -> ProfileResponse:
    return ProfileResponse(
        id=profile.id,
        email=profile.email,
        status=profile.status,
        role=profile.role,
        version=profile.version,
        created_at=profile.created_at,
    )
