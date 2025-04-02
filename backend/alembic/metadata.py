from backend.models.AnalyticsModel import Base as AnalyticsBase
from backend.Area.AreaModel import Base as L1Base
from backend.User.UserModel import Base as UserBase
from backend.AudioProcessing.VoiceRecordingModel import Base as VoiceRecordingBase
from backend.Transcription.TranscriptionModel import Base as TranscriptionBase
from backend.Store.StoreModel import Base as L0Base
from backend.Business.BusinessModel import Base as BussinessBase
from backend.Feedback.FeedbackModel import Base as FeedbackBase
from backend.Sales.SalesModel import Base as L2Base
from backend.State.stateModel import Base as L3Base

target_metadata = [
    BussinessBase.metadata,
    UserBase.metadata,
    L1Base.metadata,
    L0Base.metadata,
    L2Base.metadata,
    L3Base.metadata,
    TranscriptionBase.metadata,
    AnalyticsBase.metadata,
    VoiceRecordingBase.metadata,
    FeedbackBase.metadata,
]
