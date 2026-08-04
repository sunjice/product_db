"""测试部 AI 助手 — Pydantic Schemas 注册入口。
各域 schemas 分别定义在 case/sample/script/spec/task 子包中，本文件集中 re-import
以保证已有导入路径不中断。新代码请直接从子包导入。
"""

from pydantic import BaseModel, Field

from app.serializers import BigId

# 用例域
from app.aitc.case.schemas import (  # noqa: F401
    CaseCoreMark, CaseQuery, CaseStep, CaseUpdate, CaseVO,
    CaseSampleMark,
    CaseReviewReq, CaseReviewDetailVO, CaseFieldReviewItem,
    FieldSuggestionVO, PendingCaseVO, PendingSuiteNodeVO,
    ImportResult,
    ProjectCreate, ProjectQuery, ProjectUpdate, ProjectVO,
    SuiteNodeVO, SuiteVO,
)

# 样本域
from app.aitc.sample.schemas import (  # noqa: F401
    SampleCreate, SampleQuery, SampleUpdate, SampleVO,
)

# 脚本域
from app.aitc.script.schemas import (  # noqa: F401
    ScriptQuery, ScriptUpdate, ScriptVO,
)

# 规范域
from app.aitc.spec.schemas import (  # noqa: F401
    SpecCreate, SpecQuery, SpecUpdate, SpecVO,
)


# ═══════════════ 下拉选项（跨域共享）═══════════════

class OptionVO(BaseModel):
    value: BigId
    label: str

