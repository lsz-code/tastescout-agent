from fastapi import APIRouter

from app.guardrails.database_write_guard import DatabaseWriteGuard
from app.guardrails.mcp_result_guard import MCPResultGuard
from app.schemas.guardrail import GuardrailValidateRequest, GuardrailValidateResponse


router = APIRouter(prefix="/guardrails", tags=["Guardrails"])

#验证接口，根据guard_type调用不同的验证逻辑，
#主要对模型输出结果进行验证，确保符合预期格式和内容要求
@router.post("/validate", response_model=GuardrailValidateResponse)
async def validate_guardrail(
    payload: GuardrailValidateRequest,
) -> GuardrailValidateResponse:
    try:
        if payload.guard_type == "mcp_result":
            cleaned_data = MCPResultGuard.validate_restaurant(payload.data)
        elif payload.guard_type == "database_write":
            cleaned_data = DatabaseWriteGuard.validate_favorite_restaurant(payload.data)
        else:
            raise ValueError(f"Unsupported guard_type: {payload.guard_type}")

        #如果检验合格，返回清洗后的数据；如果不合格，返回错误信息
        return GuardrailValidateResponse(
            valid=True,
            cleaned_data=cleaned_data,
            errors=[],
            warnings=[],
        )

    except ValueError as exc:
        return GuardrailValidateResponse(
            valid=False,
            cleaned_data=None,
            errors=[str(exc)],
            warnings=[],
        )

    except Exception as exc:
        return GuardrailValidateResponse(
            valid=False,
            cleaned_data=None,
            errors=[f"Guardrail validation failed: {exc}"],
            warnings=[],
        )
