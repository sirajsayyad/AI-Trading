"""Course catalog endpoints used by the training workspace."""

from fastapi import APIRouter

router = APIRouter(tags=["Curriculum"])

COURSES = [
    {
        "id": "risk-basics", "title": "Understanding Stop Losses",
        "description": "Protect capital with fixed, trailing, and volatility-based stops.",
        "difficulty": "beginner",
    },
    {
        "id": "risk-reward", "title": "Risk-Reward Mastery",
        "description": "Find high-probability entries with disciplined reward-to-risk planning.",
        "difficulty": "intermediate",
    },
    {
        "id": "position-sizing", "title": "Advanced Position Sizing",
        "description": "Use fixed fractional and volatility-adjusted sizing for consistent growth.",
        "difficulty": "advanced",
    },
]


@router.get("/courses")
async def list_courses():
    return COURSES


@router.get("/courses/{course_id}")
async def get_course(course_id: str):
    return next(
        (course for course in COURSES if course["id"] == course_id),
        {"error": "Course not found"},
    )
