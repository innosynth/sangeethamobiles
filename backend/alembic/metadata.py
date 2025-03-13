from backend.models.AnalyticsModel import Base as AnalyticsBase  
from backend.models.AreaModel import Base as AreaBase
from backend.User.UserModel import Base as UserBase
from backend.AudioProcessing.VoiceRecordingModel import Base as VoiceRecordingBase
from backend.models.TranscriptionModel  import Base as TranscriptionBase
from backend.Store.StoreModel import Base as StoreBase
from backend.Business.BusinessModel import Base as BussinessBase
from backend.Store.StoreModel import Base as StoreBase
from backend.Business.BusinessModel import Base as BussinessBase


target_metadata = [
    BussinessBase.metadata,
    AreaBase.metadata,
    UserBase.metadata,
    AreaBase.metadata,
    UserBase.metadata,
    StoreBase.metadata,
    TranscriptionBase.metadata,
    AnalyticsBase.metadata,
    TranscriptionBase.metadata,
    AnalyticsBase.metadata,
    VoiceRecordingBase.metadata,
]
