from backend.models.AnalyticsModel import Base as AnalyticsBase  
from backend.models.AreaModel import Base as AreaBase
from backend.models.BussinessModel import Base as BussinessBase
from backend.models.StoreModel import Base as StoreBase
from backend.User.UserModel import Base as UserBase
from backend.models.VoiceRecordingModel import Base as VoiceRecordingBase
from backend.models.TranscriptionModel  import Base as TranscriptionBase


target_metadata = [
    AnalyticsBase.metadata,
    AreaBase.metadata,
    BussinessBase.metadata,
    StoreBase.metadata,
    UserBase.metadata,
    VoiceRecordingBase.metadata,
    TranscriptionBase.metadata
]
