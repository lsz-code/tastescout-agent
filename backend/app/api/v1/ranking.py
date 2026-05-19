from fastapi import APIRouter

from app.schemas.ranking import RankingRequest, RankingResponse, RankedRestaurant
from app.services.ranking_service import RankingService


router = APIRouter(prefix="/ranking", tags=["Ranking"])


@router.post("/rank", response_model=RankingResponse)
async def rank_restaurants(payload: RankingRequest) -> RankingResponse:
    service = RankingService()
    ranked = service.rank_restaurants(
        restaurants=payload.restaurants,
        memory=payload.memory,
        filters=payload.filters,
        limit=payload.limit,
    )

    return RankingResponse(
        restaurants=[
            RankedRestaurant(**restaurant)
            for restaurant in ranked
        ]
    )
